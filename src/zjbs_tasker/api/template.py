from typing import Annotated, Optional

from fastapi import APIRouter, Body, Query
from pydantic import BaseModel

from zjbs_tasker.db import Template
from zjbs_tasker.util import invalid_request_exception

router = APIRouter(tags=["template"])


class TaskTemplateResponse(BaseModel):
    id: int
    interpreter: int
    name: str
    description: str
    creator: int
    script_pack_path: str | None
    script_path: str | None
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
                creator=task_template.creator,
                script_pack_path=task_template.script_pack_path,
                script_path=task_template.script_path,
                arguments=task_template.arguments,
                environment=task_template.environment,
            )
            if task_template
            else None
        )


@router.post("/create-template", description="创建任务模板")
async def create_template(
    interpreter: Annotated[int, Body(description="任务解释器ID")],
    name: Annotated[str, Body(max_length=255, description="名称")],
    description: Annotated[str, Body(description="描述")],
    creator: Annotated[int, Body(description="创建者ID")],
    script_pack_path: Annotated[str, Body(description="脚本包FileServer路径")],
    script_path: Annotated[str | None, Body(description="脚本路径")],
    arguments: Annotated[list[str], Body(description="参数")],
    environment: Annotated[dict[str, str], Body(description="环境变量")],
) -> TaskTemplateResponse:
    template: Template = await Template.objects.create(
        interpreter=interpreter,
        name=name,
        description=description,
        creator=creator,
        script_pack_path=script_pack_path,
        script_path=script_path,
        arguments=arguments,
        environment=environment,
    )
    return TaskTemplateResponse.from_db(template)


@router.post("/get-template", description="获取任务模板")
async def get_template(id_: Annotated[int, Query(alias="id", description="任务模板ID")]) -> TaskTemplateResponse | None:
    template: Template | None = await Template.objects.get_or_none(id=id_, is_deleted=False)
    return TaskTemplateResponse.from_db(template)


@router.post("/list-template", description="获取任务模板列表")
async def list_template(
    interpreter: Annotated[int | None, Query(description="任务解释器ID")] = None,
    name: Annotated[str | None, Query(description="任务模板名称")] = None,
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


@router.post("/update-template", description="更新任务模板")
async def update_template(
    id_: Annotated[int, Body(alias="id", description="任务模板ID")],
    name: Annotated[str | None, Body(max_length=255, description="名称")] = None,
    description: Annotated[str | None, Body(description="描述")] = None,
    creator: Annotated[int | None, Body(description="创建者ID")] = None,
    script_pack_path: Annotated[str | None, Body(description="脚本包FileServer路径")] = None,
    script_path: Annotated[str | None, Body(description="脚本路径")] = None,
    arguments: Annotated[list[str] | None, Body(description="参数")] = None,
    environment: Annotated[dict[str, str] | None, Body(description="环境变量")] = None,
) -> TaskTemplateResponse:
    template: Template | None = await Template.objects.get_or_none(id=id_, is_deleted=False)
    if template is None:
        raise invalid_request_exception("task template not found")
    await template.update(
        ["name", "description", "creator", "script_pack_path", "script_path", "arguments", "environment"],
        name=name,
        description=description,
        creator=creator,
        script_pack_path=script_pack_path,
        script_path=script_path,
        arguments=arguments,
        environment=environment,
    )
    return TaskTemplateResponse.from_db(template)


@router.post("/delete-template", description="删除任务模板")
async def delete_template(id_: Annotated[int, Query(alias="id", description="任务模板ID")]) -> TaskTemplateResponse | None:
    template: Template | None = await Template.objects.get_or_none(id=id_, is_deleted=False)
    if template is None:
        return None
    await template.update(["is_deleted"], is_deleted=True)
    return TaskTemplateResponse.from_db(template)
