import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.favorite.common.constants import FOLDER_NAME_MAX_LEN
from apps.favorite.exceptions import (
    FavoriteFolderNameInvalidException,
    FavoriteFolderNameDuplicateException,
    FavoriteFolderNotFoundException,
)
from apps.favorite.repositories.folder import (
    favorite_create_folder,
    favorite_folder_list_by_user,
    favorite_folder_find_by_id_and_user,
    favorite_folder_count_items,
)
from apps.favorite.schemas.folder import FavoriteFolderListQueryParams


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

    async def list_favorite_folders(
        self, params: FavoriteFolderListQueryParams
    ) -> dict:
        items, total = await favorite_folder_list_by_user(
            session=self.session,
            user_id=params.user_id,
            page=params.page,
            page_size=params.page_size,
            keyword=params.keyword,
        )

        return {
            "items": items,
            "total": total,
            "page": params.page,
            "page_size": params.page_size,
        }

    async def get_favorite_folder_detail(
        self, user_id: uuid.UUID, folder_id: uuid.UUID
    ) -> dict:

        folder = await favorite_folder_find_by_id_and_user(
            self.session, folder_id, user_id
        )

        if folder is None:
            raise FavoriteFolderNotFoundException()

        count = await favorite_folder_count_items(self.session, folder_id)

        return {
            "id": folder.id,
            "name": folder.name,
            "item_count": count,
            "created_at": folder.created_at,
            "updated_at": folder.updated_at,
        }
