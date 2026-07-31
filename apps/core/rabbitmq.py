import aio_pika
from aio_pika.abc import AbstractChannel
from aio_pika.abc import AbstractConnection

from apps.core.config import settings


class RabbitMQService:
    def __init__(self):
        self._connection: AbstractConnection | None = None
        self._channel: AbstractChannel | None = None

    async def init_rabbitmq(self):
        self._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        self._channel = await self._connection.channel()
        # 声明 exchange（topic，durable）
        await self._channel.declare_exchange(
            settings.favorite_event_exchange,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

    async def close(self):
        if self._channel:
            await self._channel.close()
        if self._connection:
            await self._connection.close()

    @property
    def channel(self) -> AbstractChannel:
        if not self._channel:
            raise RuntimeError("RabbitMQ channel is not initialized")
        return self._channel


rabbitmq_service = RabbitMQService()


async def get_rabbitmq_channel() -> AbstractChannel | None:
    try:
        return rabbitmq_service.channel
    except RuntimeError:
        return None
