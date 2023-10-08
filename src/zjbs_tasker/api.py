import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Body, File, Form, Query, UploadFile
from zjbs_file_client import upload, upload_zip

from zjbs_tasker.db import Task, TaskRun, TaskTemplate
from zjbs_tasker.model import CompressMethod, CreateTask
from zjbs_tasker.server import queue
from zjbs_tasker.util import TASK_TEMPLATE_BASE_DIR, get_task_source_dir
from zjbs_tasker.worker import execute_task_run

router = APIRouter(tags=["api"])


@router.post("/CreateTaskTemplate", description="创建任务模板")
async def create_task_template(
    file: Annotated[UploadFile, File(description="任务模板可执行文件")],
    name: Annotated[str, Form(description="任务模板名称", max_length=255)],
    template_type: Annotated[TaskTemplate.Type, Form(description="任务模板类型", alias="type")],
    executable: Annotated[list[str], Form(description="任务模板可执行文件")],
    environment: Annotated[dict[str, str] | None, Form(description="任务模板环境变量")] = None,
    compress_method: Annotated[CompressMethod, Form(description="压缩方式")] = CompressMethod.not_compressed,
) -> int:
    with (
        TaskTemplate.Meta.database.transaction(),
        tempfile.NamedTemporaryFile() as temp_receive_file,
        tempfile.TemporaryDirectory() as temp_decompress_dir,
        tempfile.NamedTemporaryFile() as temp_recompressed_file,
    ):
        task_template = await TaskTemplate.objects.create(
            name=name, type=template_type, executable=executable, environment=environment
        )

        while chunk := file.file.read(1024 * 1024):
            temp_receive_file.file.write(chunk)
        if compress_method is not CompressMethod.not_compressed:
            decompress_file(temp_receive_file.name, compress_method, temp_decompress_dir)
        else:
            shutil.move(temp_receive_file.name, temp_decompress_dir)
        with tarfile.open(temp_recompressed_file.name, "w:xz") as recompressed_file:
            recompressed_file.add(temp_decompress_dir, arcname=f"{task_template.id}_{task_template.name}")
        with open(temp_recompressed_file.name, "rb") as temp_recompressed_file_read:
            await upload(
                TASK_TEMPLATE_BASE_DIR,
                temp_recompressed_file_read,
                f"{task_template.id}_{task_template.name}.tar.xz",
                mkdir=True,
                allow_overwrite=False,
            )
    return task_template.id


@router.post("/UploadTaskTemplateExecutable", description="上传任务模板可执行文件")
async def upload_task_template_executable(
    task_template_id: Annotated[int, Query(ge=0, description="任务模板ID")],
    file: Annotated[UploadFile, File(description="任务模板可执行文件")],
    is_zipped: Annotated[bool, Query(description="是否压缩")] = False,
    zip_metadata_encoding: Annotated[str | None, Query(description="压缩文件元数据编码")] = None,
) -> None:
    task_template = await TaskTemplate.objects.get(id=task_template_id)
    task_template_dir = get_task_template_dir(task_template.id, task_template.name)
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
    task_source_dir = get_task_source_dir(task.id, task.name)
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


async def start_run_task(task_id: int, index: int = 1) -> None:
    task_run = await TaskRun.objects.create(task=task_id, index=index, status=TaskRun.Status.pending)
    queue.enqueue(execute_task_run, task_run.id)


def decompress_file(
    file_path: Path | str, compress_method: CompressMethod, target_parent_directory: Path | str
) -> None:
    target_parent_directory.mkdir(parents=True, exist_ok=True)
    match compress_method:
        case CompressMethod.zip:
            with zipfile.ZipFile(file_path, "r") as zip_file:
                zip_file.extractall(target_parent_directory)
        case CompressMethod.tgz | CompressMethod.txz:
            with tarfile.open(file_path, "r:gz" if compress_method is CompressMethod.tgz else "r:xz") as tar_file:
                tar_file.extractall(target_parent_directory)
        case CompressMethod.not_compressed:
            raise ValueError("cannot decompress not compressed file")
