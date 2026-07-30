import datetime
import uuid
from datetime import timezone

from sqlalchemy import func, update
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.favorite.models import GriverFavoriteFolder, GriverFavoriteItem


# 创建新文件夹
async def favorite_create_folder(
    session: AsyncSession, user_id: uuid.UUID, folder_name: str
) -> GriverFavoriteFolder:
    folder = GriverFavoriteFolder(user_id=user_id, name=folder_name)
    session.add(folder)
    await session.flush()
    return folder


async def favorite_folder_find_by_id_and_user(
    session: AsyncSession, folder_id: uuid.UUID, user_id: uuid.UUID
) -> GriverFavoriteFolder | None:
    result = await session.execute(
        select(GriverFavoriteFolder).where(
            GriverFavoriteFolder.id == folder_id,
            GriverFavoriteFolder.user_id == user_id,
            GriverFavoriteFolder.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()


async def favorite_folder_count_by_name(
    session: AsyncSession, user_id: uuid.UUID, name: str
) -> int:
    result = await session.execute(
        select(GriverFavoriteFolder).where(
            GriverFavoriteFolder.user_id == user_id,
            GriverFavoriteFolder.name == name,
            GriverFavoriteFolder.is_deleted.is_(False),
        )
    )
    if result.scalar_one_or_none() is None:
        return 0
    else:
        return 1


async def favorite_folder_list_by_user(
    session: AsyncSession, user_id: uuid.UUID, page: int, page_size: int, keyword: str
) -> tuple[list[GriverFavoriteFolder], int] | None:
    new_key_word = keyword.strip()

    if len(new_key_word) > 0:
        escaped_str = new_key_word.translate(
            str.maketrans({"%": r"\%", "_": r"\_", "\\": r"\\"})
        )
        search_str = f"%{escaped_str}%"

        res = await session.execute(
            select(GriverFavoriteFolder)
            .where(
                GriverFavoriteFolder.user_id == user_id,
                GriverFavoriteFolder.name.ilike(search_str, escape="\\"),
                GriverFavoriteFolder.is_deleted.is_(False),
            )
            .order_by(GriverFavoriteFolder.updated_at.desc())
            .offset(offset=(max(1, page) - 1) * page_size)
            .limit(page_size)
        )
        total = await session.scalar(
            select(func.count()).where(
                GriverFavoriteFolder.user_id == user_id,
                GriverFavoriteFolder.name.ilike(search_str, escape="\\"),
                GriverFavoriteFolder.is_deleted.is_(False),
            )
        )

        items: list[GriverFavoriteFolder] = list(res.scalars().all())
        return items, total

    else:
        res = await session.execute(
            select(GriverFavoriteFolder)
            .where(
                GriverFavoriteFolder.user_id == user_id,
                GriverFavoriteFolder.is_deleted.is_(False),
            )
            .order_by(GriverFavoriteFolder.updated_at.desc())
            .offset(offset=(max(1, page) - 1) * page_size)
            .limit(page_size)
        )
        total = await session.scalar(
            select(func.count()).where(
                GriverFavoriteFolder.user_id == user_id,
                GriverFavoriteFolder.is_deleted.is_(False),
            )
        )

        items: list[GriverFavoriteFolder] = list(res.scalars().all())
        return items, total


async def favorite_folder_count_items(session, folder_id: uuid.UUID) -> int:
    # SELECT count(*) FROM griver_favorite_item
    # WHERE folder_id = ? AND is_deleted = false
    smt = (
        select(func.count())
        .select_from(GriverFavoriteItem)
        .where(
            GriverFavoriteItem.folder_id == folder_id,
            GriverFavoriteItem.is_deleted.is_(False),
        )
    )

    result = await session.execute(smt)
    return result.scalar() or 0


async def favorite_folder_update_name(
    session, folder: GriverFavoriteFolder, new_name: str
) -> GriverFavoriteFolder:
    folder.name = new_name

    folder.updated_at = datetime.datetime.now(timezone.utc)
    await session.flush()
    return folder


async def favorite_folder_soft_delete(
    session: AsyncSession, folder: GriverFavoriteFolder
) -> GriverFavoriteFolder:
    folder.is_deleted = True
    folder.updated_at = datetime.datetime.now(timezone.utc)

    await session.flush()
    return folder


async def favorite_item_soft_delete_by_folder_id(
    session: AsyncSession, folder_id: uuid.UUID
) -> list[GriverFavoriteItem]:
    smt = (
        update(GriverFavoriteItem)
        .where(
            GriverFavoriteItem.folder_id == folder_id,
            GriverFavoriteItem.is_deleted.is_(False),
        )
        .values(is_deleted=True)
        .returning(GriverFavoriteItem)
    )

    items = await session.execute(smt)
    return list(items.scalars().all())
