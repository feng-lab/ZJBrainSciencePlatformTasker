from datetime import datetime
from enum import StrEnum
from typing import Any

import databases
import sqlalchemy
from ormar import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Model,
    ModelMeta,
    ReferentialAction,
    String,
)
from pydantic import Json
from sqlalchemy import func
from sqlalchemy.sql import expression

from zjbs_tasker.settings import settings

database = databases.Database(settings.DATABASE_URL)
metadata = sqlalchemy.MetaData()


class BaseMeta(ModelMeta):
    database = database
    metadata = metadata


def short_string(**kwargs):
    return String(max_length=255, **kwargs)


def long_string(**kwargs):
    return String(max_length=65535, **kwargs)


class ModelMixin:
    # 主键
    id: int = BigInteger(primary_key=True, autoincrement=True)
    # 创建时间
    create_at: datetime = DateTime(server_default=func.now())
    # 修改时间
    modified_at: datetime = DateTime(server_default=func.now())
    # 是否被删除
    is_deleted: bool = Boolean(server_default=expression.false())


# 任务模板
class TaskTemplate(Model, ModelMixin):
    class Meta(BaseMeta):
        tablename = "task_template"

    # 允许的任务类型
    class Type(StrEnum):
        # 可执行文件
        executable = "executable"
        # Python脚本或模块
        python = "python"

    # 名称
    name: str = short_string()
    # 类型
    type: Type = Enum(enum_class=Type)
    # 可执行文件
    executable: str = long_string()
    # 参数
    argument: Json[list[str]] = JSON()
    # 环境变量
    environment: Json[dict[str, Any]] = JSON()


# 任务
class Task(Model, ModelMixin):
    class Meta(BaseMeta):
        tablename = "task"

    # 名称
    name: str = short_string()
    # 创建者ID
    creator_id: int = BigInteger()
    # 源文件路径
    source_files: Json[list[str]] = JSON()
    # 允许重试的次数
    retry_times: int = Integer(minimum=0)

    # 模板
    template: TaskTemplate = ForeignKey(TaskTemplate)


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

    # 任务运行状态
    status: Status = Enum(enum_class=Status)
    # 开始时间
    start_at: datetime | None = DateTime(nullable=True)
    # 结束时间
    end_at: datetime | None = DateTime(nullable=True)

    # 任务
    task: Task = ForeignKey(
        Task, related_name="runs", onupdate=ReferentialAction.CASCADE, ondelete=ReferentialAction.CASCADE
    )
