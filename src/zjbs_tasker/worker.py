import asyncio
from asyncio import TaskGroup
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from zjbs_file_client import close_client, init_client

from zjbs_tasker.db import Task, TaskRun, TaskTemplate
from zjbs_tasker.settings import settings


def execute_task_run(task_run_id: int) -> None:
    asyncio.run(async_execute_task_run(task_run_id))


async def async_execute_task_run(task_run_id: int) -> None:
    async with connect_database(), file_client():
        task_run: TaskRun = await TaskRun.objects.get(id=task_run_id)
        task_run.status = TaskRun.Status.running
        task_run.start_at = datetime.now()
        await task_run.save()

        async with TaskGroup() as tg:
            tg.create_task(download_executable(task_run.task.template))
            tg.create_task(download_source_files(task_run.task))
        await execute_external_executable(task_run)
        await upload_result_file(task_run)

        task_run.status = TaskRun.Status.success
        task_run.end_at = datetime.now()
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


async def download_executable(task_template: TaskTemplate) -> None:
    template_dir = settings.WORKER_WORKING_DIR / "template"
    template_dir.mkdir(parents=True, exist_ok=True)


async def download_source_files(task: Task) -> None:
    pass


async def execute_external_executable(task_run: TaskRun) -> None:
    pass


async def upload_result_file(task_run: TaskRun) -> None:
    pass


def get_local_template_dir(task_template_id: int, task_template_name: str) -> Path:
    template_dir = settings.WORKER_WORKING_DIR / "template" / f"{task_template_id}_{task_template_name}"
    template_dir.mkdir(parents=True, exist_ok=True)
    return template_dir
