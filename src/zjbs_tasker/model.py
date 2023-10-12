from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from zjbs_tasker.db import TaskRun, TaskTemplate


def short_string():
    return Field(max_length=255)


def long_string():
    return Field(max_length=65535)


class CompressMethod(StrEnum):
    not_compressed = "not_compressed"
    zip = "zip"
    tgz = "tgz"
    txz = "txz"


class CreateTaskTemplate(BaseModel):
    name: str = short_string()
    type: TaskTemplate.Type
    executable: list[str]
    environment: dict[str, Any]


class CreateTask(BaseModel):
    template: int
    name: str = short_string()
    argument: list[str]
    environment: dict[str, Any]
    retry_times: int = Field(0, ge=0)


class BaseTaskRun(BaseModel):
    task: int
    index: int = Field(ge=0)
    status: TaskRun.Status
    start_at: datetime | None = None
    end_at: datetime | None = None
