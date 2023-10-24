from typing import Annotated

from fastapi import APIRouter, Body, File, Form, UploadFile

from zjbs_tasker.db import Task, TaskRun, TaskTemplate
from zjbs_tasker.model import CompressMethod
from zjbs_tasker.server import queue
from zjbs_tasker.settings import FileServerPath
from zjbs_tasker.util import upload_file
from zjbs_tasker.worker import execute_task_run

router = APIRouter(tags=["api"])


@router.post("/UploadTaskTemplateExecutable", description="上传任务模板可执行文件")
async def upload_task_template_executable(
    task_template_id: Annotated[int, Form(description="任务模板ID")],
    file: Annotated[UploadFile, File(description="任务模板可执行文件")],
    compress_method: Annotated[CompressMethod, Form(description="压缩方式")] = CompressMethod.not_compressed,
) -> None:
    task_template = await TaskTemplate.objects.get(id=task_template_id, is_deleted=False)
    await upload_file(
        file.file,
        file.filename,
        compress_method,
        FileServerPath.TASK_TEMPLATE_DIR,
        f"{task_template.id}_{task_template.name}",
    )


@router.post("/UploadTaskSourceFile", description="上传任务源文件")
async def upload_task_source_file(
    task_id: Annotated[int, Form(ge=0, description="任务ID")],
    file: Annotated[UploadFile, File(description="任务源文件")],
    compress_method: Annotated[CompressMethod, Form(description="压缩方式")] = CompressMethod.not_compressed,
) -> None:
    task = await Task.objects.get(id=task_id, is_deleted=False)
    await upload_file(file.file, file.filename, compress_method, FileServerPath.task_dir(task.id, task.name), "source")


@router.post("/StartTask", description="开始任务")
async def start_task(task_id: Annotated[int, Body(description="任务ID")]) -> None:
    task = await Task.objects.get(id=task_id, is_deleted=False)
    task_run = await TaskRun.objects.create(task=task.id, index=0, status=TaskRun.Status.pending)
    queue.enqueue(execute_task_run, task_run.id)


@router.post("/ListTaskRuns", description="列出任务运行记录", response_model=list[TaskRun])
async def list_task_runs(task_id: int) -> list[TaskRun]:
    task = await Task.objects.select_related("runs").get(id=task_id, is_deleted=False)
    return [task_run.dict(exclude={"task"}) for task_run in task.runs if not task_run.is_deleted]


async def start_run_task(task_id: int, index: int = 1) -> None:
    task_run = await TaskRun.objects.create(task=task_id, index=index, status=TaskRun.Status.pending)
    queue.enqueue(execute_task_run, task_run.id)
