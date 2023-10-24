import asyncio
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import asyncpg
import databases
import sqlalchemy
from asyncpg import Connection
from databases import Database
from ormar import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, Model, ModelMeta, String, Text
from sqlalchemy import MetaData, func
from sqlalchemy.sql import expression

from zjbs_tasker.settings import settings

database: Database = databases.Database(settings.DATABASE_URL)
metadata: MetaData = sqlalchemy.MetaData()


class BaseMeta(ModelMeta):
    database = database
    metadata = metadata


def short_string(**kwargs):
    return String(max_length=255, **kwargs)


def long_string(**kwargs):
    return String(max_length=65535, **kwargs)


class ModelMixin:
    # 主键
    id: int = Integer(primary_key=True, autoincrement=True)
    # 创建时间
    create_at: datetime = DateTime(server_default=func.now())
    # 修改时间
    modified_at: datetime = DateTime(server_default=func.now())
    # 是否被删除
    is_deleted: bool = Boolean(server_default=expression.false())


# 任务可执行文件的解释器
class TaskInterpreter(Model, ModelMixin):
    class Meta(BaseMeta):
        tablename = "task_interpreter"

    # 允许的解释器类型
    class Type(StrEnum):
        # 可执行文件
        executable = "executable"
        # Python脚本或模块
        python = "python"
        # Node.js脚本
        nodejs = "nodejs"

    # 名称
    name: str = short_string()
    # 描述
    description: str = Text()
    # 是否有可执行文件
    has_executable: bool = Boolean()
    # 类型
    type: Type = Enum(enum_class=Type)
    # 可执行文件
    executable: list[str] = JSON()
    # 环境变量
    environment: dict[str, Any] = JSON()


# 任务模板
class TaskTemplate(Model, ModelMixin):
    class Meta(BaseMeta):
        tablename = "task_template"

    # 名称
    name: str = short_string()
    # 描述
    description: str = Text()
    # 是否有脚本
    has_script: bool = Boolean()
    # 参数
    arguments: list[str] = JSON()
    # 环境变量
    environment: dict[str, Any] = JSON()

    # 解释器
    interpreter: TaskInterpreter = ForeignKey(TaskInterpreter, related_name="templates")


# 任务
class Task(Model, ModelMixin):
    class Meta(BaseMeta):
        tablename = "task"

    # 名称
    name: str = short_string()
    # 描述
    description: str = Text()
    # 是否有源文件
    has_source_file: bool = Boolean()
    # 参数
    arguments: list[str] = JSON()
    # 环境变量
    environment: dict[str, Any] = JSON()
    # 允许重试的次数
    retry_times: int = Integer(minimum=0)

    # 模板
    template: TaskTemplate = ForeignKey(TaskTemplate, related_name="tasks", nullable=False)


# 任务的一次运行
class TaskRun(Model, ModelMixin):
    class Meta(BaseMeta):
        tablename = "task_run"

    # 任务运行的状态
    class Status(StrEnum):
        # 等待运行
        pending = "pending"
        # 运行中
        running = "running"
        # 成功结束
        success = "success"
        # 失败
        failed = "failed"
        # 取消
        canceled = "canceled"

    # 序号
    index: int = Integer()
    # 任务运行状态
    status: Status = Enum(enum_class=Status)
    # 开始时间
    start_at: datetime | None = DateTime(nullable=True)
    # 结束时间
    end_at: datetime | None = DateTime(nullable=True)

    # 任务
    task: Task = ForeignKey(Task, related_name="runs", nullable=False)


async def run_pg_script(path: Path | str) -> None:
    connection: Connection | None = None
    try:
        connection = await asyncpg.connect(settings.DATABASE_URL)
        await connection.execute(path.read_text(encoding="UTF-8"))
    finally:
        if connection and not connection.is_closed():
            await connection.close()


if __name__ == "__main__":
    create_all_script = Path(__file__).parent.parent.parent / "alembic" / "sql" / "create_all.sql"
    asyncio.run(run_pg_script(create_all_script))
