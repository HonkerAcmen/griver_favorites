import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.favorite.models import FavoriteOperationLog


async def operation_log_create(
    session: AsyncSession,
    *,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    folder_id: uuid.UUID,
    intelligence_id: uuid.UUID,
    action: str,
) -> FavoriteOperationLog:
    row = FavoriteOperationLog(
        event_id=event_id,
        user_id=user_id,
        folder_id=folder_id,
        intelligence_id=intelligence_id,
        action=action,
    )
    session.add(row)
    await session.flush()
    return row


async def operation_log_exists_by_event_id(
    session: AsyncSession, event_id: uuid.UUID
) -> bool:
    result = await session.execute(
        select(FavoriteOperationLog.id).where(FavoriteOperationLog.event_id == event_id)
    )
    return result.scalar_one_or_none() is not None
