"""ItemService 单测"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.favorite.exceptions import (
    FavoriteFolderNotFoundException,
    FavoriteItemAlreadyExistsException,
    FavoriteItemMoveFailedException,
    FavoriteItemNotFoundException,
    IntelligenceNotFoundException,
)
from apps.favorite.models import GriverFavoriteItem
from apps.favorite.repositories.intelligence import intelligence_find_by_id_not_deleted
from apps.favorite.schemas.item import FavoriteItemListQueryParams
from apps.favorite.services.folder import FolderService
from apps.favorite.services.item import ItemService

SEED_ALICE_ID = uuid.UUID("fa500001-0001-4000-8000-000000000001")
SEED_BOB_ID = uuid.UUID("fa500001-0002-4000-8000-000000000002")
SEED_INTELLIGENCE_ID = uuid.UUID("fa700001-0001-4000-8000-000000000001")
SEED_INTELLIGENCE_DELETED_ID = uuid.UUID("fa700001-0001-4000-8000-000000000099")


async def _create_folder(
    session: AsyncSession, user_id: uuid.UUID, name: str | None = None
) -> uuid.UUID:
    folder_name = name or str(uuid.uuid4())
    result = await FolderService(session=session).create_folder(
        user_id=user_id, name=folder_name
    )
    return uuid.UUID(str(result["id"]))


async def _list_items(
    item_service: ItemService, folder_id: uuid.UUID, user_id: uuid.UUID
) -> dict:
    params = FavoriteItemListQueryParams(
        user_id=user_id, page=1, page_size=10, keyword=None
    )
    return await item_service.list_items_in_folder(folder_id=folder_id, params=params)


# --- #19 加入成功 ---


@pytest.mark.asyncio
async def test_add_item_success(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_id = await _create_folder(session, user_id, f"add-ok-{uuid.uuid4()}")
    service = ItemService(session=session)

    item = await service.add_item_to_folder(
        user_id=user_id,
        folder_id=folder_id,
        intelligence_id=SEED_INTELLIGENCE_ID,
    )

    assert item["target_id"] == SEED_INTELLIGENCE_ID
    assert item["target_type"] == "intelligence"
    assert item["is_deleted"] is False

    listed = await _list_items(service, folder_id, user_id)
    assert listed["total"] == 1


PUBLISH_PATH = "apps.favorite.services.item.publish_favorite_added"


@pytest.mark.asyncio
@patch(PUBLISH_PATH, new_callable=AsyncMock)
async def test_add_item_success_publishes_event(mock_publish, session: AsyncSession):
    mock_publish.return_value = uuid.uuid4()
    user_id = SEED_ALICE_ID
    folder_id = await _create_folder(session, user_id, f"add-mq-{uuid.uuid4()}")
    mq_channel = AsyncMock()
    service = ItemService(session=session, mq_channel=mq_channel)

    await service.add_item_to_folder(
        user_id=user_id,
        folder_id=folder_id,
        intelligence_id=SEED_INTELLIGENCE_ID,
    )

    mock_publish.assert_awaited_once_with(
        mq_channel,
        user_id=user_id,
        folder_id=folder_id,
        intelligence_id=SEED_INTELLIGENCE_ID,
    )


@pytest.mark.asyncio
@patch(PUBLISH_PATH, new_callable=AsyncMock)
async def test_add_item_duplicate_does_not_publish(mock_publish, session: AsyncSession):
    mock_publish.return_value = uuid.uuid4()
    user_id = SEED_ALICE_ID
    folder_id = await _create_folder(session, user_id, f"add-mq-dup-{uuid.uuid4()}")
    service = ItemService(session=session, mq_channel=AsyncMock())

    await service.add_item_to_folder(
        user_id=user_id,
        folder_id=folder_id,
        intelligence_id=SEED_INTELLIGENCE_ID,
    )
    assert mock_publish.await_count == 1

    with pytest.raises(FavoriteItemAlreadyExistsException):
        await service.add_item_to_folder(
            user_id=user_id,
            folder_id=folder_id,
            intelligence_id=SEED_INTELLIGENCE_ID,
        )

    mock_publish.assert_awaited_once()


# --- #20 同 folder 重复加入 ---


@pytest.mark.asyncio
async def test_add_item_duplicate_in_same_folder(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_id = await _create_folder(session, user_id, f"add-dup-{uuid.uuid4()}")
    service = ItemService(session=session)

    await service.add_item_to_folder(
        user_id=user_id,
        folder_id=folder_id,
        intelligence_id=SEED_INTELLIGENCE_ID,
    )
    with pytest.raises(FavoriteItemAlreadyExistsException):
        await service.add_item_to_folder(
            user_id=user_id,
            folder_id=folder_id,
            intelligence_id=SEED_INTELLIGENCE_ID,
        )


# --- #21 不同 folder 加入同一情报 ---


@pytest.mark.asyncio
async def test_add_item_same_intelligence_in_different_folders(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_a = await _create_folder(session, user_id, f"add-cross-a-{uuid.uuid4()}")
    folder_b = await _create_folder(session, user_id, f"add-cross-b-{uuid.uuid4()}")
    service = ItemService(session=session)

    item_a = await service.add_item_to_folder(
        user_id=user_id,
        folder_id=folder_a,
        intelligence_id=SEED_INTELLIGENCE_ID,
    )
    item_b = await service.add_item_to_folder(
        user_id=user_id,
        folder_id=folder_b,
        intelligence_id=SEED_INTELLIGENCE_ID,
    )

    assert item_a["id"] != item_b["id"]
    assert item_a["target_id"] == item_b["target_id"] == SEED_INTELLIGENCE_ID


# --- #22 情报不存在/已删 ---


@pytest.mark.asyncio
async def test_add_item_intelligence_not_exists(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_id = await _create_folder(session, user_id, f"add-no-intel-{uuid.uuid4()}")
    service = ItemService(session=session)

    with pytest.raises(IntelligenceNotFoundException):
        await service.add_item_to_folder(
            user_id=user_id,
            folder_id=folder_id,
            intelligence_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_add_item_intelligence_soft_deleted(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_id = await _create_folder(session, user_id, f"add-del-intel-{uuid.uuid4()}")
    service = ItemService(session=session)

    deleted = await intelligence_find_by_id_not_deleted(
        session, SEED_INTELLIGENCE_DELETED_ID
    )
    assert deleted is None

    with pytest.raises(IntelligenceNotFoundException):
        await service.add_item_to_folder(
            user_id=user_id,
            folder_id=folder_id,
            intelligence_id=SEED_INTELLIGENCE_DELETED_ID,
        )


# --- #23 folder 已删后加入 ---


@pytest.mark.asyncio
async def test_add_item_folder_deleted(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_service = FolderService(session=session)
    item_service = ItemService(session=session)

    created = await folder_service.create_folder(
        user_id=user_id, name=f"add-del-folder-{uuid.uuid4()}"
    )
    folder_id = uuid.UUID(str(created["id"]))
    await folder_service.delete_favorite_folder(user_id, folder_id)

    with pytest.raises(FavoriteFolderNotFoundException):
        await item_service.add_item_to_folder(
            user_id=user_id,
            folder_id=folder_id,
            intelligence_id=SEED_INTELLIGENCE_ID,
        )


# --- #24 移除成功 ---


@pytest.mark.asyncio
async def test_remove_item_success(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_id = await _create_folder(session, user_id, f"remove-ok-{uuid.uuid4()}")
    item_service = ItemService(session=session)

    added = await item_service.add_item_to_folder(
        user_id=user_id,
        folder_id=folder_id,
        intelligence_id=SEED_INTELLIGENCE_ID,
    )
    removed = await item_service.remove_item_from_folder(
        user_id=user_id,
        folder_id=folder_id,
        item_id=added["id"],
    )

    assert removed["folder_id"] == folder_id
    assert removed["target_id"] == SEED_INTELLIGENCE_ID

    listed = await _list_items(item_service, folder_id, user_id)
    assert listed["total"] == 0

    # 情报仍在，可再次加入
    re_added = await item_service.add_item_to_folder(
        user_id=user_id,
        folder_id=folder_id,
        intelligence_id=SEED_INTELLIGENCE_ID,
    )
    assert re_added["target_id"] == SEED_INTELLIGENCE_ID


@pytest.mark.asyncio
async def test_remove_item_not_found(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_id = await _create_folder(session, user_id, f"remove-miss-{uuid.uuid4()}")
    item_service = ItemService(session=session)

    with pytest.raises(FavoriteItemNotFoundException):
        await item_service.remove_item_from_folder(
            user_id=user_id,
            folder_id=folder_id,
            item_id=uuid.uuid4(),
        )


# --- #25 移动成功 ---


@pytest.mark.asyncio
async def test_move_item_success(session: AsyncSession):
    user_id = SEED_ALICE_ID
    item_service = ItemService(session=session)
    source_id = await _create_folder(session, user_id, f"move-ok-src-{uuid.uuid4()}")
    target_id = await _create_folder(session, user_id, f"move-ok-dst-{uuid.uuid4()}")

    added = await item_service.add_item_to_folder(
        user_id=user_id,
        folder_id=source_id,
        intelligence_id=SEED_INTELLIGENCE_ID,
    )

    moved = await item_service.move_item(
        user_id=user_id,
        item_id=added["id"],
        target_folder_id=target_id,
    )

    assert moved["folder_id"] == target_id
    assert moved["target_id"] == SEED_INTELLIGENCE_ID
    assert moved["is_deleted"] is False

    src_list = await _list_items(item_service, source_id, user_id)
    dst_list = await _list_items(item_service, target_id, user_id)
    assert src_list["total"] == 0
    assert dst_list["total"] == 1

    source_row = await session.get(GriverFavoriteItem, added["id"])
    assert source_row is not None
    assert source_row.is_deleted is True


# --- #26 来源不含情报 / 原地移动 ---


@pytest.mark.asyncio
async def test_move_item_source_not_contains(session: AsyncSession):
    """item 已软删后不可移动。"""
    user_id = SEED_ALICE_ID
    item_service = ItemService(session=session)
    source_id = await _create_folder(session, user_id, f"move-no-src-{uuid.uuid4()}")
    target_id = await _create_folder(session, user_id, f"move-no-dst-{uuid.uuid4()}")

    added = await item_service.add_item_to_folder(
        user_id=user_id,
        folder_id=source_id,
        intelligence_id=SEED_INTELLIGENCE_ID,
    )
    await item_service.remove_item_from_folder(
        user_id=user_id, folder_id=source_id, item_id=added["id"]
    )

    with pytest.raises(FavoriteItemNotFoundException):
        await item_service.move_item(
            user_id=user_id,
            item_id=added["id"],
            target_folder_id=target_id,
        )


@pytest.mark.asyncio
async def test_move_item_to_same_folder(session: AsyncSession):
    user_id = SEED_ALICE_ID
    item_service = ItemService(session=session)
    folder_id = await _create_folder(session, user_id, f"move-same-{uuid.uuid4()}")

    added = await item_service.add_item_to_folder(
        user_id=user_id,
        folder_id=folder_id,
        intelligence_id=SEED_INTELLIGENCE_ID,
    )

    with pytest.raises(FavoriteItemMoveFailedException):
        await item_service.move_item(
            user_id=user_id,
            item_id=added["id"],
            target_folder_id=folder_id,
        )


# --- #27 目标已含情报 ---


@pytest.mark.asyncio
async def test_move_item_target_already_has_intelligence(session: AsyncSession):
    user_id = SEED_ALICE_ID
    item_service = ItemService(session=session)
    source_id = await _create_folder(session, user_id, f"move-dup-src-{uuid.uuid4()}")
    target_id = await _create_folder(session, user_id, f"move-dup-dst-{uuid.uuid4()}")

    added = await item_service.add_item_to_folder(
        user_id=user_id,
        folder_id=source_id,
        intelligence_id=SEED_INTELLIGENCE_ID,
    )
    await item_service.add_item_to_folder(
        user_id=user_id,
        folder_id=target_id,
        intelligence_id=SEED_INTELLIGENCE_ID,
    )

    src_before = await _list_items(item_service, source_id, user_id)
    dst_before = await _list_items(item_service, target_id, user_id)

    with pytest.raises(FavoriteItemAlreadyExistsException):
        await item_service.move_item(
            user_id=user_id,
            item_id=added["id"],
            target_folder_id=target_id,
        )

    src_after = await _list_items(item_service, source_id, user_id)
    dst_after = await _list_items(item_service, target_id, user_id)
    assert src_after["total"] == src_before["total"]
    assert dst_after["total"] == dst_before["total"]
