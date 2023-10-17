from datetime import datetime
from enum import StrEnum
from typing import Any

import databases
import sqlalchemy
from databases import Database
from ormar import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, Model, ModelMeta, String, Text
from pydantic import Json
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
        # Python脚本或模块
        python = "python"
        # Node.js脚本
        nodejs = "nodejs"

    # 名称
    name: str = short_string()
    # 类型
    type: Type = Enum(enum_class=Type)


# 任务模板
class TaskTemplate(Model, ModelMixin):
    class Meta(BaseMeta):
        tablename = "task_template"

    # 名称
    name: str = short_string()
    # 描述
    description: str = Text()
    # 可执行文件
    executable: Json[list[str]] = JSON()
    # 环境变量
    environment: Json[dict[str, Any]] = JSON()

    # 解释器
    interpreter: TaskInterpreter | None = ForeignKey(TaskInterpreter, related_name="templates", nullable=True)


# 任务
class Task(Model, ModelMixin):
    class Meta(BaseMeta):
        tablename = "task"

    # 名称
    name: str = short_string()
    # 参数
    argument: Json[list[str]] = JSON()
    # 环境变量
    environment: Json[dict[str, Any]] = JSON()
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


if __name__ == "__main__":
    engine = sqlalchemy.create_engine(settings.DATABASE_URL, echo=True)
    metadata.drop_all(engine)
    metadata.create_all(engine)
