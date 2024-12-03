import enum
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskStatus(enum.StrEnum):
    RUN = "Run"
    IN_QUEUE = "In Queue"
    COMPLETED = "Completed"
    FAILED = "Failed"


class CoreModel(BaseModel):
    class Config:
        frozen = True
        extra = "forbid"


class TaskInDB(CoreModel):
    task_id: Annotated[str, Field(default_factory=lambda: uuid4().hex)]
    status: Annotated[TaskStatus, Field(default=TaskStatus.IN_QUEUE)]
    create_time: Annotated[datetime, Field(default_factory=lambda: datetime.now(UTC))]
    start_time: Annotated[datetime | None, Field(default=None)]
    exec_time: Annotated[datetime | None, Field(default=None)]


class TaskResult(CoreModel):
    status: Annotated[TaskStatus, Field(default=TaskStatus.IN_QUEUE)]
    create_time: datetime
    start_time: Annotated[datetime | None, Field(default=None)]
    time_to_execute: Annotated[int | None, Field(ge=0, default=None)]


class TaskExecute(CoreModel):
    task_id: str
    create_time: datetime
    function_name: str
    function_args: tuple
    retry_count: Annotated[int, Field(ge=0, default=0)]
