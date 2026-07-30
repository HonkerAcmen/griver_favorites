from fastapi import APIRouter

from .folder import router as folder_router
from .item import router as item_router

router = APIRouter(prefix="/grapi/v1/favorite")
router.include_router(folder_router)
router.include_router(item_router)
