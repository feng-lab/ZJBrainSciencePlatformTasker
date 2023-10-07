from typing import Annotated

from fastapi import APIRouter, Body, File, Query, UploadFile
from zjbs_file_client import upload, upload_zip

from zjbs_tasker.db import Task, TaskRun, TaskTemplate
from zjbs_tasker.model import CreateTask, CreateTaskTemplate
from zjbs_tasker.server import queue
from zjbs_tasker.worker import execute_task_run

router = APIRouter(tags=["api"])

TASKER_BASE_DIR: str = "/tasker"
TASK_BASE_DIR: str = f"{TASKER_BASE_DIR}/task"
TASK_TEMPLATE_BASE_DIR: str = f"{TASKER_BASE_DIR}/template"


@router.post("/CreateTaskTemplate", description="创建任务模板")
async def create_task_template(args: Annotated[CreateTaskTemplate, Body(description="任务模板")]) -> int:
    task_template = await TaskTemplate.objects.create(**args.dict())
    return task_template.id


@router.post("/UploadTaskTemplateExecutable", description="上传任务模板可执行文件")
async def upload_task_template_executable(
    task_template_id: Annotated[int, Query(ge=0, description="任务模板ID")],
    file: Annotated[UploadFile, File(description="任务模板可执行文件")],
    is_zipped: Annotated[bool, Query(description="是否压缩")] = False,
    zip_metadata_encoding: Annotated[str | None, Query(description="压缩文件元数据编码")] = None,
) -> None:
    task_template = await TaskTemplate.objects.get(id=task_template_id)
    task_template_dir = get_task_template_dir(task_template=task_template)
    if is_zipped:
        await upload_zip(
            task_template_dir,
            file.file,
            file.filename,
            mkdir=True,
            allow_overwrite=False,
            zip_metadata_encoding=zip_metadata_encoding,
        )
    else:
        await upload(task_template_dir, file.file, file.filename, mkdir=True, allow_overwrite=False)


@router.post("/CreateTask", description="创建任务")
async def create_task(args: Annotated[CreateTask, Body(description="任务")]) -> int:
    async with Task.Meta.database.transaction():
        task = await Task.objects.create(**args.dict(), source_files=[])
        await start_run_task(task.id)
        return task.id


@router.post("/UploadTaskSourceFile", description="上传任务源文件")
async def upload_task_source_file(
    task_id: Annotated[int, Query(ge=0, description="任务ID")],
    file: Annotated[UploadFile, File(description="任务源文件")],
    is_zipped: Annotated[bool, Query(description="是否压缩")] = False,
    zip_metadata_encoding: Annotated[str | None, Query(description="压缩文件元数据编码")] = None,
) -> None:
    task = await Task.objects.get(id=task_id)
    task_source_dir = get_task_source_dir(task=task)
    if is_zipped:
        await upload_zip(
            task_source_dir,
            file.file,
            file.filename,
            mkdir=True,
            allow_overwrite=False,
            zip_metadata_encoding=zip_metadata_encoding,
        )
    else:
        await upload(task_source_dir, file.file, file.filename, mkdir=True, allow_overwrite=False)


def get_task_template_dir(
    *,
    task_template: TaskTemplate | None = None,
    task_template_id: int | None = None,
    task_template_name: str | None = None,
) -> str:
    if task_template:
        task_template_id, task_template_name = task_template.id, task_template.name
    return f"{TASK_TEMPLATE_BASE_DIR}/{task_template_id}_{task_template_name}"


def get_task_dir(*, task: Task | None = None, task_id: int | None = None, task_name: str | None = None) -> str:
    if task:
        task_id, task_name = task.id, task.name
    return f"{TASK_BASE_DIR}/{task_id}_{task_name}"


def get_task_source_dir(*, task: Task | None = None, task_id: int | None = None, task_name: str | None = None) -> str:
    task_dir = get_task_dir(task=task, task_id=task_id, task_name=task_name)
    return f"{task_dir}/source"


def get_task_run_dir(
    *,
    task: Task | None = None,
    task_run: TaskRun | None = None,
    task_id: int | None = None,
    task_name: str | None = None,
    task_run_index: int | None = None,
) -> str:
    task_dir = get_task_dir(task=task, task_id=task_id, task_name=task_name)
    if task_run:
        task_run_index = task_run.index
    return f"{task_dir}/run_{task_run_index}"


async def start_run_task(task_id: int, index: int = 1) -> None:
    task_run = await TaskRun.objects.create(task=task_id, index=index, status=TaskRun.Status.pending)
    queue.enqueue(execute_task_run, task_run.id)
