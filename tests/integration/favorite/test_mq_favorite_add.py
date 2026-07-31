"""RabbitMQ 收藏事件集成测试：真实 Broker + DB；无 RabbitMQ 时 skip。"""

import asyncio
import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
from aio_pika import DeliveryMode, Message
from sqlalchemy import func, select

from apps.core.config import settings
from apps.core.database import SessionLocal
from apps.favorite.exceptions import FavoriteItemAlreadyExistsException
from apps.favorite.models import FavoriteOperationLog
from apps.favorite.mq.consumer import handle_message
from apps.favorite.repositories.operation_log import operation_log_exists_by_event_id
from apps.favorite.schemas.event import FavoriteAddedEvent
from apps.favorite.services.folder import FolderService
from apps.favorite.services.item import ItemService

SEED_ALICE_ID = uuid.UUID("fa500001-0001-4000-8000-000000000001")
SEED_INTELLIGENCE_ID = uuid.UUID("fa700001-0001-4000-8000-000000000001")

PROCESS_PATH = "apps.favorite.mq.consumer.process_favorite_added_message"


async def _create_folder(user_id: uuid.UUID, name: str) -> uuid.UUID:
    async with SessionLocal() as session:
        result = await FolderService(session).create_folder(user_id=user_id, name=name)
        return uuid.UUID(str(result["id"]))


async def _publish_event_bytes(
    channel, body: bytes, *, headers: dict | None = None
) -> None:
    exchange = await channel.get_exchange(settings.favorite_event_exchange)
    await exchange.publish(
        Message(
            body=body,
            headers=headers or {},
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        ),
        routing_key=settings.favorite_event_routing_key,
    )


def _event_body_bytes(
    *,
    event_id: uuid.UUID | None = None,
    folder_id: uuid.UUID | None = None,
) -> bytes:
    event = FavoriteAddedEvent(
        event_id=event_id or uuid.uuid4(),
        user_id=SEED_ALICE_ID,
        folder_id=folder_id or uuid.uuid4(),
        intelligence_id=SEED_INTELLIGENCE_ID,
        occurred_at=datetime.now(),
    )
    return event.model_dump_json().encode("utf-8")


async def _count_logs_by_event_id(event_id: uuid.UUID) -> int:
    async with SessionLocal() as session:
        result = await session.execute(
            select(func.count())
            .select_from(FavoriteOperationLog)
            .where(FavoriteOperationLog.event_id == event_id)
        )
        return int(result.scalar_one())


async def _drain_queue(queue) -> None:
    while True:
        message = await queue.get(timeout=1, fail=False)
        if message is None:
            break
        await message.ack()


@pytest.mark.asyncio
async def test_add_success_publishes_message(mq_setup):
    """§7.3 #1：收藏 commit 成功后队列收到消息。"""
    channel, queue, _dlq = mq_setup
    folder_id = await _create_folder(SEED_ALICE_ID, f"mq-int-{uuid.uuid4()}")

    async with SessionLocal() as session:
        service = ItemService(session, mq_channel=channel)
        await service.add_item_to_folder(
            user_id=SEED_ALICE_ID,
            folder_id=folder_id,
            intelligence_id=SEED_INTELLIGENCE_ID,
        )

    await asyncio.sleep(0.2)
    incoming = await queue.get(timeout=5, fail=False)
    assert incoming is not None
    payload = FavoriteAddedEvent.model_validate_json(incoming.body)
    assert payload.user_id == SEED_ALICE_ID
    assert payload.folder_id == folder_id
    assert payload.intelligence_id == SEED_INTELLIGENCE_ID
    await incoming.ack()


@pytest.mark.asyncio
async def test_add_failure_does_not_publish(mq_setup):
    """§7.3 #2：DB 重复收藏失败时不发新消息。"""
    channel, queue, _dlq = mq_setup
    folder_id = await _create_folder(SEED_ALICE_ID, f"mq-dup-{uuid.uuid4()}")

    async with SessionLocal() as session:
        service = ItemService(session, mq_channel=channel)
        await service.add_item_to_folder(
            user_id=SEED_ALICE_ID,
            folder_id=folder_id,
            intelligence_id=SEED_INTELLIGENCE_ID,
        )

    await _drain_queue(queue)

    async with SessionLocal() as session:
        service = ItemService(session, mq_channel=channel)
        with pytest.raises(FavoriteItemAlreadyExistsException):
            await service.add_item_to_folder(
                user_id=SEED_ALICE_ID,
                folder_id=folder_id,
                intelligence_id=SEED_INTELLIGENCE_ID,
            )

    incoming = await queue.get(timeout=1, fail=False)
    assert incoming is None


@pytest.mark.asyncio
async def test_consumer_persists_operation_log(mq_setup):
    """§7.3 #3：消费成功后 operation_log 有记录。"""
    channel, queue, _dlq = mq_setup
    event_id = uuid.uuid4()
    await _publish_event_bytes(channel, _event_body_bytes(event_id=event_id))

    incoming = await queue.get(timeout=5, fail=False)
    assert incoming is not None
    await handle_message(incoming, channel)

    async with SessionLocal() as session:
        assert await operation_log_exists_by_event_id(session, event_id)


@pytest.mark.asyncio
async def test_duplicate_event_id_not_duplicated_in_log(mq_setup):
    """§7.3 #4：重复 event_id 消费后仍只有一条 operation_log。"""
    channel, queue, _dlq = mq_setup
    event_id = uuid.uuid4()
    body = _event_body_bytes(event_id=event_id)

    await _publish_event_bytes(channel, body)
    first = await queue.get(timeout=5, fail=False)
    assert first is not None
    await handle_message(first, channel)

    await _publish_event_bytes(channel, body)
    second = await queue.get(timeout=5, fail=False)
    assert second is not None
    await handle_message(second, channel)

    assert await _count_logs_by_event_id(event_id) == 1


@pytest.mark.asyncio
@patch(PROCESS_PATH, side_effect=RuntimeError("simulated consume failure"))
async def test_consume_failures_end_up_in_dlq(mock_process, mq_setup):
    """§7.3 #5：连续消费失败后消息进入 DLQ。"""
    channel, queue, dlq = mq_setup
    await _publish_event_bytes(channel, _event_body_bytes())

    for _ in range(3):
        incoming = await queue.get(timeout=5, fail=False)
        assert incoming is not None
        await handle_message(incoming, channel)

    dlq_message = await dlq.get(timeout=5, fail=False)
    assert dlq_message is not None
    await dlq_message.ack()
    mock_process.assert_called()
