import asyncio
import shutil
import tempfile
from asyncio import TaskGroup
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from pathlib import Path

from loguru import logger
from zjbs_file_client import close_client, download_file, init_client, upload_directory

from zjbs_tasker.db import Interpreter, Run, Status, Task, Template
from zjbs_tasker.model import CompressMethod
from zjbs_tasker.settings import FileServerPath, settings
from zjbs_tasker.util import decompress_file


async def execute_task_run(task_run_id: int) -> None:
    # 连接数据库和文件服务器
    async with connect_database(), file_client():
        # 更新TaskRun状态
        task_run: Run = await Run.objects.get(id=task_run_id)
        await task_run.update(status=Status.running, start_at=datetime.now())

        task = await task_run.task.load()
        task_template = await task.template.load()
        task_interpreter = task_template.interpreter
        if task_interpreter is not None:
            await task_interpreter.load()

        # 并行下载解释器，模板和源文件
        async with TaskGroup() as tg:
            if task_interpreter is not None:
                tg.create_task(
                    download_pack_and_extract_as_dir(
                        FileServerPath.interpreter_executable_path(task_interpreter.id, task_interpreter.name),
                        settings.WORKER_WORKING_DIR / "interpreter",
                        f"{task_interpreter.id}_{task_interpreter.name}",
                    )
                )
            tg.create_task(
                download_pack_and_extract_as_dir(
                    FileServerPath.template_script_path(task_template.id, task_template.name),
                    settings.WORKER_WORKING_DIR / "template",
                    f"{task_template.id}_{task_template.name}",
                )
            )
            tg.create_task(
                download_pack_and_extract_as_dir(
                    FileServerPath.task_source_file_path(task.id, task.name), worker_task_dir(task_run), "source"
                )
            )

        # 执行任务
        return_code = await execute_external_executable(task_run, task, task_template, task_interpreter)
        end_at = datetime.now()

        # 上传结果文件
        await upload_result_file(task_run)

        # 更新TaskRun的状态
        await task_run.update(status=Run.Status.success if return_code == 0 else Run.Status.failed, end_at=end_at)

        # 如果任务执行成功，删除源文件
        if return_code == 0:
            shutil.rmtree(worker_task_source_dir(task_run), ignore_errors=True)


@asynccontextmanager
async def connect_database() -> None:
    database = Run.Meta.database
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
        await init_client(settings.FILE_SERVER_URL, timeout=60)
        yield
    finally:
        await close_client()


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


async def execute_external_executable(
    task_run: Run, task: Task, task_template: Template, task_interpreter: Interpreter | None
) -> int:
    run_dir = worker_task_run_dir(task_run)
    run_dir.mkdir(parents=True, exist_ok=True)

    with context_logger(run_dir / "worker.log", "INFO"):
        logger.info(f"start execute task run")

        exe, args = build_command(task, task_template, task_interpreter)
        env = build_environment(task, task_template, task_interpreter, run_dir)
        logger.info(f"executable: {exe}")
        logger.info(f"arguments: {args}")
        logger.info(f"environment variables: {env}")

        # 运行任务，并把stdout和stderr输出到文件
        with (
            open(run_dir / "stdout.txt", "w", encoding="utf-8") as stdout_file,
            open(run_dir / "stderr.txt", "w", encoding="utf-8") as stderr_file,
        ):
            process = await asyncio.create_subprocess_exec(
                exe, *args, stdout=stdout_file, stderr=stderr_file, env=env, cwd=run_dir
            )
            return await process.wait()


@contextmanager
def context_logger(log_path: Path | str, level: int | str) -> None:
    from loguru import logger

    handle = None
    try:
        handle = logger.add(log_path, level=level)
        yield
    except Exception as e:
        logger.exception(e)
    finally:
        if handle is not None:
            logger.remove(handle)


def build_command(task: Task, task_template: Template, task_interpreter: Interpreter | None) -> tuple[str, list[str]]:
    cmd = []
    if task_interpreter is not None:
        cmd.extend(task_interpreter.executable)
    cmd.extend(task_template.executable)
    cmd.extend(task.argument)

    # 把可执行文件转换为实际路径
    if task.template.interpreter is None:
        exe = str(worker_template_dir(task_template) / cmd[0])
    else:
        exe = str(worker_interpreter_dir(task_interpreter) / cmd[0])

    return exe, cmd[1:]


def build_environment(
    task: Task, task_template: Template, task_interpreter: Interpreter | None, run_dir: Path | str
) -> dict[str, str]:
    run_dir = Path(run_dir).absolute()
    env = {"INPUT_DIR": str(run_dir.parent / "source"), "OUTPUT_DIR": str(run_dir)}
    if task_interpreter is not None:
        env.update(task_interpreter.environment)
    env.update(task_template.environment)
    env.update(task.environment)
    return env


async def upload_result_file(task_run: Run) -> None:
    run_dir = worker_task_run_dir(task_run)
    await upload_directory(
        FileServerPath.task_dir(task_run.task.id, task_run.task.name), run_dir, CompressMethod.txz, mkdir=True
    )
    shutil.rmtree(run_dir, ignore_errors=True)


def worker_interpreter_dir(task_interpreter: Interpreter) -> Path:
    return settings.WORKER_WORKING_DIR / "interpreter" / f"{task_interpreter.id}_{task_interpreter.name}"


def worker_task_dir(task_run: Run) -> Path:
    return settings.WORKER_WORKING_DIR / "task" / f"{task_run.task.id}_{task_run.task.name}"


def worker_task_run_dir(task_run: Run) -> Path:
    return worker_task_dir(task_run) / f"run_{task_run.index}"


def worker_task_source_dir(task_run: Run) -> Path:
    return worker_task_dir(task_run) / "source"


def worker_template_dir(task_template: Template) -> Path:
    return settings.WORKER_WORKING_DIR / "template" / f"{task_template.id}_{task_template.name}"


def worker_executable(task_run: Run) -> str:
    exe_path = (
        settings.WORKER_WORKING_DIR
        / "template"
        / f"{task_run.task.template.id}_{task_run.task.template.name}"
        / task_run.task.template.executable[0]
    )
    return str(exe_path)
