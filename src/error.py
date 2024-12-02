from uuid import UUID


class WorkerError(Exception):
    def __str__(self) -> str:
        return "Worker error occured"


class TaskNotFound(WorkerError):
    task_id: UUID

    def __init__(self, task_id: UUID) -> None:
        self.task_id = task_id

    def __str__(self) -> str:
        return f"Task with id={self.task_id} does not exists"


class TaskDelayError(WorkerError):
    def __str__(self) -> str:
        return f"Task creation failed"
