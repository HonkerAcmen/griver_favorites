import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.favorite.models import GriverFavoriteItem


async def favorite_item_create(
    session: AsyncSession,
    folder_id: uuid.UUID,
    user_id: uuid.UUID,
    target_type: str,
    target_id: uuid.UUID,
) -> GriverFavoriteItem:
    item = GriverFavoriteItem(
        folder_id=folder_id,
        user_id=user_id,
        target_type=target_type,
        target_id=target_id,
    )
    session.add(item)

    await session.flush()
    return item


async def favorite_item_find_by_id_and_user(
    session: AsyncSession, item_id: uuid.UUID, user_id: uuid.UUID
)->GriverFavoriteItem:
    smt = select(GriverFavoriteItem).where(
        GriverFavoriteItem.id == item_id, GriverFavoriteItem.user_id == user_id
    )
    result = await session.execute(smt)
    return result.scalar_one_or_none()


async def favorite_item_find_in_folder(
    session: AsyncSession, folder_id: uuid.UUID, target_type: str, target_id: uuid.UUID
):
    pass


async def favorite_item_soft_delete(session: AsyncSession, item):
    pass


async def favorite_item_list_by_folder(
    session: AsyncSession, folder_id: uuid.UUID, page, page_size, keyword
):
    pass
