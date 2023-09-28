from typing import Annotated

from fastapi import APIRouter, Body, File, Query, UploadFile
from zjbs_file_client import upload, upload_zip

from zjbs_tasker.db import TaskTemplate
from zjbs_tasker.model import CreateTaskTemplate

router = APIRouter(tags=["api"])


@router.post("/CreateTaskTemplate", description="创建任务模板")
async def create_task_template(args: Annotated[CreateTaskTemplate, Body(description="任务模板")]) -> int:
    task_template = await TaskTemplate.objects.create(**args.dict())
    return task_template.id


@router.post("/UploadTaskTemplateExecutable", description="上传任务模板可执行文件")
async def upload_task_template_executable(
    task_template_id: Annotated[int, Query(ge=0, description="任务模板ID")],
    file: Annotated[UploadFile, File(description="任务模板可执行文件")],
    is_zipped: Annotated[bool | None, Query(description="是否压缩")] = None,
    zip_metadata_encoding: Annotated[str | None, Query(description="压缩文件元数据编码")] = None,
) -> None:
    task_template = await TaskTemplate.objects.get(id=task_template_id)
    task_template_dir = get_task_template_dir(task_template=task_template)
    if is_zipped or (is_zipped is None and file.filename.endswith(".zip")):
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


def get_task_template_dir(
    *,
    task_template: TaskTemplate | None = None,
    task_template_id: int | None = None,
    task_template_name: str | None = None,
) -> str:
    if task_template:
        task_template_id, task_template_name = task_template.id, task_template.name
    return f"/tasker/template/{task_template_id}_{task_template_name}"
