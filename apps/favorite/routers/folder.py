import uuid
from typing import Annotated

from fastapi import APIRouter, status
from fastapi.params import Depends, Query, Path

from apps.core.response import success
from apps.favorite.dependencies import get_folder_service
from apps.favorite.schemas.folder import (
    FavoriteFolderCreateInSchema,
    FavoriteFolderListQueryParams,
    FavoriteFolderUpdateInSchema,
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


@router.get("/{folder_id}", status_code=status.HTTP_200_OK)
async def get_favorite_folder_detail(
    folder_id: Annotated[uuid.UUID, Path(description="收藏夹ID")],
    user_id: Annotated[uuid.UUID, Query(description="用户ID")],
    service: FolderService = Depends(get_folder_service),
):
    res = await service.get_favorite_folder_detail(user_id, folder_id)
    return success(data=res)


@router.patch("/{folder_id}", status_code=status.HTTP_200_OK)
async def renamerename_favorite_folder(
    folder_id: Annotated[uuid.UUID, Path(description="收藏夹ID")],
    params: Annotated[FavoriteFolderUpdateInSchema, Query()],
    service: FolderService = Depends(get_folder_service),
):
    res = await service.rename_favorite_folder(
        folder_id=folder_id, user_id=params.user_id, name=params.name
    )

    return success(data=res)
