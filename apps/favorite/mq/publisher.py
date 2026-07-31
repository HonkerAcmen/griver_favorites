import uuid
from datetime import datetime

from aio_pika import Message, DeliveryMode
from aio_pika.abc import AbstractChannel
from logger import logger

from apps.core.config import settings
from apps.favorite.schemas.event import FavoriteAddedEvent


async def publish_favorite_added(
    channel: AbstractChannel | None,
    *,
    user_id: uuid.UUID,
    folder_id: uuid.UUID,
    intelligence_id: uuid.UUID,
) -> uuid.UUID:
    """发收藏事件；返回 event_id。失败只打 ERROR，不抛异常。"""
    event_id = uuid.uuid4()
    fae = FavoriteAddedEvent(
        event_id=event_id,
        user_id=user_id,
        folder_id=folder_id,
        intelligence_id=intelligence_id,
        occurred_at=datetime.now(),
    )

    body = fae.model_dump_json().encode("utf-8")

    try:
        if channel is None:
            logger.error("RabbitMQ not initialized, skip publish")
            return event_id

        exchange = await channel.get_exchange(settings.favorite_event_exchange)

        await exchange.publish(
            Message(
                body=body,
                content_type="application/json",
                delivery_mode=DeliveryMode.PERSISTENT,
            ),
            routing_key=settings.favorite_event_routing_key,
        )
    except Exception as e:
        logger.error(
            "Failed to publish FavoriteAddedEvent (event_id=%s): %s",
            event_id,
            e,
            exc_info=True,
        )

    return event_id
