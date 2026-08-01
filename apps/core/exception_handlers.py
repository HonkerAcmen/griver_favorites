from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from apps.core.response import business_fail
from apps.favorite.common.integrity import (
    integrity_error_message,
)
from apps.favorite.exceptions import (
    BusinessException,
    FavoriteFolderNameDuplicateException,
    FavoriteFolderNameInvalidException,
    FavoriteInternalDataConflict,
    FavoriteItemAlreadyExistsException,
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessException)
    async def handle_business_exception(
        request: Request, exc: BusinessException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content=business_fail(exc.code, exc.msg),
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        message = integrity_error_message(exc)
        if "uq_griver_favorite_folder_user_name_active" in message:
            biz = FavoriteFolderNameDuplicateException()
        elif "uq_griver_favorite_item_folder_target_active" in message:
            biz = FavoriteItemAlreadyExistsException()
        elif "uq_griver_favorite_item_user_target_active" in message:
            biz = FavoriteItemAlreadyExistsException()
        elif "value too long" in message and "character varying(100)" in message:
            biz = FavoriteFolderNameInvalidException()
        else:
            biz = FavoriteInternalDataConflict()
        return JSONResponse(
            status_code=biz.http_status,
            content=business_fail(biz.code, biz.msg),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.errors()})
