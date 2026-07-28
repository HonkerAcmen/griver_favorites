from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    code: int = 0
    msg: str = "success"
    data: T | None = None


class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


def success(data: Any = None, msg: str = "success") -> dict[str, Any]:
    """成功响应：HTTP 201/200 由路由 status_code 决定，body 统一 code=0。"""
    return {"code": 0, "msg": msg, "data": data}


def business_fail(code: int, msg: str, data: Any = None) -> dict[str, Any]:
    """业务失败 body：配合 exception_handler 返回 HTTP 200。"""
    return {"code": code, "msg": msg, "data": data if data is not None else {}}
