from fastapi import APIRouter

router = APIRouter(prefix="/folders", tags=["favorite_folder"])

@router.get("")
async  def list_folders():
        return {
                "code": 0,
                "msg": "success",
                "data": None
        }