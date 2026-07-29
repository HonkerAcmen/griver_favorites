import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.favorite.common.constants import FOLDER_NAME_MAX_LEN
from apps.favorite.exceptions import (
    FavoriteFolderNameInvalidException,
    FavoriteFolderNameDuplicateException,
)
from apps.favorite.repositories.folder import favorite_create_folder


class FolderService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_folder(self, user_id: uuid.UUID, name: str) -> dict:
        cleaned = name.strip()
        if not cleaned or len(cleaned) > FOLDER_NAME_MAX_LEN:
            raise FavoriteFolderNameInvalidException()

        try:
            folder = await favorite_create_folder(
                self.session, user_id, folder_name=name
            )
            await self.session.flush()
            await self.session.commit()

            return {
                "name": folder.name,
                "user_id": folder.user_id,
                "created_at": folder.created_at,
                "updated_at": folder.updated_at,
            }
        except IntegrityError as e:
            await self.session.rollback()
            raise FavoriteFolderNameDuplicateException() from e
