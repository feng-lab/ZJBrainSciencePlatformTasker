from typing import Annotated

from fastapi import APIRouter, Body, File, Form, Query, UploadFile
from pydantic import BaseModel

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
    has_executable: Annotated[bool, Body(description="是否可执行文件")],
    type_: Annotated[TaskInterpreter.Type, Body(alias="type", description="解释器类型")],
    executable: Annotated[list[str], Body(description="可执行文件")],
    environment: Annotated[dict[str, str], Body(description="环境变量")],
) -> TaskInterpreterResponse | None:
    created = await TaskInterpreter.objects.create(
        name=name,
        description=description,
        has_executable=has_executable,
        type=type_,
        executable=executable,
        environment=environment,
    )
    return TaskInterpreterResponse(**created.dict()) if created else None


@router.post("/GetTaskInterpreter", description="获取任务解释器")
async def get_task_interpreter(
    id_: Annotated[int, Query(alias="id", description="解释器ID")]
) -> TaskInterpreterResponse | None:
    obj = await TaskInterpreter.objects.get_or_none(id=id_, is_deleted=False)
    return TaskInterpreterResponse(**obj.dict()) if obj else None


@router.post("/ListTaskInterpreters", description="获取任务解释器列表")
async def list_task_interpreters(
    name: Annotated[str | None, Query(alias="name", description="名称")] = None,
    type_: Annotated[TaskInterpreter.Type | None, Query(alias="type", description="类型")] = None,
) -> list[TaskInterpreterResponse]:
    query = {}
    if name is not None:
        query["name__icontains"] = name
    if type_ is not None:
        query["type"] = type_
    if not query:
        raise invalid_request_exception("no query parameter is provided")
    objs = await TaskInterpreter.objects.all(**query, is_deleted=False)
    return [TaskInterpreterResponse(**obj.dict()) for obj in objs]


@router.post("/UploadTaskInterpreterPack", description="上传任务解释器文件")
async def upload_task_interpreter_pack(
    task_interpreter_id: Annotated[int, Form(description="任务解释器ID")],
    file: Annotated[UploadFile, File(description="任务解释器文件")],
    compress_method: Annotated[CompressMethod, Form(description="压缩方式")],
) -> None:
    task_interpreter = await TaskInterpreter.objects.get(id=task_interpreter_id, is_deleted=False)
    await upload_file(
        file.file,
        file.filename,
        compress_method,
        FileServerPath.TASK_INTERPRETER_DIR,
        f"{task_interpreter.id}_{task_interpreter.name}",
    )
