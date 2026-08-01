import uuid

from aio_pika.abc import AbstractChannel
from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.favorite.common.integrity import raise_item_integrity_error
from apps.favorite.exceptions import (
    FavoriteFolderNotFoundException,
    FavoriteItemAlreadyExistsException,
    FavoriteItemMoveFailedException,
    FavoriteItemNotFoundException,
    IntelligenceNotFoundException,
    FavoriteUserNotFoundException,
)
from apps.favorite.mq.publisher import publish_favorite_added
from apps.favorite.repositories.folder import favorite_folder_find_by_id_and_user
from apps.favorite.repositories.intelligence import intelligence_find_by_id_not_deleted
from apps.favorite.repositories.user import user_find_active_by_id
from apps.favorite.repositories.item import (
    favorite_item_create,
    favorite_item_soft_delete,
    favorite_item_find_by_id_and_user,
    favorite_item_find_in_folder,
    favorite_item_list_by_folder,
)
from apps.favorite.schemas.item import FavoriteItemListQueryParams
from apps.favorite.services.cache.folder_cache import (
    invalidate_folder_detail,
    invalidate_folder_detail_many,
)


class ItemService:

    def __init__(
        self,
        session: AsyncSession,
        redis_read: Redis | None = None,
        redis_write: Redis | None = None,
        mq_channel: AbstractChannel | None = None,
    ):
        self.session = session
        self.redis_read = redis_read
        self.redis_write = redis_write
        self.mq_channel = mq_channel

    async def _ensure_user_exists(self, user_id: uuid.UUID) -> None:
        user = await user_find_active_by_id(self.session, user_id)
        if user is None:
            raise FavoriteUserNotFoundException()

    async def add_item_to_folder(
        self, user_id: uuid.UUID, folder_id: uuid.UUID, intelligence_id: uuid.UUID
    ) -> dict:
        await self._ensure_user_exists(user_id)

        folder = await favorite_folder_find_by_id_and_user(
            session=self.session, user_id=user_id, folder_id=folder_id
        )
        if folder is None:
            raise FavoriteFolderNotFoundException()

        if folder.is_deleted:
            raise FavoriteFolderNotFoundException()

        intel = await intelligence_find_by_id_not_deleted(self.session, intelligence_id)
        if intel is None:
            raise IntelligenceNotFoundException()

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
            raise_item_integrity_error(e)

        if self.redis_write is not None:
            await invalidate_folder_detail(
                self.redis_write, user_id=user_id, folder_id=folder_id
            )

        await publish_favorite_added(
            self.mq_channel,
            user_id=user_id,
            folder_id=folder_id,
            intelligence_id=intelligence_id,
        )

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

        if self.redis_write is not None:
            await invalidate_folder_detail(
                self.redis_write, user_id=user_id, folder_id=folder_id
            )

        return {
            "user_id": del_item.user_id,
            "folder_id": del_item.folder_id,
            "target_id": del_item.target_id,
            "target_type": del_item.target_type,
        }

    async def move_item(
        self, user_id: uuid.UUID, item_id: uuid.UUID, target_folder_id: uuid.UUID
    ) -> dict:
        # 检测当前item是否存在
        curr_item = await favorite_item_find_by_id_and_user(
            self.session, user_id=user_id, item_id=item_id
        )
        if curr_item is None:
            raise FavoriteItemNotFoundException()

        # 检测当前item 是否在 当前文件夹
        source_item = await favorite_item_find_in_folder(
            session=self.session,
            folder_id=curr_item.folder_id,
            target_type=curr_item.target_type,
            target_id=curr_item.target_id,
        )
        if source_item is None or source_item.id != item_id:
            raise FavoriteItemNotFoundException()

        # 检测目标文件夹是否存在
        target_folder = await favorite_folder_find_by_id_and_user(
            session=self.session, user_id=user_id, folder_id=target_folder_id
        )
        if target_folder is None or target_folder.is_deleted:
            raise FavoriteFolderNotFoundException()
        # 检测是否原地TP
        if target_folder_id == curr_item.folder_id:
            raise FavoriteItemMoveFailedException()

        # 检测目标文件夹中是否存在当前item
        target_folder_item = await favorite_item_find_in_folder(
            session=self.session,
            folder_id=target_folder_id,
            target_type=curr_item.target_type,
            target_id=curr_item.target_id,
        )
        if target_folder_item is not None:
            raise FavoriteItemAlreadyExistsException()

        source_folder_id = curr_item.folder_id
        try:
            # 先创建
            new_item = await favorite_item_create(
                session=self.session,
                folder_id=target_folder_id,
                user_id=user_id,
                target_type=curr_item.target_type,
                target_id=curr_item.target_id,
            )

            # 再软删
            await favorite_item_soft_delete(session=self.session, item=curr_item)
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise_item_integrity_error(e)

        if self.redis_write is not None:
            await invalidate_folder_detail_many(
                self.redis_write,
                user_id=user_id,
                folder_ids=[source_folder_id, target_folder_id],
            )

        return {
            "id": new_item.id,
            "user_id": new_item.user_id,
            "folder_id": new_item.folder_id,
            "target_id": new_item.target_id,
            "target_type": new_item.target_type,
            "is_deleted": new_item.is_deleted,
        }

    async def list_items_in_folder(
        self, folder_id: uuid.UUID, params: FavoriteItemListQueryParams
    ) -> dict:
        folder = await favorite_folder_find_by_id_and_user(
            session=self.session, user_id=params.user_id, folder_id=folder_id
        )
        if folder is None or folder.is_deleted:
            raise FavoriteFolderNotFoundException()

        rows, total = await favorite_item_list_by_folder(
            session=self.session,
            folder_id=folder_id,
            page=params.page,
            page_size=params.page_size,
            keyword=params.keyword or "",
        )

        items = [
            {
                "item_id": item.id,
                "intelligence_id": item.target_id,
                "title": intel.title,
                "created_at": item.created_at,
            }
            for item, intel in rows
        ]

        return {
            "items": items,
            "total": total,
            "page": params.page,
            "page_size": params.page_size,
        }
