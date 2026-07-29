from sqlalchemy.ext.asyncio import AsyncSession

from apps.favorite.models import GriverFavoriteFolder


# 创建新文件夹
async def favorite_create_folder(
    session: AsyncSession, user_id: str, folder_name: str
) -> GriverFavoriteFolder:
    folder = GriverFavoriteFolder(user_id=user_id, name=folder_name)
    session.add(folder)
    await session.flush()
    return folder
