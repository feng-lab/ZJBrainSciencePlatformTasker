import asyncio
import shutil
import tempfile
from asyncio import TaskGroup
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from loguru import logger
from zjbs_file_client import close_client, download_file, init_client, upload_directory

from zjbs_tasker.db import TaskRun
from zjbs_tasker.model import CompressMethod
from zjbs_tasker.settings import settings
from zjbs_tasker.util import decompress_file, get_task_dir, get_task_source_file_pack, get_task_template_pack


def sync_execute_task_run(task_run_id: int) -> None:
    asyncio.run(execute_task_run(task_run_id))


async def execute_task_run(task_run_id: int) -> None:
    async with connect_database(), file_client():
        task_run: TaskRun = await TaskRun.objects.get(id=task_run_id)
        await task_run.update(status=TaskRun.Status.running, start_at=datetime.now())

        await task_run.load_all(follow=True)
        async with TaskGroup() as tg:
            tg.create_task(download_executable(task_run.task.template.id, task_run.task.template.name))
            tg.create_task(download_source_file(task_run))
        return_code = await execute_external_executable(task_run)
        end_at = datetime.now()
        await upload_result_file(task_run)

        await task_run.update(
            status=TaskRun.Status.success if return_code == 0 else TaskRun.Status.failed, end_at=end_at
        )
        if return_code == 0:
            shutil.rmtree(worker_task_source_dir(task_run), ignore_errors=True)


@asynccontextmanager
async def connect_database() -> None:
    database = TaskRun.Meta.database
    try:
        if not database.is_connected:
            await database.connect()
        yield
    finally:
        if database.is_connected:
            await database.disconnect()


@asynccontextmanager
async def file_client() -> None:
    try:
        await init_client(settings.FILE_SERVICE_URL, timeout=60)
        yield
    finally:
        await close_client()


async def download_executable(template_id: int, template_name: str) -> None:
    await download_pack_and_extract_as_dir(
        get_task_template_pack(template_id, template_name),
        settings.WORKER_WORKING_DIR / "template",
        f"{template_id}_{template_name}",
    )


async def download_source_file(task_run: TaskRun) -> None:
    await download_pack_and_extract_as_dir(
        get_task_source_file_pack(task_run.task.id, task_run.task.name), worker_task_dir(task_run), "source"
    )


async def download_pack_and_extract_as_dir(
    server_path: str, target_parent_dir: Path, dedup_name: str | None = None
) -> bool:
    target_parent_dir.mkdir(parents=True, exist_ok=True)
    if dedup_name is not None:
        dedup_path = target_parent_dir / dedup_name
        if dedup_path.is_dir() and any(dedup_path.iterdir()):
            return False

    with tempfile.SpooledTemporaryFile() as pack_file:
        await download_file(server_path, pack_file)
        pack_file.seek(0)
        decompress_file(pack_file, CompressMethod.txz, target_parent_dir)
        return True


async def execute_external_executable(task_run: TaskRun) -> int:
    run_dir = worker_task_run_dir(task_run)
    run_dir.mkdir(parents=True, exist_ok=True)
    worker_logger_id = logger.add(run_dir / "worker.log", level="INFO")

    with (
        open(run_dir / "stdout.txt", "wt", encoding="utf-8") as stdout_log,
        open(run_dir / "stderr.txt", "wt", encoding="utf-8") as stderr_log,
    ):
        executable = worker_executable(task_run)
        args = task_run.task.template.executable[1:] + task_run.task.argument
        env = (
            {"OUTPUT_DIR": str(run_dir), "INPUT_DIR": str(run_dir.parent / "source")}
            | task_run.task.template.environment
            | task_run.task.environment
        )
        logger.info(f"{executable=}, {args=}, {env=}")

        work_process = await asyncio.create_subprocess_exec(
            executable, *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env
        )
        stdout, stderr = await work_process.communicate()
        stderr_log.write(stderr.decode("utf-8"))
        stdout_log.write(stdout.decode("utf-8"))
        logger.remove(worker_logger_id)
        return work_process.returncode


async def upload_result_file(task_run: TaskRun) -> None:
    run_dir = worker_task_run_dir(task_run)
    await upload_directory(get_task_dir(task_run.task.id, task_run.task.name), run_dir, CompressMethod.txz, mkdir=True)
    shutil.rmtree(run_dir, ignore_errors=True)


def worker_task_dir(task_run: TaskRun) -> Path:
    return settings.WORKER_WORKING_DIR / "task" / f"{task_run.task.id}_{task_run.task.name}"


def worker_task_run_dir(task_run: TaskRun) -> Path:
    return worker_task_dir(task_run) / f"run_{task_run.index}"


def worker_task_source_dir(task_run: TaskRun) -> Path:
    return worker_task_dir(task_run) / "source"


def worker_template_dir(task_template_id: int, task_template_name: str) -> Path:
    return settings.WORKER_WORKING_DIR / "template" / f"{task_template_id}_{task_template_name}"


def worker_executable(task_run: TaskRun) -> str:
    exe_path = (
        settings.WORKER_WORKING_DIR
        / "template"
        / f"{task_run.task.template.id}_{task_run.task.template.name}"
        / task_run.task.template.executable[0]
    )
    return str(exe_path)
