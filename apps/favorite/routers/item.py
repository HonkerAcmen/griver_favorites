import uuid
from typing import Annotated

from fastapi import APIRouter, status
from fastapi.params import Depends, Path, Query

from apps.core.response import success
from apps.favorite.dependencies import get_item_service
from apps.favorite.schemas.item import (
    FavoriteItemCreateInSchema,
    FavoriteItemListQueryParams,
    FavoriteItemMoveInSchema,
)
from apps.favorite.services.item import ItemService

router = APIRouter(tags=["favorite_item"])


@router.get("/folders/{folder_id}/items", status_code=status.HTTP_200_OK)
async def list_items_in_folder(
    folder_id: Annotated[uuid.UUID, Path(description="收藏夹ID")],
    params: Annotated[FavoriteItemListQueryParams, Query()],
    service: ItemService = Depends(get_item_service),
):
    result = await service.list_items_in_folder(folder_id=folder_id, params=params)
    return success(data=result)


@router.post("/folders/{folder_id}/items", status_code=status.HTTP_201_CREATED)
async def add_item_to_folder(
    folder_id: Annotated[uuid.UUID, Path(description="收藏夹ID")],
    payload: FavoriteItemCreateInSchema,
    service: ItemService = Depends(get_item_service),
):
    result = await service.add_item_to_folder(
        user_id=payload.user_id,
        folder_id=folder_id,
        intelligence_id=payload.intelligence_id,
    )
    return success(data=result)


@router.delete("/folders/{folder_id}/items/{item_id}")
async def remove_item_from_folder(
    folder_id: Annotated[uuid.UUID, Path(description="收藏夹ID")],
    item_id: Annotated[uuid.UUID, Path(description="收藏项ID")],
    user_id: Annotated[uuid.UUID, Query(description="用户ID")],
    service: ItemService = Depends(get_item_service),
):
    result = await service.remove_item_from_folder(
        user_id=user_id, folder_id=folder_id, item_id=item_id
    )
    return success(data=result)


@router.put("/items/{item_id}/move", status_code=status.HTTP_200_OK)
async def move_item(
    item_id: Annotated[uuid.UUID, Path(description="收藏夹ID")],
    payload: FavoriteItemMoveInSchema,
    service: ItemService = Depends(get_item_service),
):
    result = await service.move_item(
        user_id=payload.user_id,
        item_id=item_id,
        target_folder_id=payload.target_folder_id,
    )
    return success(data=result)
