import logging
from typing import AsyncGenerator, Protocol

import aio_pika
from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractQueue

logger = logging.getLogger()


class MessageBroker(Protocol):
    async def produce(self, message: str) -> None: ...

    async def consume(self) -> AsyncGenerator[str, None]: ...


class RabbitMQMessageBroker(MessageBroker):
    _connection: AbstractConnection
    _channel: AbstractChannel
    _queue_name: str

    def __init__(self, queue_name: str) -> None:
        self._queue_name = queue_name

    async def connect(self, connection_url: str, qos: int) -> None:
        self._connection = await aio_pika.connect(connection_url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=qos)

    async def produce(self, message: str) -> None:
        await self._channel.default_exchange.publish(
            Message(body=message.encode(), delivery_mode=DeliveryMode.PERSISTENT),
            routing_key=self._queue_name,
        )

    async def consume(self) -> AsyncGenerator[str, None]:
        queue: AbstractQueue = await self._channel.declare_queue(
            name=self._queue_name,
            durable=True,
        )

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                yield message.body.decode()
                await message.ack()

    async def disconnect(self) -> None:
        await self._connection.close()
