from typing import Annotated

from fastapi import APIRouter, status
from fastapi.params import Depends, Query

from apps.core.response import success
from apps.favorite.dependencies import get_folder_service
from apps.favorite.schemas.folder import (
    FavoriteFolderCreateInSchema,
    FavoriteFolderListQueryParams,
)
from apps.favorite.services.folder import FolderService

router = APIRouter(prefix="/folders", tags=["favorite_folder"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_folder(
    payload: FavoriteFolderCreateInSchema,
    service: FolderService = Depends(get_folder_service),
):
    folder = await service.create_folder(payload.user_id, payload.name)
    return success(data=folder)


@router.get("", status_code=status.HTTP_200_OK)
async def list_favorite_folders(
    payload: Annotated[FavoriteFolderListQueryParams, Query()],
    service: FolderService = Depends(get_folder_service),
):
    result = await service.list_favorite_folders(params=payload)
    return success(data=result)
