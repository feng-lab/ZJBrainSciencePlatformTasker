from typing import Annotated

from fastapi import APIRouter, Body, File, Form, Query, UploadFile
from pydantic import BaseModel
from zjbs_file_client import delete

from zjbs_tasker.db import TaskInterpreter
from zjbs_tasker.model import CompressMethod
from zjbs_tasker.settings import FileServerPath
from zjbs_tasker.util import invalid_request_exception, upload_file

router = APIRouter(tags=["interpreter"])


class TaskInterpreterResponse(BaseModel):
    id: int
    name: str
    description: str
    has_executable: bool
    type: TaskInterpreter.Type
    executable: list[str]
    environment: dict[str, str]


@router.post("/CreateTaskInterpreter", description="创建任务解释器")
async def create_task_interpreter(
    name: Annotated[str, Body(max_length=255, description="名称")],
    description: Annotated[str, Body(description="描述")],
    type_: Annotated[TaskInterpreter.Type, Body(alias="type", description="解释器类型")],
    executable: Annotated[list[str], Body(description="可执行文件")],
    environment: Annotated[dict[str, str], Body(description="环境变量")],
) -> TaskInterpreterResponse:
    interpreter: TaskInterpreter = await TaskInterpreter.objects.create(
        name=name,
        description=description,
        has_executable=False,
        type=type_,
        executable=executable,
        environment=environment,
    )
    return TaskInterpreterResponse(**interpreter.dict())


@router.post("/GetTaskInterpreter", description="获取任务解释器")
async def get_task_interpreter(
    id_: Annotated[int, Query(alias="id", description="解释器ID")]
) -> TaskInterpreterResponse | None:
    interpreter: TaskInterpreter | None = await TaskInterpreter.objects.get_or_none(id=id_, is_deleted=False)
    return TaskInterpreterResponse(**interpreter.dict()) if interpreter else None


@router.post("/ListTaskInterpreters", description="获取任务解释器列表")
async def list_task_interpreters(
    name: Annotated[str | None, Query(alias="name", description="名称")] = None,
    type_: Annotated[TaskInterpreter.Type | None, Query(alias="type", description="类型")] = None,
    offset: Annotated[int, Query(description="分页偏移量")] = 0,
    limit: Annotated[int, Query(description="分页大小")] = 10,
) -> list[TaskInterpreterResponse]:
    query = {"is_deleted": False}
    if name is not None:
        query["name__icontains"] = name
    if type_ is not None:
        query["type"] = type_
    interpreters: list[TaskInterpreter] = await TaskInterpreter.objects.offset(offset).limit(limit).all(**query)
    return [TaskInterpreterResponse(**interpreter.dict()) for interpreter in interpreters]


@router.post("/UpdateTaskInterpreter", description="更新任务解释器")
async def update_task_interpreter(
    id_: Annotated[int, Body(alias="id", description="解释器ID")],
    name: Annotated[str | None, Body(max_length=255, description="名称")] = None,
    description: Annotated[str | None, Body(description="描述")] = None,
    type_: Annotated[TaskInterpreter.Type | None, Body(alias="type", description="解释器类型")] = None,
    executable: Annotated[list[str] | None, Body(description="可执行文件")] = None,
    environment: Annotated[dict[str, str] | None, Body(description="环境变量")] = None,
) -> TaskInterpreterResponse:
    interpreter: TaskInterpreter | None = await TaskInterpreter.objects.get_or_none(id=id_, is_deleted=False)
    if interpreter is None:
        raise invalid_request_exception("task interpreter not found")
    update_fields = {}
    if name is not None:
        update_fields["name"] = name
    if description is not None:
        update_fields["description"] = description
    if type_ is not None:
        update_fields["type"] = type_
    if executable is not None:
        update_fields["executable"] = executable
    if environment is not None:
        update_fields["environment"] = environment
    await interpreter.update(list(update_fields.keys()), **update_fields)
    return TaskInterpreterResponse(**interpreter.dict())


@router.post("/DeleteTaskInterpreter", description="删除任务解释器")
async def delete_task_interpreter(
    id_: Annotated[int, Query(alias="id", description="解释器ID")]
) -> TaskInterpreterResponse | None:
    interpreter: TaskInterpreter | None = await TaskInterpreter.objects.get_or_none(id=id_, is_deleted=False)
    if interpreter is None:
        return None
    await interpreter.update(["is_deleted"], is_deleted=True)
    return TaskInterpreterResponse(**interpreter.dict())


@router.post("/UploadTaskInterpreterExecutable", description="上传任务解释器文件")
async def upload_task_interpreter_executable(
    id_: Annotated[int, Form(alias="id", description="任务解释器ID")],
    file: Annotated[UploadFile, File(description="任务解释器文件")],
    compress_method: Annotated[CompressMethod, Form(description="压缩方式")],
) -> None:
    interpreter: TaskInterpreter | None = await TaskInterpreter.objects.get_or_none(id=id_, is_deleted=False)
    if interpreter is None:
        raise invalid_request_exception("task interpreter not found")
    await upload_file(
        file.file,
        file.filename,
        compress_method,
        FileServerPath.TASK_INTERPRETER_DIR,
        f"{interpreter.id}_{interpreter.name}",
    )
    await interpreter.update(["has_executable"], has_executable=True)


@router.post("/DeleteTaskInterpreterExecutable", description="删除任务解释器文件")
async def delete_task_interpreter_executable(id_: Annotated[int, Query(alias="id", description="任务解释器ID")]) -> None:
    interpreter: TaskInterpreter | None = await TaskInterpreter.objects.get_or_none(id=id_, is_deleted=False)
    if interpreter is None:
        raise invalid_request_exception("task interpreter not found")
    if interpreter.has_executable:
        await delete(FileServerPath.interpreter_executable_path(interpreter.id, interpreter.name))
        await interpreter.update(["has_executable"], has_executable=False)
