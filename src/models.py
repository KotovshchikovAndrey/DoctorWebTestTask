import enum
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskStatus(enum.StrEnum):
    RUN = "Run"
    IN_QUEUE = "In Queue"
    COMPLETED = "Completed"


class CoreModel(BaseModel):
    class Config:
        frozen = True
        extra = "forbid"


class TaskBase(CoreModel):
    status: Annotated[TaskStatus, Field(default=TaskStatus.IN_QUEUE)]
    create_time: Annotated[datetime, Field(default_factory=lambda: datetime.now(UTC))]


class TaskInDB(TaskBase):
    task_id: Annotated[str, Field(default_factory=lambda: uuid4().hex)]
    start_time: Annotated[datetime | None, Field(default=None)]
    exec_time: Annotated[datetime | None, Field(default=None)]


class TaskResult(TaskBase):
    start_time: Annotated[datetime | None, Field(default=None)]
    time_to_execute: Annotated[int | None, Field(ge=0, default=None)]


class TaskExecute(TaskBase):
    task_id: Annotated[str, Field(default_factory=lambda: uuid4().hex)]
    function_name: str
    function_args: tuple
