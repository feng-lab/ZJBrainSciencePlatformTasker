from typing import Annotated, Optional

from fastapi import APIRouter, Body, File, Form, Query, UploadFile
from pydantic import BaseModel
from zjbs_file_client import delete, rename

from zjbs_tasker.db import Template
from zjbs_tasker.model import CompressMethod
from zjbs_tasker.settings import FileServerPath
from zjbs_tasker.util import invalid_request_exception, upload_file

router = APIRouter(tags=["template"])


class TaskTemplateResponse(BaseModel):
    id: int
    interpreter: int
    name: str
    description: str
    has_script: bool
    arguments: list[str]
    environment: dict[str, str]

    @staticmethod
    def from_db(task_template: Template | None) -> Optional["TaskTemplateResponse"]:
        return (
            TaskTemplateResponse(
                id=task_template.id,
                interpreter=task_template.interpreter.id,
                name=task_template.name,
                description=task_template.description,
                has_script=task_template.has_script,
                arguments=task_template.arguments,
                environment=task_template.environment,
            )
            if task_template
            else None
        )


@router.post("/CreateTaskTemplate", description="创建任务模板")
async def create_task_template(
    interpreter: Annotated[int, Body(description="任务解释器ID")],
    name: Annotated[str, Body(max_length=255, description="名称")],
    description: Annotated[str, Body(description="描述")],
    arguments: Annotated[list[str], Body(description="参数")],
    environment: Annotated[dict[str, str], Body(description="环境变量")],
) -> TaskTemplateResponse:
    template: Template = await Template.objects.create(
        interpreter=interpreter,
        name=name,
        description=description,
        has_script=False,
        arguments=arguments,
        environment=environment,
    )
    return TaskTemplateResponse.from_db(template)


@router.post("/UploadTaskTemplateScript", description="上传任务模板可执行文件")
async def upload_task_template_script(
    id_: Annotated[int, Form(alias="id", description="任务模板ID")],
    file: Annotated[UploadFile, File(description="任务模板脚本")],
    compress_method: Annotated[CompressMethod, Form(description="压缩方式")] = CompressMethod.not_compressed,
) -> None:
    template: Template | None = await Template.objects.get_or_none(id=id_, is_deleted=False)
    if template is None:
        raise invalid_request_exception("task template not found")
    await upload_file(
        file.file, file.filename, compress_method, FileServerPath.TASK_TEMPLATE_DIR, f"{template.id}_{template.name}"
    )
    await template.update(["has_script"], has_script=True)


@router.post("/GetTaskTemplate", description="获取任务模板")
async def get_task_template(
    id_: Annotated[int, Query(alias="id", description="任务模板ID")]
) -> TaskTemplateResponse | None:
    template: Template | None = await Template.objects.get_or_none(id=id_, is_deleted=False)
    return TaskTemplateResponse.from_db(template)


@router.post("/ListTaskTemplate", description="获取任务模板列表")
async def list_task_template(
    interpreter: Annotated[int | None, Query(alias="interpreter", description="任务解释器ID")] = None,
    name: Annotated[str | None, Query(alias="name", description="任务模板名称")] = None,
    offset: Annotated[int, Query(description="分页偏移量")] = 0,
    limit: Annotated[int, Query(description="分页大小")] = 10,
) -> list[TaskTemplateResponse]:
    query = {"is_deleted": False}
    if interpreter is not None:
        query["interpreter"] = interpreter
    if name is not None:
        query["name__icontains"] = name
    templates: list[Template] = await Template.objects.offset(offset).limit(limit).all(**query)
    return [TaskTemplateResponse.from_db(template) for template in templates]


@router.post("/UpdateTaskTemplate", description="更新任务模板")
async def update_task_template(
    id_: Annotated[int, Body(alias="id", description="任务模板ID")],
    name: Annotated[str | None, Body(max_length=255, description="名称")] = None,
    description: Annotated[str | None, Body(description="描述")] = None,
    arguments: Annotated[list[str] | None, Body(description="参数")] = None,
    environment: Annotated[dict[str, str] | None, Body(description="环境变量")] = None,
) -> TaskTemplateResponse:
    template: Template | None = await Template.objects.get_or_none(id=id_, is_deleted=False)
    if template is None:
        raise invalid_request_exception("task template not found")
    update_fields = {}
    new_name = None
    if name is not None:
        update_fields["name"] = name
        new_name = name
    if description is not None:
        update_fields["description"] = description
    if arguments is not None:
        update_fields["arguments"] = arguments
    if environment is not None:
        update_fields["environment"] = environment
    await template.update(list(update_fields.keys()), **update_fields)
    if new_name is not None:
        await rename(FileServerPath.template_script_path(template.id, template.name), f"{template.id}_{new_name}.txz")
    return TaskTemplateResponse.from_db(template)


@router.post("/DeleteTaskTemplate", description="删除任务模板")
async def delete_task_template(
    id_: Annotated[int, Query(alias="id", description="任务模板ID")]
) -> TaskTemplateResponse | None:
    template: Template | None = await Template.objects.get_or_none(id=id_, is_deleted=False)
    if template is None:
        return None
    await template.update(["is_deleted"], is_deleted=True)
    return TaskTemplateResponse.from_db(template)


@router.post("/DeleteTaskTemplateScript", description="删除任务模板脚本")
async def delete_task_template_script(id_: Annotated[int, Query(alias="id", description="任务模板ID")]) -> None:
    template: Template | None = await Template.objects.get_or_none(id=id_, is_deleted=False)
    if template is None:
        raise invalid_request_exception("task template not found")
    if template.has_script:
        await delete(FileServerPath.template_script_path(template.id, template.name))
        await template.update(["has_script"], has_script=False)
