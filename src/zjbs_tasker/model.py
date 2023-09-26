from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from zjbs_tasker.db import TaskRun, TaskTemplate


def short_string():
    return Field(max_length=255)


def long_string():
    return Field(max_length=65535)


class CreateTaskTemplate(BaseModel):
    name: str = short_string()
    type: TaskTemplate.Type
    executable: str = long_string()
    argument: list[str]
    environment: dict[str, Any]


class CreateTask(BaseModel):
    template: int
    name: str = short_string()
    creator_id: int
    source_files: list[str]
    retry_times: int = Field(ge=0)


class CreateTaskRun(BaseModel):
    task: int
    status: TaskRun.Status
    start_at: datetime | None = None
    end_at: datetime | None = None
