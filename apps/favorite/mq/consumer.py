import asyncio

import aio_pika
from aio_pika import IncomingMessage, Message
from aio_pika.abc import AbstractChannel, AbstractQueue, DeliveryMode
from logger import logger
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.core.config import settings
from apps.core.database import SessionLocal
from apps.favorite.common.constants import MQ_MAX_RETRIES
from apps.favorite.repositories.operation_log import operation_log_create
from apps.favorite.schemas.event import FavoriteAddedEvent


async def setup_operation_log_queues(channel: AbstractChannel) -> AbstractQueue:
    # DLQ
    await channel.declare_queue(settings.favorite_operation_log_dlq, durable=True)

    # 主队列+死信到DLQ
    queue = await channel.declare_queue(
        settings.favorite_operation_log_queue,
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": settings.favorite_operation_log_dlq,
        },
    )

    # 绑定exchange
    exchange = await channel.get_exchange(settings.favorite_event_exchange)
    await queue.bind(exchange, routing_key=settings.favorite_event_routing_key)

    return queue


async def process_favorite_added_message(session: AsyncSession, body: bytes) -> None:

    fae = FavoriteAddedEvent.model_validate_json(body)
    try:
        async with session.begin():
            await operation_log_create(
                session,
                event_id=fae.event_id,
                user_id=fae.user_id,
                folder_id=fae.folder_id,
                intelligence_id=fae.intelligence_id,
                action=fae.action,
            )
    except IntegrityError:
        logger.info("Event %s already exists (IntegrityError), acking.", fae.event_id)
        return


def _get_retry_count(message: IncomingMessage):
    raw = (message.headers or {}).get("x-retry-count", 0)
    return int(raw)


async def handle_message(message: IncomingMessage, channel: AbstractChannel):
    try:
        async with SessionLocal() as session:
            await process_favorite_added_message(session, message.body)

        await message.ack()
    except ValidationError as e:
        logger.error("Invalid event payload: %s", e)
        await message.reject(requeue=False)

    except Exception as e:
        logger.error("Consume failed: %s", e, exc_info=True)
        retry_count = _get_retry_count(message)

        if retry_count >= MQ_MAX_RETRIES - 1:
            await message.reject(requeue=False)
        else:
            new_retry_count = retry_count + 1
            logger.warning(
                "Re-publishing message for retry %d/%d",
                new_retry_count,
                MQ_MAX_RETRIES,
            )
            headers = dict(message.headers or {})
            headers["x-retry-count"] = new_retry_count
            exchange = await channel.get_exchange(settings.favorite_event_exchange)
            await exchange.publish(
                Message(
                    body=message.body,
                    headers=headers,
                    content_type=message.content_type or "application/json",
                    delivery_mode=message.delivery_mode or DeliveryMode.PERSISTENT,
                ),
                routing_key=settings.favorite_event_routing_key,
            )
            await message.ack()


async def run_consumer() -> None:
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await setup_operation_log_queues(channel)

    async def on_message(message: IncomingMessage) -> None:
        await handle_message(message, channel)

    await queue.consume(on_message)
    logger.info("Favorite operation log consumer started")

    try:
        await asyncio.Future()
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(run_consumer())
