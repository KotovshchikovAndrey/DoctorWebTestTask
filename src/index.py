import asyncio
import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException, status
from redis import asyncio as aioredis

from broker import RabbitMQMessageBroker
from models import TaskResult
from settings import settings
from tasks import task
from worker import worker

logger = logging.getLogger()


@asynccontextmanager
async def lifespan(_: FastAPI):
    worker.broker = RabbitMQMessageBroker(queue_name=settings.broker.queue_name)
    await worker.broker.connect(
        connection_url=settings.broker.get_connection_url(),
        qos=settings.worker.max_workers,
    )

    worker.redis = await aioredis.from_url(
        settings.database.get_connection_url(),
        decode_responses=True,
    )

    asyncio.create_task(worker.run())

    yield

    await worker.broker.disconnect()
    await worker.redis.close()


app = FastAPI(lifespan=lifespan)


@app.post("/tasks")
async def create_task():
    task_id = await task.delay()
    return {
        "message": "Task created successfully",
        "task_id": task_id,
    }


@app.get("/tasks/{task_id:str}", response_model=TaskResult)
async def get_task_result(task_id: UUID):
    task_result = await worker.get_task_result(task_id)
    if task_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id={task_id} does not exists",
        )

    return task_result
