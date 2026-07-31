from uuid import UUID

from logger import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from apps.favorite.common.cache_keys import folder_detail_key_gen
from apps.favorite.common.constants import (
    FOLDER_DETAIL_NULL_CACHE_TTL_SECONDS,
    FOLDER_DETAIL_CACHE_TTL_SECONDS,
)
from apps.favorite.exceptions import FavoriteFolderNotFoundException
from apps.favorite.repositories.folder import (
    favorite_folder_find_by_id_and_user,
    favorite_folder_count_items,
)
from apps.favorite.schemas.cache import FolderDetailCacheDTO


async def _load_detail_from_db(session: AsyncSession, folder_id: UUID, user_id: UUID):
    folder_instance = await favorite_folder_find_by_id_and_user(
        session, folder_id=folder_id, user_id=user_id
    )

    if folder_instance is None:
        raise FavoriteFolderNotFoundException()

    item_count = await favorite_folder_count_items(session, folder_id)

    return {
        "id": folder_instance.id,
        "name": folder_instance.name,
        "item_count": item_count,
        "created_at": folder_instance.created_at,
        "updated_at": folder_instance.updated_at,
    }


async def get_folder_detail_cached(
    session: AsyncSession,
    redis_read: Redis,
    redis_write: Redis,
    user_id: UUID,
    folder_id: UUID,
) -> dict:

    # 生成key
    key = folder_detail_key_gen(user_id=user_id, folder_id=folder_id)

    raw: str | None = None

    try:
        raw = await redis_read.get(key)
    except Exception as e:
        logger.warning("[Redis Read Error]: Failed to get key %s: %s", key, e)

    if raw is not None:
        dto = FolderDetailCacheDTO.from_json(raw)
        if dto is None:
            raise FavoriteFolderNotFoundException()

        return dto.model_dump(mode="json")

    # 缓存未命中或 Redis 读降级，从数据库加载
    try:
        data = await _load_detail_from_db(session, folder_id=folder_id, user_id=user_id)
    except FavoriteFolderNotFoundException as e:
        try:
            await redis_write.setex(
                key,
                FOLDER_DETAIL_NULL_CACHE_TTL_SECONDS,
                FolderDetailCacheDTO.null_sentinel_json(),
            )
        except Exception as e:
            logger.error(
                "[Redis Write Error]: Failed to write sentinel for %s: %s", key, e
            )

        raise

    # 将数据库查询结果组装为 DTO
    dto = FolderDetailCacheDTO.from_service_dict(data)

    try:
        await redis_write.setex(key, FOLDER_DETAIL_CACHE_TTL_SECONDS, dto.to_json())
    except Exception as e:
        logger.error("[Redis Write Error]: Failed to write setex for %s: %s", key, e)

    return data


async def invalidate_folder_detail(
    redis_write: Redis, user_id: UUID, folder_id: UUID
) -> None:
    key = folder_detail_key_gen(user_id=user_id, folder_id=folder_id)
    try:
        await redis_write.delete(key)
    except Exception as e:
        logger.error("[Redis Delete Error]: Failed to delete key %s: %s", key, e)


async def invalidate_folder_detail_many(
    redis_write: Redis, user_id: UUID, folder_ids: list[UUID]
) -> None:
    if not folder_ids:
        return

    keys: list[str] = [
        folder_detail_key_gen(user_id=user_id, folder_id=folder_id)
        for folder_id in folder_ids
    ]
    try:
        await redis_write.delete(*keys)
    except Exception as e:
        logger.error("[Redis Delete Error]: Failed to delete keys %s: %s", keys, e)
