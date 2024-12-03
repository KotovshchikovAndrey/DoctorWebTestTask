from typing import Annotated

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class BrokerSettings(BaseSettings):
    host: Annotated[str, Field(alias="RABBITMQ_HOST", default="127.0.0.1")]
    port: Annotated[int, Field(alias="RABBITMQ_PORT", default=5672)]
    username: Annotated[str, Field(alias="RABBITMQ_USERNAME", default="guest")]
    password: Annotated[str, Field(alias="RABBITMQ_PASSWORD", default="guest")]
    queue_name: Annotated[str, Field(alias="RABBITMQ_QUEUE_NAME", default="task_queue")]

    def get_connection_url(self) -> str:
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/"


class DatabaseSettings(BaseSettings):
    host: Annotated[str, Field(alias="REDIS_HOST", default="127.0.0.1")]
    port: Annotated[int, Field(alias="REDIS_PORT", default=6379)]

    def get_connection_url(self) -> str:
        return f"redis://{self.host}:{self.port}"


class WorkerSettings(BaseSettings):
    max_workers: Annotated[int, Field(default=2)]
    max_retries: Annotated[int, Field(default=3)]


class Settings(BaseModel):
    database: DatabaseSettings = DatabaseSettings()
    broker: BrokerSettings = BrokerSettings()
    worker: WorkerSettings = WorkerSettings()


settings = Settings()
