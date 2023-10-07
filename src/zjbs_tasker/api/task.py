from typing import Annotated

from fastapi import APIRouter, Body, File, Query, UploadFile
from zjbs_file_client import upload, upload_zip

from zjbs_tasker.api import get_task_source_dir
from zjbs_tasker.db import Task
from zjbs_tasker.model import CreateTask

router = APIRouter(tags=["task"])


@router.post("/CreateTask", description="创建任务")
async def create_task(args: Annotated[CreateTask, Body(description="任务")]) -> int:
    task = await Task.objects.create(**args.dict())
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
