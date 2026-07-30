import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from apps.favorite.models import GriverFavoriteItem, Intelligence


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
) -> GriverFavoriteItem | None:
    smt = select(GriverFavoriteItem).where(
        GriverFavoriteItem.id == item_id,
        GriverFavoriteItem.user_id == user_id,
        GriverFavoriteItem.is_deleted.is_(False),
    )
    result = await session.execute(smt)
    return result.scalar_one_or_none()


async def favorite_item_find_in_folder(
    session: AsyncSession, folder_id: uuid.UUID, target_type: str, target_id: uuid.UUID
) -> GriverFavoriteItem | None:
    # TODO 注意实现这个查询的索引
    smt = select(GriverFavoriteItem).where(
        GriverFavoriteItem.folder_id == folder_id,
        GriverFavoriteItem.target_id == target_id,
        GriverFavoriteItem.target_type == target_type,
        GriverFavoriteItem.is_deleted.is_(False),
    )

    result = await session.execute(smt)
    return result.scalar_one_or_none()


async def favorite_item_soft_delete(
    session: AsyncSession, item: GriverFavoriteItem
) -> GriverFavoriteItem:
    item.is_deleted = True
    await session.flush()

    return item


async def favorite_item_list_by_folder(
    session: AsyncSession,
    folder_id: uuid.UUID,
    page: int = 1,
    page_size: int = 10,
    keyword: str = "",
) -> tuple[list[tuple[GriverFavoriteItem, Intelligence]], int]:
    clean_page = max(1, page)
    clean_page_size = min(max(1, page_size), 100)
    offset = (clean_page - 1) * clean_page_size

    collect = [
        GriverFavoriteItem.folder_id == folder_id,
        GriverFavoriteItem.is_deleted.is_(False),
    ]

    clean_str = keyword.strip().replace("%", r"\%").replace("_", r"\_")
    if clean_str:
        collect.append(Intelligence.title.ilike(f"%{clean_str}%"))

    base_stmt = (
        select(GriverFavoriteItem, Intelligence)
        .join(
            Intelligence,
            (Intelligence.id == GriverFavoriteItem.target_id)
            & (GriverFavoriteItem.target_type == "intelligence"),
        )
        .where(*collect)
    )

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    # 注意索引没有desc，可以考虑后期加索引
    query_stmt = (
        base_stmt.order_by(GriverFavoriteItem.created_at.desc())
        .offset(offset)
        .limit(clean_page_size)
    )

    result = await session.execute(query_stmt)
    rows = list(result.tuples().all())

    return rows, total
