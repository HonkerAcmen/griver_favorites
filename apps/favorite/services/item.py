import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.favorite.exceptions import (
    FavoriteFolderNotFoundException,
    FavoriteItemAlreadyExistsException,
    FavoriteItemNotFoundException,
)
from apps.favorite.repositories.folder import favorite_folder_find_by_id_and_user
from apps.favorite.repositories.item import (
    favorite_item_create,
    favorite_item_soft_delete,
    favorite_item_find_by_id_and_user,
)


class ItemService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_item_to_folder(
        self, user_id: uuid.UUID, folder_id: uuid.UUID, intelligence_id: uuid.UUID
    ) -> dict:
        folder = await favorite_folder_find_by_id_and_user(
            session=self.session, user_id=user_id, folder_id=folder_id
        )
        if folder is None:
            raise FavoriteFolderNotFoundException()

        if folder.is_deleted:
            raise FavoriteFolderNotFoundException()

        # TODO 查询intell是否存在 如果不存在返回IntellNotFound

        try:
            item = await favorite_item_create(
                session=self.session,
                folder_id=folder_id,
                user_id=user_id,
                target_type="intelligence",
                target_id=intelligence_id,
            )
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise FavoriteItemAlreadyExistsException() from e

        return {
            "id": item.id,
            "user_id": item.user_id,
            "target_id": item.target_id,
            "target_type": item.target_type,
            "is_deleted": item.is_deleted,
        }

    async def remove_item_from_folder(self, user_id, folder_id, item_id) -> dict:

        item = await favorite_item_find_by_id_and_user(
            self.session, user_id=user_id, item_id=item_id
        )
        if item is None or item.folder_id != folder_id:
            raise FavoriteItemNotFoundException()

        del_item = await favorite_item_soft_delete(self.session, item)
        await self.session.commit()

        return {
            "user_id": del_item.user_id,
            "folder_id": del_item.folder_id,
            "target_id": del_item.target_id,
            "target_type": del_item.target_type,
        }
