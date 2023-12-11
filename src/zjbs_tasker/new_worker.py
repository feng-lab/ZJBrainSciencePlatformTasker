from asyncio import TaskGroup
from datetime import datetime
from pathlib import Path

from loguru import logger
from zjbs_file_client import init_client, close_client, download_directory

from zjbs_tasker.db import database, Run, Task, Template, Interpreter, Status
from zjbs_tasker.settings import settings
from zjbs_tasker.worker import download_pack_and_extract_as_dir


class WorkerPath:
    @staticmethod
    def interpreter_dir(interpreter: Interpreter) -> Path:
        return settings.WORKER_WORKING_DIR / "interpreter" / str(interpreter.id)

    @staticmethod
    def template_dir(template: Template) -> Path:
        return settings.WORKER_WORKING_DIR / "template" / str(template.id)

    @staticmethod
    def task_dir(task: Task) -> Path:
        return settings.WORKER_WORKING_DIR / "task" / str(task.id)

    @staticmethod
    def task_source_dir(task: Task) -> Path:
        return WorkerPath.task_dir(task) / "source"

    @staticmethod
    def task_run_dir(run: Run) -> Path:
        return settings.WORKER_WORKING_DIR / "task" / str(run.task.id) / str(run.id)


async def execute_run(run_id: int) -> None:
    # 处理数据库和文件服务器的链接
    try:
        if not database.is_connected:
            await database.connect()
        await init_client(settings.FILE_SERVER_URL, timeout=60)

        # 执行任务
        await execute(run_id)

    finally:
        await close_client()
        if database.is_connected:
            await database.disconnect()


async def execute(run_id: int) -> None:
    # 更新数据库
    run: Run = await Run.objects.get(id=run_id, is_deleted=False)
    task: Task = await run.task.load()
    template: Template = await task.template.load()
    interpreter: Interpreter = await template.interpreter.load()

    # 添加log
    logger.add(WorkerPath.task_run_dir(run) / "worker.log", level="INFO")

    # 更新状态
    task.status = run.status = Status.running
    run.start_at = datetime.now()
    if task.start_at is None:
        task.start_at = run.start_at
    update_columns = ["status", "start_at"]
    await run.update(update_columns)
    await task.update(update_columns)

    # 下载解释器、模板和源文件
    async with TaskGroup() as tg:
        if interpreter.executable_pack_path:
            tg.create_task(
                download_pack_and_extract_as_dir(
                    interpreter.executable_pack_path,
                    WorkerPath.interpreter_dir(interpreter).parent,
                    str(interpreter.id),
                )
            )
        if template.script_pack_path:
            tg.create_task(
                download_pack_and_extract_as_dir(
                    template.script_pack_path, WorkerPath.template_dir(template).parent, str(template.id)
                )
            )
        if task.source_file_dir:
            tg.create_task(download_task_source_dir(task))

    # 执行任务
    return_code = await execute_external_executable(run, task, template, interpreter)


async def download_task_source_dir(task: Task) -> None:
    if task.source_file_dir:
        source_dir = await download_directory(task.source_file_dir, WorkerPath.task_source_dir(task).parent)
        source_dir.rename(source_dir.with_name("source"))


# async def execute_external_executable(run: Run, task: Task, template: Template, interpreter: Interpreter) -> int:
#     run_dir = WorkerPath.task_run_dir(run)
#     run_dir.mkdir(parents=True, exist_ok=True)
#
#     try:
#         logger.info("start execute task run")
