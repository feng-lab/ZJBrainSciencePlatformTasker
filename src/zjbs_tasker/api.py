import shutil
import tarfile
import uuid
from typing import Annotated, BinaryIO

from fastapi import APIRouter, Body, File, Form, UploadFile
from zjbs_file_client import upload

from zjbs_tasker.db import Task, TaskRun, TaskTemplate
from zjbs_tasker.model import BaseTaskRun, CompressMethod, CreateTask, CreateTaskTemplate
from zjbs_tasker.server import queue
from zjbs_tasker.settings import settings
from zjbs_tasker.util import TASK_BASE_DIR, TASK_TEMPLATE_BASE_DIR, decompress_file
from zjbs_tasker.worker import execute_task_run

router = APIRouter(tags=["api"])


@router.post("/CreateTaskTemplate", description="创建任务模板")
async def create_task_template(create_args: Annotated[CreateTaskTemplate, Body(description="任务模板")]) -> int:
    task_template = await TaskTemplate.objects.create(**create_args.dict())
    return task_template.id


@router.post("/UploadTaskTemplateExecutable", description="上传任务模板可执行文件")
async def upload_task_template_executable(
    task_template_id: Annotated[int, Form(description="任务模板ID")],
    file: Annotated[UploadFile, File(description="任务模板可执行文件")],
    compress_method: Annotated[CompressMethod, Form(description="压缩方式")] = CompressMethod.not_compressed,
) -> None:
    task_template = await TaskTemplate.objects.get(id=task_template_id, is_deleted=False)
    await upload_file(
        file.file, file.filename, compress_method, TASK_TEMPLATE_BASE_DIR, f"{task_template.id}_{task_template.name}"
    )


@router.post("/CreateTask", description="创建任务")
async def create_task(args: Annotated[CreateTask, Body(description="任务")]) -> int:
    task = await Task.objects.create(**args.dict())
    return task.id


@router.post("/UploadTaskSourceFile", description="上传任务源文件")
async def upload_task_source_file(
    task_id: Annotated[int, Form(ge=0, description="任务ID")],
    file: Annotated[UploadFile, File(description="任务源文件")],
    compress_method: Annotated[CompressMethod, Form(description="压缩方式")] = CompressMethod.not_compressed,
) -> None:
    task = await Task.objects.get(id=task_id, is_deleted=False)
    task_basename = f"{task.id}_{task.name}"
    await upload_file(file.file, file.filename, compress_method, f"{TASK_BASE_DIR}/{task_basename}", "source")


@router.post("/StartTask", description="开始任务")
async def start_task(task_id: Annotated[int, Body(description="任务ID")]) -> None:
    task = await Task.objects.get(id=task_id)
    await start_run_task(task.id)


@router.post("/ListTaskRuns", description="列出任务运行记录", response_model_exclude={"task"})
async def list_task_runs(task_id: int) -> list[BaseTaskRun]:
    task = await Task.objects.select_related("runs").get(id=task_id, is_deleted=False)
    return [
        BaseTaskRun(task=task.id, status=task_run.status, start_at=task_run.start_at, end_at=task_run.end_at)
        for task_run in task.runs
        if not task_run.is_deleted
    ]


async def upload_file(
    file: BinaryIO, filename: str, compress_method: CompressMethod, base_dir: str, target_basename: str
) -> None:
    tmp_working_dir = settings.SERVER_WORKING_DIR / uuid.uuid4().hex
    try:
        # 临时文件
        tmp_working_dir.mkdir(parents=True)
        temp_received_file_path = tmp_working_dir / "received_file"
        temp_decompressed_dir_path = tmp_working_dir / "decompress_dir"
        temp_recompressed_file_path = tmp_working_dir / "recompressed_file"

        # 写入收到的文件
        with open(temp_received_file_path, "wb") as temp_received_file:
            while chunk := file.read(1024 * 1024):
                temp_received_file.write(chunk)

        # 如果是压缩文件，则先解压再压缩，否则直接压缩
        temp_decompressed_dir_path.mkdir()
        if compress_method is CompressMethod.not_compressed:
            shutil.move(temp_received_file_path, temp_decompressed_dir_path / filename)
        else:
            decompress_file(temp_received_file_path, compress_method, temp_decompressed_dir_path)
        with tarfile.open(temp_recompressed_file_path, "w:xz") as recompressed_file:
            recompressed_file.add(temp_decompressed_dir_path, arcname=target_basename)

        # 上传文件
        with open(temp_recompressed_file_path, "rb") as temp_recompressed_file_read:
            await upload(
                base_dir, temp_recompressed_file_read, f"{target_basename}.tar.xz", mkdir=True, allow_overwrite=False
            )
    finally:
        shutil.rmtree(tmp_working_dir, ignore_errors=True)


async def start_run_task(task_id: int, index: int = 1) -> None:
    task_run = await TaskRun.objects.create(task=task_id, index=index, status=TaskRun.Status.pending)
    queue.enqueue(execute_task_run, task_run.id)
