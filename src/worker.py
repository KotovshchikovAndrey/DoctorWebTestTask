import asyncio
import importlib
import logging
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from typing import Any, Callable
from uuid import UUID

from redis import asyncio as aioredis

from broker import MessageBroker
from error import TaskDelayError, TaskNotFound
from models import TaskExecute, TaskInDB, TaskResult, TaskStatus
from settings import settings

logger = logging.getLogger()


class Worker:
    _max_workers: int
    broker: MessageBroker
    redis: aioredis.Redis

    def __init__(self, max_workers: int) -> None:
        self._max_workers = max_workers

    async def run(self) -> None:
        with ProcessPoolExecutor(max_workers=self._max_workers) as executor:
            async for message in self.broker.consume():
                task_execute = TaskExecute.model_validate_json(message)
                asyncio.create_task(
                    self._execute_task_function(
                        executor=executor,
                        task_execute=task_execute,
                    ),
                )

    def task(self, function: Callable[..., Any]) -> Callable[..., Any]:
        async def delay(*args) -> UUID:
            task = TaskInDB()
            await self.redis.set(task.task_id, task.model_dump_json())

            task_execute = TaskExecute(
                task_id=task.task_id,
                status=task.status,
                function_name=function.__name__,
                function_args=args,
                create_time=task.create_time,
            )

            try:
                await self.broker.produce(message=task_execute.model_dump_json())
            except Exception:
                logger.exception("exception occurred while producing message")
                await self.redis.delete(task.task_id)
                raise TaskDelayError()

            return task.task_id

        function.delay = delay
        return function

    async def get_task_result(self, task_id: UUID) -> TaskResult:
        task_in_db = await self.redis.get(task_id.hex)
        if task_in_db is None:
            raise TaskNotFound(task_id)

        task = TaskInDB.model_validate_json(task_in_db)
        task_result = TaskResult(
            status=task.status,
            start_time=task.start_time,
            create_time=task.create_time,
        )

        if task.status != TaskStatus.COMPLETED:
            return task_result

        return task_result.model_copy(
            update={"time_to_execute": (task.exec_time - task.start_time).seconds}
        )

    async def _execute_task_function(
        self,
        executor: ProcessPoolExecutor,
        task_execute: TaskExecute,
    ) -> None:
        tasks_module = importlib.import_module("tasks")
        function_to_execute = getattr(tasks_module, task_execute.function_name)

        running_task = TaskInDB(
            task_id=task_execute.task_id,
            create_time=task_execute.create_time,
            start_time=datetime.now(UTC),
            status=TaskStatus.RUN,
        )

        await self.redis.set(task_execute.task_id, running_task.model_dump_json())
        logger.info(f"task with id={task_execute.task_id} running")

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            executor,
            function_to_execute,
            *task_execute.function_args,
        )

        completed_task = running_task.model_copy(
            update={"status": TaskStatus.COMPLETED, "exec_time": datetime.now(UTC)}
        )

        await self.redis.set(task_execute.task_id, completed_task.model_dump_json())
        logger.info(f"task with id={task_execute.task_id} completed")


worker = Worker(max_workers=settings.max_workers)
