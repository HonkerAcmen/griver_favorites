"""IntegrityError message helpers (R10)."""

from sqlalchemy.exc import IntegrityError

from apps.favorite.exceptions import (
    FavoriteFolderNameDuplicateException,
    FavoriteFolderNameInvalidException,
    FavoriteInternalDataConflict,
    FavoriteItemAlreadyExistsException,
)


def integrity_error_message(exc: IntegrityError) -> str:
    if exc.orig is not None:
        return str(exc.orig)
    return str(exc)


def raise_folder_integrity_error(exc: IntegrityError) -> None:
    msg = integrity_error_message(exc)
    if "uq_griver_favorite_folder_user_name_active" in msg:
        raise FavoriteFolderNameDuplicateException() from exc
    if "value too long" in msg and "character varying(100)" in msg:
        raise FavoriteFolderNameInvalidException() from exc
    raise FavoriteInternalDataConflict() from exc


def raise_item_integrity_error(exc: IntegrityError) -> None:
    msg = integrity_error_message(exc)
    if "uq_griver_favorite_item_folder_target_active" in msg:
        raise FavoriteItemAlreadyExistsException() from exc
    if "uq_griver_favorite_item_user_target_active" in msg:
        raise FavoriteItemAlreadyExistsException() from exc
    raise FavoriteInternalDataConflict() from exc
