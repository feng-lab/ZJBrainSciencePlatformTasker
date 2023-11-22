from typing import Annotated

from fastapi import APIRouter, Body, Query
from pydantic import BaseModel

from zjbs_tasker.db import Interpreter
from zjbs_tasker.util import invalid_request_exception

router = APIRouter(tags=["interpreter"])


class TaskInterpreterResponse(BaseModel):
    id: int
    name: str
    description: str
    creator: int
    type: Interpreter.Type
    executable_pack_path: str | None
    executable_path: str | None
    environment: dict[str, str]


@router.post("/create-interpreter", description="创建任务解释器")
async def create_interpreter(
    name: Annotated[str, Body(max_length=255, description="名称")],
    description: Annotated[str, Body(description="描述")],
    creator: Annotated[int, Body(description="创建者ID")],
    type_: Annotated[Interpreter.Type, Body(alias="type", description="解释器类型")],
    executable_pack_path: Annotated[str | None, Body(description="可执行文件包FileServer路径")],
    executable_path: Annotated[str | None, Body(description="可执行文件相对路径")],
    environment: Annotated[dict[str, str], Body(description="环境变量")],
) -> TaskInterpreterResponse:
    interpreter: Interpreter = await Interpreter.objects.create(
        name=name,
        description=description,
        creator=creator,
        type=type_,
        executable_pack_path=executable_pack_path,
        executable_path=executable_path,
        environment=environment,
    )
    return TaskInterpreterResponse(**interpreter.dict())


@router.post("/get-interpreter", description="获取任务解释器")
async def get_interpreter(
    id_: Annotated[int, Query(alias="id", description="解释器ID")]
) -> TaskInterpreterResponse | None:
    interpreter: Interpreter | None = await Interpreter.objects.get_or_none(id=id_, is_deleted=False)
    return TaskInterpreterResponse(**interpreter.dict()) if interpreter else None


@router.post("/list-interpreters", description="获取任务解释器列表")
async def list_interpreters(
    name: Annotated[str | None, Query(alias="name", description="名称")] = None,
    type_: Annotated[Interpreter.Type | None, Query(alias="type", description="类型")] = None,
    offset: Annotated[int, Query(description="分页偏移量")] = 0,
    limit: Annotated[int, Query(description="分页大小")] = 10,
) -> list[TaskInterpreterResponse]:
    query = {"is_deleted": False}
    if name is not None:
        query["name__icontains"] = name
    if type_ is not None:
        query["type"] = type_
    interpreters: list[Interpreter] = await Interpreter.objects.offset(offset).limit(limit).all(**query)
    return [TaskInterpreterResponse(**interpreter.dict()) for interpreter in interpreters]


@router.post("/update-interpreter", description="更新任务解释器")
async def update_interpreter(
    id_: Annotated[int, Body(alias="id", description="解释器ID")],
    name: Annotated[str | None, Body(max_length=255, description="名称")] = None,
    description: Annotated[str | None, Body(description="描述")] = None,
    type_: Annotated[Interpreter.Type | None, Body(alias="type", description="解释器类型")] = None,
    executable_pack_path: Annotated[str | None, Body(description="可执行文件包FileServer路径")] = None,
    executable_path: Annotated[str, Body(description="可执行文件")] = None,
    environment: Annotated[dict[str, str] | None, Body(description="环境变量")] = None,
) -> TaskInterpreterResponse:
    interpreter: Interpreter | None = await Interpreter.objects.get_or_none(id=id_, is_deleted=False)
    if interpreter is None:
        raise invalid_request_exception("task interpreter not found")
    await interpreter.update(
        ["name", "description", "type", "executable_pack_path", "executable_path", "environment"],
        name=name,
        description=description,
        type=type_,
        executable_pack_path=executable_pack_path,
        executable_path=executable_path,
        environment=environment,
    )
    return TaskInterpreterResponse(**interpreter.dict())


@router.post("/delete-interpreter", description="删除任务解释器")
async def delete_interpreter(
    id_: Annotated[int, Query(alias="id", description="解释器ID")]
) -> TaskInterpreterResponse | None:
    interpreter: Interpreter | None = await Interpreter.objects.get_or_none(id=id_, is_deleted=False)
    if interpreter is None:
        return None
    await interpreter.update(["is_deleted"], is_deleted=True)
    return TaskInterpreterResponse(**interpreter.dict())
