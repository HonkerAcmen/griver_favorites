from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.core.database import get_db_session
from apps.favorite.services.folder import FolderService


async def get_folder_service(
    session: AsyncSession = Depends(get_db_session),
) -> FolderService:
    return FolderService(session)
