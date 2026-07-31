"""MQ Publisher 单测：mock channel，不连真 RabbitMQ。"""

import json
import uuid
from unittest.mock import AsyncMock

import pytest
from aio_pika import DeliveryMode

from apps.core.config import settings
from apps.favorite.mq.publisher import publish_favorite_added
from apps.favorite.schemas.event import FavoriteAddedEvent

USER_ID = uuid.UUID("fa500001-0001-4000-8000-000000000001")
FOLDER_ID = uuid.UUID("fa500002-0001-4000-8000-000000000002")
INTELLIGENCE_ID = uuid.UUID("fa700001-0001-4000-8000-000000000001")


def _make_mock_channel(*, publish_side_effect=None):
    exchange = AsyncMock()
    if publish_side_effect is not None:
        exchange.publish = AsyncMock(side_effect=publish_side_effect)
    else:
        exchange.publish = AsyncMock()

    channel = AsyncMock()
    channel.get_exchange = AsyncMock(return_value=exchange)
    return channel, exchange


@pytest.mark.asyncio
async def test_publish_favorite_added_success():
    channel, exchange = _make_mock_channel()

    event_id = await publish_favorite_added(
        channel,
        user_id=USER_ID,
        folder_id=FOLDER_ID,
        intelligence_id=INTELLIGENCE_ID,
    )

    assert isinstance(event_id, uuid.UUID)
    channel.get_exchange.assert_awaited_once_with(settings.favorite_event_exchange)
    exchange.publish.assert_awaited_once()

    publish_kwargs = exchange.publish.await_args.kwargs
    assert publish_kwargs["routing_key"] == settings.favorite_event_routing_key

    message = exchange.publish.await_args.args[0]
    payload = json.loads(message.body.decode("utf-8"))
    parsed = FavoriteAddedEvent.model_validate(payload)

    assert parsed.event_id == event_id
    assert parsed.user_id == USER_ID
    assert parsed.folder_id == FOLDER_ID
    assert parsed.intelligence_id == INTELLIGENCE_ID
    assert parsed.action == "favorite_add"
    assert parsed.occurred_at is not None
    assert message.content_type == "application/json"
    assert message.delivery_mode == DeliveryMode.PERSISTENT


@pytest.mark.asyncio
async def test_publish_when_channel_none_returns_event_id():
    event_id = await publish_favorite_added(
        None,
        user_id=USER_ID,
        folder_id=FOLDER_ID,
        intelligence_id=INTELLIGENCE_ID,
    )

    assert isinstance(event_id, uuid.UUID)


@pytest.mark.asyncio
async def test_publish_broker_error_does_not_raise():
    channel, exchange = _make_mock_channel(
        publish_side_effect=Exception("connection refused")
    )

    event_id = await publish_favorite_added(
        channel,
        user_id=USER_ID,
        folder_id=FOLDER_ID,
        intelligence_id=INTELLIGENCE_ID,
    )

    assert isinstance(event_id, uuid.UUID)
    exchange.publish.assert_awaited_once()
