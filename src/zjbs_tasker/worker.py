import asyncio
import shutil
from asyncio import TaskGroup
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from loguru import logger
from zjbs_file_client import close_client, download_file, init_client, upload_directory

from zjbs_tasker.db import TaskRun
from zjbs_tasker.model import CompressMethod
from zjbs_tasker.settings import settings
from zjbs_tasker.util import decompress_file, get_task_dir, get_task_template_dir


def execute_task_run(task_run_id: int) -> None:
    asyncio.run(async_execute_task_run(task_run_id))


async def async_execute_task_run(task_run_id: int) -> None:
    async with connect_database(), file_client():
        task_run: TaskRun = await TaskRun.objects.get(id=task_run_id)
        task_run.status = TaskRun.Status.running
        task_run.start_at = datetime.now()
        await task_run.save()

        async with TaskGroup() as tg:
            tg.create_task(download_executable(task_run.task.template.id, task_run.task.template.name))
            tg.create_task(download_source_file(task_run.task.id, task_run.task.name))
        return_code = await execute_external_executable(task_run)
        task_run.end_at = datetime.now()
        await upload_result_file(task_run)

        task_run.status = TaskRun.Status.success if return_code == 0 else TaskRun.Status.failed
        await task_run.save()


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
    template_dir = settings.WORKER_WORKING_DIR / "template"
    template_dir.mkdir(parents=True, exist_ok=True)

    # 避免重复下载
    template_basename = f"{template_id}_{template_name}"
    template_target_dir = template_dir / template_basename
    if template_target_dir.is_dir() and any(template_target_dir.iterdir()):
        return

    template_xz_path = template_dir / f"{template_basename}.tar.xz"
    await download_file(get_task_template_dir(template_id, template_name), template_xz_path)
    decompress_file(template_xz_path, CompressMethod.txz, template_dir)
    template_xz_path.unlink()


async def download_source_file(task_id: int, task_name: str) -> None:
    task_dir = settings.WORKER_WORKING_DIR / "task"
    task_dir.mkdir(parents=True, exist_ok=True)

    # 避免重复下载
    task_basename = f"{task_id}_{task_name}"
    task_target_dir = task_dir / task_basename
    if task_target_dir.is_dir() and any(task_target_dir.iterdir()):
        return

    source_file_xz_path = task_dir / f"{task_basename}.tar.xz"
    await download_file(get_task_dir(task_id, task_name), source_file_xz_path)
    decompress_file(source_file_xz_path, CompressMethod.txz, task_dir)
    source_file_xz_path.unlink()


async def execute_external_executable(task_run: TaskRun) -> int:
    run_dir = worker_task_run_dir(task_run)
    logger.add(run_dir / "worker.log", level="INFO")

    with (
        open(run_dir / "stdout", "wt", encoding="utf-8") as stdout_log,
        open(run_dir / "stderr", "wt", encoding="utf-8") as stderr_log,
    ):
        executable = str(
            settings.WORKER_WORKING_DIR
            / "template"
            / f"{task_run.task.template.id}_{task_run.task.template.name}"
            / task_run.task.template.executable[0]
        )
        args = task_run.task.template.executable[1:] + task_run.task.argument
        env = {"OUTPUT_DIR": str(run_dir)} | task_run.task.template.environment | task_run.task.environment
        logger.info(f"{executable=}, {args=}, {env=}")

        work_process = await asyncio.create_subprocess_exec(
            executable, *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env
        )
        stdout, stderr = await work_process.communicate()
        stderr_log.write(stderr.decode("utf-8"))
        stdout_log.write(stdout.decode("utf-8"))
        return work_process.returncode


async def upload_result_file(task_run: TaskRun) -> None:
    run_dir = worker_task_run_dir(task_run)
    await upload_directory(get_task_dir(task_run.task.id, task_run.task.name), run_dir, CompressMethod.txz, mkdir=True)
    shutil.rmtree(run_dir, ignore_errors=True)


def worker_task_run_dir(task_run):
    run_dir = (
        settings.WORKER_WORKING_DIR / "task" / f"{task_run.task.id}_{task_run.task.name}" / f"run_{task_run.index}"
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def worker_template_dir(task_template_id: int, task_template_name: str) -> Path:
    template_dir = settings.WORKER_WORKING_DIR / "template" / f"{task_template_id}_{task_template_name}"
    template_dir.mkdir(parents=True, exist_ok=True)
    return template_dir
