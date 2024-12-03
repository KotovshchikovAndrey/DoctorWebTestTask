import asyncio
import importlib
import logging
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from typing import Any, Callable
from uuid import UUID

from redis import asyncio as aioredis

from broker import MessageBroker
from models import TaskExecute, TaskInDB, TaskResult, TaskStatus
from settings import settings

logger = logging.getLogger()


class Worker:
    _max_workers: int
    _max_retries: int

    broker: MessageBroker
    redis: aioredis.Redis

    def __init__(self, max_workers: int, max_retries: int) -> None:
        self._max_workers = max_workers
        self._max_retries = max_retries

    async def run(self) -> None:
        with ProcessPoolExecutor(max_workers=self._max_workers) as executor:
            async for message in self.broker.consume():
                task_execute = TaskExecute.model_validate_json(message)
                asyncio.create_task(self._execute_task(executor, task_execute))

    def task(self, function: Callable[..., Any]) -> Callable[..., Any]:
        async def delay(*args) -> UUID:
            async with self.redis.pipeline(transaction=True) as transaction:
                new_task = TaskInDB()
                await transaction.set(new_task.task_id, new_task.model_dump_json())

                task_execute = TaskExecute(
                    task_id=new_task.task_id,
                    create_time=new_task.create_time,
                    function_name=function.__name__,
                    function_args=args,
                )

                await self.broker.produce(message=task_execute.model_dump_json())
                await transaction.execute()
                logger.info(f"task with id={task_execute.task_id} in queue")

            return new_task.task_id

        function.delay = delay
        return function

    async def get_task_result(self, task_id: UUID) -> TaskResult | None:
        task_in_db = await self.redis.get(task_id.hex)
        if task_in_db is None:
            return

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

    async def _execute_task(
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
        try:
            await loop.run_in_executor(
                executor,
                function_to_execute,
                *task_execute.function_args,
            )
        except Exception as exc:
            logger.exception(f"execution of task with id={task_execute.task_id} failed")
            return await self._retry_task_execution(task_execute)

        completed_task = running_task.model_copy(
            update={"status": TaskStatus.COMPLETED, "exec_time": datetime.now(UTC)}
        )

        await self.redis.set(task_execute.task_id, completed_task.model_dump_json())
        logger.info(f"task with id={task_execute.task_id} completed")

    async def _retry_task_execution(self, task_execute: TaskExecute) -> None:
        if task_execute.retry_count == self._max_retries:
            failed_task = TaskInDB(
                task_id=task_execute.task_id,
                create_time=task_execute.create_time,
                status=TaskStatus.FAILED,
            )

            await self.redis.set(failed_task.task_id, failed_task.model_dump_json())
            logger.info(f"task with id={task_execute.task_id} rejected")
            return

        async with self.redis.pipeline(transaction=True) as transaction:
            retried_task = TaskInDB(
                task_id=task_execute.task_id,
                create_time=task_execute.create_time,
                status=TaskStatus.IN_QUEUE,
            )

            await transaction.set(task_execute.task_id, retried_task.model_dump_json())
            task_execute = task_execute.model_copy(
                update={"retry_count": task_execute.retry_count + 1}
            )

            await self.broker.produce(message=task_execute.model_dump_json())
            await transaction.execute()
            logger.info(f"task with id={task_execute.task_id} retried")


worker = Worker(
    max_workers=settings.worker.max_workers,
    max_retries=settings.worker.max_retries,
)
