from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from zjbs_tasker.db import Run


def short_string():
    return Field(max_length=255)


def long_string():
    return Field(max_length=65535)


class CompressMethod(StrEnum):
    not_compressed = "not_compressed"
    zip = "zip"
    tgz = "tgz"
    txz = "txz"


class BaseTaskRun(BaseModel):
    task: int
    index: int = Field(ge=0)
    status: Run.Status
    start_at: datetime | None = None
    end_at: datetime | None = None
