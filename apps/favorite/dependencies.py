from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.core.database import get_db_session
from apps.favorite.services.folder import FolderService
from apps.favorite.services.item import ItemService


async def get_folder_service(
    session: AsyncSession = Depends(get_db_session),
) -> FolderService:
    return FolderService(session)


async def get_item_service(
    session: AsyncSession = Depends(get_db_session),
) -> ItemService:
    return ItemService(session)