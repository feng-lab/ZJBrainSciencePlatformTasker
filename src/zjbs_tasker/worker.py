import asyncio
from asyncio import TaskGroup
from contextlib import asynccontextmanager
from datetime import datetime

from zjbs_tasker.db import Task, TaskRun, TaskTemplate


async def async_execute_task_run(task_run_id: int) -> None:
    async with connect_database():
        task_run: TaskRun = await TaskRun.objects.get(id=task_run_id)
        task_run.status = TaskRun.Status.running
        task_run.start_at = datetime.now()
        await task_run.save()

        async with TaskGroup() as tg:
            tg.create_task(download_executable(task_run.task.template))
            tg.create_task(download_source_files(task_run.task))
        execute_external_executable(task_run)
        upload_result_file(task_run)

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


async def download_executable(task_template: TaskTemplate) -> None:
    pass


async def download_source_files(task: Task) -> None:
    pass


def execute_external_executable(task_run: TaskRun) -> None:
    pass


def upload_result_file(task_run: TaskRun) -> None:
    pass


def execute_task_run(task_run_id: int) -> None:
    asyncio.run(async_execute_task_run(task_run_id))
