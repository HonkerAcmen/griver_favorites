import datetime
import uuid
from datetime import timezone

from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.favorite.common.constants import FOLDER_NAME_MAX_LEN
from apps.favorite.exceptions import (
    FavoriteFolderNameInvalidException,
    FavoriteFolderNameDuplicateException,
    FavoriteFolderNotFoundException,
    FavoriteUserNotFoundException,
    FavoriteInternalDataConflict,
)
from apps.favorite.models import GriverFavoriteFolder, GriverFavoriteItem
from apps.favorite.repositories.folder import (
    favorite_create_folder,
    favorite_folder_list_by_user,
    favorite_folder_find_by_id_and_user,
    favorite_folder_update_name,
    favorite_item_soft_delete_by_folder_id,
    favorite_folder_soft_delete,
)
from apps.favorite.schemas.folder import FavoriteFolderListQueryParams
from apps.favorite.services.cache.folder_cache import (
    get_folder_detail_cached,
    invalidate_folder_detail,
    _load_detail_from_db,
)


class FolderService:
    def __init__(
        self,
        session: AsyncSession,
        redis_read: Redis | None = None,
        redis_write: Redis | None = None,
    ):
        self.session = session
        self.redis_read = redis_read
        self.redis_write = redis_write

    async def create_folder(self, user_id: uuid.UUID, name: str) -> dict:
        cleaned = name.strip()
        if not cleaned or len(cleaned) > FOLDER_NAME_MAX_LEN:
            raise FavoriteFolderNameInvalidException()

        try:
            folder = await favorite_create_folder(
                self.session, user_id, folder_name=cleaned
            )
            await self.session.flush()
            await self.session.commit()

            return {
                "id": folder.id,
                "name": folder.name,
                "user_id": folder.user_id,
                "created_at": folder.created_at,
                "updated_at": folder.updated_at,
            }
        except IntegrityError as e:
            await self.session.rollback()
            if e.orig is None:
                msg = str(e)
            else:
                msg = str(e.orig)

            if "uq_griver_favorite_folder_user_name_active" in msg:
                raise FavoriteFolderNameDuplicateException() from e
            elif "griver_favorite_folder_user_id_fkey" in msg:
                raise FavoriteUserNotFoundException() from e
            elif "value too long" in msg or "character varying(100)" in msg:
                raise FavoriteFolderNameInvalidException() from e
            else:
                raise FavoriteInternalDataConflict() from e

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
        if self.redis_read is not None and self.redis_write is not None:
            return await get_folder_detail_cached(
                session=self.session,
                redis_read=self.redis_read,
                redis_write=self.redis_write,
                user_id=user_id,
                folder_id=folder_id,
            )
        return await _load_detail_from_db(
            self.session, folder_id=folder_id, user_id=user_id
        )

    async def rename_favorite_folder(
        self, user_id: uuid.UUID, folder_id: uuid.UUID, name: str
    ) -> GriverFavoriteFolder:
        clean_name = name.strip()
        if len(clean_name) == 0 or len(clean_name) > FOLDER_NAME_MAX_LEN:
            raise FavoriteFolderNameInvalidException()

        folder = await favorite_folder_find_by_id_and_user(
            session=self.session, user_id=user_id, folder_id=folder_id
        )

        if not folder:
            raise FavoriteFolderNotFoundException()

        if folder.name == clean_name:
            folder.updated_at = datetime.datetime.now(timezone.utc)
            new_folder = folder
        else:
            try:
                new_folder = await favorite_folder_update_name(
                    session=self.session, folder=folder, new_name=clean_name
                )
            except IntegrityError as e:
                await self.session.rollback()
                if e.orig is None:
                    msg = str(e)
                else:
                    msg = str(e.orig)

                if "uq_griver_favorite_folder_user_name_active" in msg:
                    raise FavoriteFolderNameDuplicateException() from e
                elif "griver_favorite_folder_user_id_fkey" in msg:
                    raise FavoriteUserNotFoundException() from e
                elif "value too long" in msg or "character varying(100)" in msg:
                    raise FavoriteFolderNameInvalidException() from e
                else:
                    raise FavoriteInternalDataConflict() from e

        await self.session.commit()
        if self.redis_write is not None:
            await invalidate_folder_detail(
                self.redis_write, user_id=user_id, folder_id=folder_id
            )
        return new_folder

    async def delete_favorite_folder(
        self, user_id: uuid.UUID, folder_id: uuid.UUID
    ) -> tuple[list[GriverFavoriteItem], GriverFavoriteFolder]:
        items = await favorite_item_soft_delete_by_folder_id(
            self.session, folder_id=folder_id
        )
        folder = await favorite_folder_find_by_id_and_user(
            self.session, user_id=user_id, folder_id=folder_id
        )

        if not folder:
            raise FavoriteFolderNotFoundException()

        deleted_folder = await favorite_folder_soft_delete(self.session, folder=folder)
        await self.session.commit()
        if self.redis_write is not None:
            await invalidate_folder_detail(
                self.redis_write, user_id=user_id, folder_id=folder_id
            )
        return items, deleted_folder
