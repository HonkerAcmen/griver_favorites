import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.favorite.models import Intelligence


async def intelligence_find_by_id_not_deleted(
    session: AsyncSession, intelligence_id: uuid.UUID
) -> Intelligence | None:
    res = await session.execute(
        select(Intelligence).where(
            Intelligence.id == intelligence_id, Intelligence.is_deleted.is_(False)
        )
    )

    return res.scalar_one_or_none()
