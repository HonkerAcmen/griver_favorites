"""MQ Consumer 单测：mock channel / message，不连真 RabbitMQ。"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aio_pika import DeliveryMode
from sqlalchemy.ext.asyncio import AsyncSession

from apps.core.config import settings
from apps.favorite.common.constants import MQ_MAX_RETRIES
from apps.favorite.mq.consumer import (
    _get_retry_count,
    handle_message,
    process_favorite_added_message,
)
from apps.favorite.repositories.operation_log import operation_log_exists_by_event_id
from apps.favorite.schemas.event import FavoriteAddedEvent

USER_ID = uuid.UUID("fa500001-0001-4000-8000-000000000001")
FOLDER_ID = uuid.UUID("fa500002-0001-4000-8000-000000000002")
INTELLIGENCE_ID = uuid.UUID("fa700001-0001-4000-8000-000000000001")

PROCESS_PATH = "apps.favorite.mq.consumer.process_favorite_added_message"
SESSION_LOCAL_PATH = "apps.favorite.mq.consumer.SessionLocal"


def _event_body(
    event_id: uuid.UUID | None = None,
) -> bytes:
    event = FavoriteAddedEvent(
        event_id=event_id or uuid.uuid4(),
        user_id=USER_ID,
        folder_id=FOLDER_ID,
        intelligence_id=INTELLIGENCE_ID,
        occurred_at=datetime.now(),
    )
    return event.model_dump_json().encode("utf-8")


def _make_message(
    *,
    body: bytes | None = None,
    headers: dict | None = None,
) -> AsyncMock:
    message = AsyncMock()
    message.body = body if body is not None else _event_body()
    message.headers = headers or {}
    message.content_type = "application/json"
    message.delivery_mode = DeliveryMode.PERSISTENT
    message.ack = AsyncMock()
    message.reject = AsyncMock()
    return message


def _make_channel() -> tuple[AsyncMock, AsyncMock]:
    exchange = AsyncMock()
    exchange.publish = AsyncMock()
    channel = AsyncMock()
    channel.get_exchange = AsyncMock(return_value=exchange)
    return channel, exchange


def _session_context_mock() -> MagicMock:
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=AsyncMock())
    session_cm.__aexit__ = AsyncMock(return_value=False)
    return session_cm


@pytest.mark.asyncio
async def test_process_favorite_added_message_writes_operation_log(
    session: AsyncSession,
):
    event_id = uuid.uuid4()
    body = _event_body(event_id=event_id)

    await process_favorite_added_message(session, body)

    assert await operation_log_exists_by_event_id(session, event_id)


@pytest.mark.asyncio
async def test_process_duplicate_event_id_is_idempotent(session: AsyncSession):
    event_id = uuid.uuid4()
    body = _event_body(event_id=event_id)

    await process_favorite_added_message(session, body)
    await process_favorite_added_message(session, body)

    assert await operation_log_exists_by_event_id(session, event_id)


def test_get_retry_count_defaults_to_zero():
    message = _make_message(headers={})
    assert _get_retry_count(message) == 0


def test_get_retry_count_reads_header():
    message = _make_message(headers={"x-retry-count": 2})
    assert _get_retry_count(message) == 2


@pytest.mark.asyncio
@patch(PROCESS_PATH, new_callable=AsyncMock)
@patch(SESSION_LOCAL_PATH, return_value=_session_context_mock())
async def test_handle_message_success_acks(mock_session_local, mock_process):
    message = _make_message()
    channel, _ = _make_channel()

    await handle_message(message, channel)

    mock_process.assert_awaited_once()
    message.ack.assert_awaited_once()
    message.reject.assert_not_awaited()


@pytest.mark.asyncio
@patch(SESSION_LOCAL_PATH, return_value=_session_context_mock())
async def test_handle_message_validation_error_rejects(mock_session_local):
    message = _make_message(body=b"not-json")
    channel, exchange = _make_channel()

    await handle_message(message, channel)

    message.reject.assert_awaited_once_with(requeue=False)
    message.ack.assert_not_awaited()
    exchange.publish.assert_not_awaited()


@pytest.mark.asyncio
@patch(PROCESS_PATH, new_callable=AsyncMock, side_effect=RuntimeError("db down"))
@patch(SESSION_LOCAL_PATH, return_value=_session_context_mock())
async def test_handle_message_republishes_on_retry(mock_session_local, mock_process):
    message = _make_message(headers={"x-retry-count": 0})
    channel, exchange = _make_channel()

    await handle_message(message, channel)

    exchange.publish.assert_awaited_once()
    publish_kwargs = exchange.publish.await_args.kwargs
    assert publish_kwargs["routing_key"] == settings.favorite_event_routing_key
    republished = exchange.publish.await_args.args[0]
    assert republished.headers["x-retry-count"] == 1
    message.ack.assert_awaited_once()
    message.reject.assert_not_awaited()


@pytest.mark.asyncio
@patch(PROCESS_PATH, new_callable=AsyncMock, side_effect=RuntimeError("db down"))
@patch(SESSION_LOCAL_PATH, return_value=_session_context_mock())
async def test_handle_message_max_retries_rejects_to_dlq(
    mock_session_local, mock_process
):
    message = _make_message(headers={"x-retry-count": MQ_MAX_RETRIES - 1})
    channel, exchange = _make_channel()

    await handle_message(message, channel)

    message.reject.assert_awaited_once_with(requeue=False)
    message.ack.assert_not_awaited()
    exchange.publish.assert_not_awaited()
