from fastapi import APIRouter

from .folder import router as folder_router

router = APIRouter(prefix="/grapi/v1/favorite")
router.include_router(folder_router)