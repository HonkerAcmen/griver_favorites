"""folder_cache Cache-Aside 单测：mock Redis + patch DB 加载，覆盖 requirements 7.2 六条。"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from apps.favorite.common.cache_keys import folder_detail_key_gen
from apps.favorite.common.constants import (
    FOLDER_DETAIL_CACHE_TTL_SECONDS,
    FOLDER_DETAIL_NULL_CACHE_TTL_SECONDS,
)
from apps.favorite.exceptions import FavoriteFolderNotFoundException
from apps.favorite.schemas.cache import FolderDetailCacheDTO
from apps.favorite.services.cache.folder_cache import (
    get_folder_detail_cached,
    invalidate_folder_detail,
    invalidate_folder_detail_many,
)

USER_ID = uuid.UUID("fa500001-0001-4000-8000-000000000001")
FOLDER_ID = uuid.UUID("fa500002-0001-4000-8000-000000000002")
TARGET_FOLDER_ID = uuid.UUID("fa500002-0002-4000-8000-000000000002")

LOAD_DETAIL_PATH = "apps.favorite.services.cache.folder_cache._load_detail_from_db"


def _expected_key(folder_id: uuid.UUID = FOLDER_ID) -> str:
    return folder_detail_key_gen(user_id=USER_ID, folder_id=folder_id)


def _sample_detail_dict() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "id": FOLDER_ID,
        "name": "工作",
        "item_count": 3,
        "created_at": now,
        "updated_at": now,
    }


def _make_mock_redis(*, get_return=None, get_side_effect=None):
    redis_read = AsyncMock()
    redis_write = AsyncMock()
    if get_side_effect is not None:
        redis_read.get = AsyncMock(side_effect=get_side_effect)
    else:
        redis_read.get = AsyncMock(return_value=get_return)
    redis_write.setex = AsyncMock()
    redis_write.delete = AsyncMock()
    return redis_read, redis_write


@pytest.mark.asyncio
async def test_get_folder_detail_cache_hit_skips_db():
    """7.2 #1：命中缓存时不查 DB。"""
    detail = _sample_detail_dict()
    cached_json = FolderDetailCacheDTO.from_service_dict(detail).to_json()
    redis_read, redis_write = _make_mock_redis(get_return=cached_json)
    session = AsyncMock()

    with patch(LOAD_DETAIL_PATH, new_callable=AsyncMock) as mock_load:
        result = await get_folder_detail_cached(
            session=session,
            redis_read=redis_read,
            redis_write=redis_write,
            user_id=USER_ID,
            folder_id=FOLDER_ID,
        )

    redis_read.get.assert_awaited_once_with(_expected_key())
    mock_load.assert_not_awaited()
    redis_write.setex.assert_not_awaited()
    assert result["name"] == "工作"
    assert result["item_count"] == 3


@pytest.mark.asyncio
async def test_get_folder_detail_cache_miss_loads_db_and_setex():
    """7.2 #2：未命中时查 DB 并 setex 300s。"""
    detail = _sample_detail_dict()
    redis_read, redis_write = _make_mock_redis(get_return=None)
    session = AsyncMock()

    with patch(
        LOAD_DETAIL_PATH, new_callable=AsyncMock, return_value=detail
    ) as mock_load:
        result = await get_folder_detail_cached(
            session=session,
            redis_read=redis_read,
            redis_write=redis_write,
            user_id=USER_ID,
            folder_id=FOLDER_ID,
        )

    mock_load.assert_awaited_once_with(session, folder_id=FOLDER_ID, user_id=USER_ID)
    redis_write.setex.assert_awaited_once()
    setex_args = redis_write.setex.await_args.args
    assert setex_args[0] == _expected_key()
    assert setex_args[1] == FOLDER_DETAIL_CACHE_TTL_SECONDS
    cached_dto = FolderDetailCacheDTO.from_json(setex_args[2])
    assert cached_dto is not None
    assert cached_dto.item_count == 3
    assert result == detail


@pytest.mark.asyncio
async def test_get_folder_detail_not_found_writes_null_sentinel_60s():
    """7.2 #3a：DB NotFound 时写空值 sentinel，TTL 60s。"""
    redis_read, redis_write = _make_mock_redis(get_return=None)
    session = AsyncMock()

    with patch(
        LOAD_DETAIL_PATH,
        new_callable=AsyncMock,
        side_effect=FavoriteFolderNotFoundException(),
    ):
        with pytest.raises(FavoriteFolderNotFoundException):
            await get_folder_detail_cached(
                session=session,
                redis_read=redis_read,
                redis_write=redis_write,
                user_id=USER_ID,
                folder_id=FOLDER_ID,
            )

    redis_write.setex.assert_awaited_once()
    setex_args = redis_write.setex.await_args.args
    assert setex_args[0] == _expected_key()
    assert setex_args[1] == FOLDER_DETAIL_NULL_CACHE_TTL_SECONDS
    assert setex_args[2] == FolderDetailCacheDTO.null_sentinel_json()


@pytest.mark.asyncio
async def test_get_folder_detail_null_sentinel_hit_raises_without_db():
    """7.2 #3b：命中空值 sentinel 时抛 NotFound，且不查 DB。"""
    sentinel = FolderDetailCacheDTO.null_sentinel_json()
    redis_read, redis_write = _make_mock_redis(get_return=sentinel)
    session = AsyncMock()

    with patch(LOAD_DETAIL_PATH, new_callable=AsyncMock) as mock_load:
        with pytest.raises(FavoriteFolderNotFoundException):
            await get_folder_detail_cached(
                session=session,
                redis_read=redis_read,
                redis_write=redis_write,
                user_id=USER_ID,
                folder_id=FOLDER_ID,
            )

    mock_load.assert_not_awaited()
    redis_write.setex.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalidate_folder_detail_deletes_key_after_rename():
    """7.2 #4：rename commit 后应 delete 单 key。"""
    redis_write = AsyncMock()

    await invalidate_folder_detail(redis_write, user_id=USER_ID, folder_id=FOLDER_ID)

    redis_write.delete.assert_awaited_once_with(_expected_key())


@pytest.mark.asyncio
async def test_invalidate_folder_detail_many_deletes_source_and_target_after_move():
    """7.2 #5：move commit 后应 delete 来源 + 目标双 key。"""
    redis_write = AsyncMock()
    source_key = _expected_key(FOLDER_ID)
    target_key = _expected_key(TARGET_FOLDER_ID)

    await invalidate_folder_detail_many(
        redis_write,
        user_id=USER_ID,
        folder_ids=[FOLDER_ID, TARGET_FOLDER_ID],
    )

    redis_write.delete.assert_awaited_once_with(source_key, target_key)


@pytest.mark.asyncio
async def test_invalidate_folder_detail_many_empty_folder_ids_no_op():
    redis_write = AsyncMock()

    await invalidate_folder_detail_many(redis_write, user_id=USER_ID, folder_ids=[])

    redis_write.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_folder_detail_redis_read_error_falls_back_to_db():
    """7.2 #6：redis_read 异常时降级查 DB。"""
    detail = _sample_detail_dict()
    redis_read, redis_write = _make_mock_redis(
        get_side_effect=Exception("connection refused")
    )
    session = AsyncMock()

    with patch(
        LOAD_DETAIL_PATH, new_callable=AsyncMock, return_value=detail
    ) as mock_load:
        result = await get_folder_detail_cached(
            session=session,
            redis_read=redis_read,
            redis_write=redis_write,
            user_id=USER_ID,
            folder_id=FOLDER_ID,
        )

    mock_load.assert_awaited_once()
    assert result == detail
