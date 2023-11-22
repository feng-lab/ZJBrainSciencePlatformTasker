from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Body, Query
from pydantic import BaseModel, Json

from zjbs_tasker.db import Run, Status, Task
from zjbs_tasker.server import queue
from zjbs_tasker.worker import execute_task_run

router = APIRouter(tags=["task"])


class TaskResponse(BaseModel):
    id: int
    template: int
    name: str
    description: str
    creator: int
    depends: list[int]
    status: Status
    start_at: datetime | None
    end_at: datetime | None
    source_file_dir: str | None
    output_file_dir: str | None
    arguments: list[str]
    environment: dict[str, str]
    user_data: Json

    @staticmethod
    def from_db(task: Task | None) -> Optional["TaskResponse"]:
        return (
            TaskResponse(
                id=task.id,
                template=task.template.id,
                name=task.name,
                description=task.description,
                creator=task.creator,
                depends=task.depends,
                status=task.status,
                start_at=task.start_at,
                end_at=task.end_at,
                source_file_dir=task.source_file_dir,
                output_file_dir=task.output_file_dir,
                arguments=task.arguments,
                environment=task.environment,
                user_data=task.user_data,
            )
            if task
            else None
        )


@router.post("/create-task", description="创建任务")
async def create_task(
    template: Annotated[int, Body(description="任务模板ID")],
    name: Annotated[str, Body(max_length=255, description="名称")],
    description: Annotated[str, Body(description="描述")],
    creator: Annotated[int, Body(description="创建者ID")],
    depends: Annotated[list[int], Body(description="依赖的任务ID")],
    source_file_dir: Annotated[str | None, Body(description="源文件夹")],
    output_file_dir: Annotated[str | None, Body(description="目标文件夹")],
    arguments: Annotated[list[str], Body(description="参数")],
    environment: Annotated[dict[str, str], Body(description="环境变量")],
    user_data: Annotated[Json, Body(description="用户自定义数据")],
) -> TaskResponse:
    task = await Task.objects.create(
        template=template,
        name=name,
        description=description,
        creator=creator,
        depends=depends,
        status=Status.pending,
        start_at=None,
        end_at=None,
        source_file_dir=source_file_dir,
        output_file_dir=output_file_dir,
        arguments=arguments,
        environment=environment,
        user_data=user_data,
    )
    return TaskResponse.from_db(task)


@router.post("/get-task", description="获取任务")
async def get_task(id_: Annotated[int, Body(description="任务ID")]) -> TaskResponse | None:
    task = await Task.objects.get(id=id_, is_deleted=False)
    return TaskResponse.from_db(task)


@router.post("/list-task", description="获取任务列表")
async def list_task(
    template: Annotated[int | None, Query(description="模板")] = None,
    name: Annotated[str | None, Query(description="任务名称")] = None,
    creator: Annotated[int | None, Query(description="创建者ID")] = None,
    status: Annotated[Status | None, Query(description="任务状态")] = None,
    offset: Annotated[int, Query(description="分页偏移量")] = 0,
    limit: Annotated[int, Query(description="分页大小")] = 10,
) -> list[TaskResponse]:
    query = {"is_deleted": False}
    if template is not None:
        query["template"] = template
    if name is not None:
        query["name__icontains"] = name
    if creator is not None:
        query["creator"] = creator
    if status is not None:
        query["status"] = status
    tasks: list[Task] = await Task.objects.filter(**query).offset(offset).limit(limit).all()
    return [TaskResponse.from_db(task) for task in tasks]


@router.post("/update-task", description="更新任务")
async def update_task(
    id_: Annotated[int, Body(description="任务ID")],
    template: Annotated[int, Body(description="任务模板ID")],
    name: Annotated[str, Body(max_length=255, description="名称")],
    description: Annotated[str, Body(description="描述")],
    creator: Annotated[int, Body(description="创建者ID")],
    depends: Annotated[list[int], Body(description="依赖的任务ID")],
    status: Annotated[Status, Body(description="任务状态")],
    start_at: Annotated[datetime | None, Body(description="开始时间")],
    end_at: Annotated[datetime | None, Body(description="结束时间")],
    source_file_dir: Annotated[str | None, Body(description="源文件夹")],
    output_file_dir: Annotated[str | None, Body(description="目标文件夹")],
    arguments: Annotated[list[str], Body(description="参数")],
    environment: Annotated[dict[str, str], Body(description="环境变量")],
    user_data: Annotated[Json, Body(description="用户自定义数据")],
) -> TaskResponse:
    task = await Task.objects.get(id=id_, is_deleted=False)
    await task.update(
        template=template,
        name=name,
        description=description,
        creator=creator,
        depends=depends,
        status=status,
        start_at=start_at,
        end_at=end_at,
        source_file_dir=source_file_dir,
        output_file_dir=output_file_dir,
        arguments=arguments,
        environment=environment,
        user_data=user_data,
    )
    return TaskResponse.from_db(task)


@router.post("/delete-task", description="删除任务")
async def delete_task(id_: Annotated[int, Body(description="任务ID")]) -> TaskResponse | None:
    task = await Task.objects.get_or_none(id=id_, is_deleted=False)
    if task is None:
        return None
    await task.update(["is_deleted"], is_deleted=True)
    return TaskResponse.from_db(task)


@router.post("/start-task", description="开始任务")
async def start_task(task_id: Annotated[int, Body(description="任务ID")]) -> None:
    task = await Task.objects.get(id=task_id, is_deleted=False)
    task_run = await Run.objects.create(task=task.id, index=0, status=Run.Status.pending)
    queue.enqueue(execute_task_run, task_run.id)


@router.post("/list-task-runs", description="列出任务运行记录", response_model=list[Run])
async def list_task_runs(task_id: int) -> list[Run]:
    task = await Task.objects.select_related("runs").get(id=task_id, is_deleted=False)
    return [task_run.dict(exclude={"task"}) for task_run in task.runs if not task_run.is_deleted]


async def start_run_task(task_id: int, index: int = 1) -> None:
    task_run = await Run.objects.create(task=task_id, index=index, status=Run.Status.pending)
    queue.enqueue(execute_task_run, task_run.id)
