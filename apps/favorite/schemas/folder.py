import uuid

from fastapi import Query
from pydantic import BaseModel


class FavoriteFolderCreateInSchema(BaseModel):
    user_id: uuid.UUID
    name: str


class FavoriteFolderListQueryParams(BaseModel):
    user_id: uuid.UUID
    page: int = Query(default=1, ge=1, description="页码，从1开始")
    page_size: int = Query(default=10, ge=1, le=100, description="每页数量")
    keyword: str | None = Query(default=None, description="搜索关键字")


class FavoriteFolderUpdateInSchema(BaseModel):
    user_id: uuid.UUID
    name: str


