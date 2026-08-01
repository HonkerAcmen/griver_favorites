import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.favorite.models import User


async def user_find_active_by_id(
    session: AsyncSession, user_id: uuid.UUID
) -> User | None:
    stmt = select(User).where(User.id == user_id, User.is_deleted.is_(False))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
