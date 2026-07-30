import uuid
from typing import Annotated

from fastapi import APIRouter, status
from fastapi.params import Depends, Path, Query

from apps.core.response import success
from apps.favorite.dependencies import get_item_service
from apps.favorite.schemas.item import FavoriteItemCreateInSchema
from apps.favorite.services.item import ItemService

router = APIRouter(tags=["favorite_item"])


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
