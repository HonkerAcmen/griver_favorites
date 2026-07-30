from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from apps.core.response import business_fail
from apps.favorite.exceptions import (
    BusinessException,
    FavoriteFolderNameDuplicateException,
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
        # 不把原始 DB 错误暴露给客户端；按约束类型映射业务码
        message = str(exc.orig) if exc.orig else str(exc)
        if "uq_griver_favorite_folder_user_name_active" in message:
            dup = FavoriteFolderNameDuplicateException()
            return JSONResponse(
                status_code=dup.http_status,
                content=business_fail(dup.code, dup.msg),
            )

        if "uq_griver_favorite_item_folder_target_active" in message:
            dup = FavoriteItemAlreadyExistsException()
            return JSONResponse(
                status_code=dup.http_status, content=business_fail(dup.code, dup.msg)
            )
        return JSONResponse(
            status_code=200,
            content=business_fail(500001, "INTERNAL_DATA_CONFLICT"),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.errors()})
