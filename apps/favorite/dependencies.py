from aio_pika.abc import AbstractChannel
from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from apps.core.database import get_db_session
from apps.core.rabbitmq import get_rabbitmq_channel
from apps.core.redis import get_redis_read, get_redis_write
from apps.favorite.services.folder import FolderService
from apps.favorite.services.item import ItemService


async def get_folder_service(
    session: AsyncSession = Depends(get_db_session),
    redis_read: Redis | None = Depends(get_redis_read),
    redis_write: Redis | None = Depends(get_redis_write),
) -> FolderService:
    return FolderService(session, redis_read=redis_read, redis_write=redis_write)


async def get_item_service(
    session: AsyncSession = Depends(get_db_session),
    redis_read: Redis | None = Depends(get_redis_read),
    redis_write: Redis | None = Depends(get_redis_write),
    mq_channel: AbstractChannel | None = Depends(get_rabbitmq_channel),
) -> ItemService:
    return ItemService(
        session,
        redis_read=redis_read,
        redis_write=redis_write,
        mq_channel=mq_channel,
    )
