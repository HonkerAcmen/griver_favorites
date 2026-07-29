import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.favorite.models import GriverFavoriteFolder


# 创建新文件夹
async def favorite_create_folder(
    session: AsyncSession, user_id: uuid.UUID, folder_name: str
) -> GriverFavoriteFolder:
    folder = GriverFavoriteFolder(user_id=user_id, name=folder_name)
    session.add(folder)
    await session.flush()
    return folder


async def favorite_folder_find_by_id_and_user(
    session: AsyncSession, user_id: uuid.UUID, folder_id: str
) -> GriverFavoriteFolder | None:
    result = await session.execute(
        select(GriverFavoriteFolder).where(
            GriverFavoriteFolder.id == folder_id,
            GriverFavoriteFolder.user_id == user_id,
            GriverFavoriteFolder.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()
