"""MQ 集成测试 fixture：需本地 RabbitMQ；不可用时 skip。"""

import aio_pika
import pytest_asyncio

from apps.core.config import settings
from apps.favorite.mq.consumer import setup_operation_log_queues


@pytest_asyncio.fixture
async def mq_setup():
    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url, timeout=5)
    except Exception as exc:
        pytest.skip(f"RabbitMQ not available: {exc}")

    channel = await connection.channel()
    await channel.declare_exchange(
        settings.favorite_event_exchange,
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )
    queue = await setup_operation_log_queues(channel)
    dlq = await channel.declare_queue(settings.favorite_operation_log_dlq, durable=True)
    await queue.purge()
    await dlq.purge()

    yield channel, queue, dlq

    await channel.close()
    await connection.close()
