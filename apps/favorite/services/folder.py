from sqlalchemy.ext.asyncio import AsyncSession
from apps.favorite.exceptions import FavoriteFolderNameInvalidException

# async def create_folder(user_id, name: str) -> dict:
#     cleaned = name.strip()
#     if not cleaned or len(cleaned) > 100:
#         raise FavoriteFolderNameInvalidException()
#
#     # TODO: Repository 写库
#     # - 查重或依赖唯一索引；重名时：
#     #     raise FavoriteFolderNameDuplicateException()
#     # - 或让 IntegrityError 冒泡，由 exception_handlers 映射（R10）
#     return {
#         "id": "bc047d8d-05f4-4712-90b6-b5010d534ca7",
#         "name": cleaned,
#         "created_at": "2026-07-28T12:00:00+00:00",
#         "updated_at": "2026-07-28T12:00:00+00:00",
#     }


class FolderService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_folder(self, user_id, name):
        pass
