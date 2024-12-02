import asyncio
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException, status
from redis import asyncio as aioredis

from broker import RabbitMQMessageBroker
from error import TaskDelayError, TaskNotFound
from models import TaskResult
from settings import settings
from tasks import task
from worker import worker


@asynccontextmanager
async def lifespan(_: FastAPI):
    worker.broker = RabbitMQMessageBroker(queue_name=settings.broker.queue_name)
    await worker.broker.connect(
        connection_url=settings.broker.get_connection_url(),
        qos=settings.max_workers,
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
    try:
        task_id = await task.delay()
        return {
            "message": "Task created successfully",
            "task_id": task_id,
        }
    except TaskDelayError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": str(exc)},
        )


@app.get("/tasks/{task_id:str}", response_model=TaskResult)
async def get_task_result(task_id: UUID):
    try:
        task_result = await worker.get_task_result(task_id)
        return task_result
    except TaskNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(exc)},
        )
