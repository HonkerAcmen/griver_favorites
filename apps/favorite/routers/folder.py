
from fastapi import APIRouter, status
from fastapi.params import Depends

from apps.core.response import success
from apps.favorite.dependencies import get_folder_service
from apps.favorite.schemas.folder import FavoriteFolderCreateInSchema
from apps.favorite.services.folder import FolderService

router = APIRouter(prefix="/folders", tags=["favorite_folder"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_folder(
        payload: FavoriteFolderCreateInSchema,
        service: FolderService = Depends(get_folder_service)
):
        folder = await service.create_folder(payload.user_id, payload.name)
        return success(data=folder)