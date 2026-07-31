import uuid

from fastapi import Query
from pydantic import BaseModel


class FavoriteItemCreateInSchema(BaseModel):
    user_id: uuid.UUID
    intelligence_id: uuid.UUID


class FavoriteItemMoveInSchema(BaseModel):
    user_id: uuid.UUID
    target_folder_id: uuid.UUID


class FavoriteItemListQueryParams(BaseModel):
    user_id: uuid.UUID
    page: int = Query(default=1, ge=1, description="页码，从1开始")
    page_size: int = Query(default=10, ge=1, le=100, description="每页数量")
    keyword: str | None = Query(default=None, description="intelligence.title 模糊搜索")
