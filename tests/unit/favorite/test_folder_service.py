import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from apps.core.database import SessionLocal, engine
from apps.favorite.exceptions import (
    FavoriteFolderNameInvalidException,
    FavoriteFolderNameDuplicateException,
)
from apps.favorite.models import GriverFavoriteFolder
from apps.favorite.schemas.folder import FavoriteFolderListQueryParams
from apps.favorite.services.folder import FolderService


@pytest_asyncio.fixture
async def session():
    async with SessionLocal() as s:
        try:
            yield s
        finally:
            await s.rollback()
    await engine.dispose()


SEED_ALICE_ID = uuid.UUID("fa500001-0001-4000-8000-000000000001")
SEED_ALICE_FOLDER_ID = uuid.UUID("fa500001-0001-4000-8000-000000000101")


@pytest.mark.asyncio
async def test_create_folder_success(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_name = str(uuid.uuid4())
    server = FolderService(session=session)
    result = await server.create_folder(user_id=user_id, name=folder_name)

    assert result["user_id"] == user_id
    assert result["name"] == folder_name


@pytest.mark.asyncio
async def test_create_folder_empty_name_raises(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_name = "    "
    server = FolderService(session=session)
    with pytest.raises(FavoriteFolderNameInvalidException):
        await server.create_folder(user_id=user_id, name=folder_name)


@pytest.mark.asyncio
async def test_create_folder_name_too_long_raises(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_name = "kkawdkaklwdklawdlkawlkdklawdnlakldsnaksdnakdwnawdnawlkdnlawdnalkwndlknasnlklklwaknlnkalnkadlkanldknlawdnlkawdlknalwkndaklnwdlnkawdlknadwklnandkankmdnkamawdakjnwdnaknjdkknsdknawkdnkjawdjknawdknjawdkjnawdjkakjwdnkawkajwdawknjdakj"
    server = FolderService(session=session)
    with pytest.raises(FavoriteFolderNameInvalidException):
        await server.create_folder(user_id=user_id, name=folder_name)


@pytest.mark.asyncio
async def test_create_folder_duplicate_name_raises(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_name = "test_create_folder_success3"
    server = FolderService(session=session)

    with pytest.raises(FavoriteFolderNameDuplicateException):
        await server.create_folder(user_id=user_id, name=folder_name)


@pytest.mark.asyncio
async def test_list_favorite_folders(session: AsyncSession):
    service = FolderService(session=session)
    params = FavoriteFolderListQueryParams(
        user_id=SEED_ALICE_ID, page=1, page_size=10, keyword=" "
    )

    result = await service.list_favorite_folders(params)

    assert all(isinstance(i, GriverFavoriteFolder) for i in result["items"])
    assert "total" in result
    assert result["page"] == params.page
    assert result["page_size"] == params.page_size


@pytest.mark.asyncio
async def test_get_favorite_folder_detail(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_id = SEED_ALICE_FOLDER_ID

    service = FolderService(session=session)
    result = await service.get_favorite_folder_detail(
        user_id=user_id, folder_id=folder_id
    )
    assert isinstance(result, dict)
    assert result["id"] == folder_id

    assert "name" in result
    assert len(result["name"]) <= 100

    assert "item_count" in result
    assert result["item_count"] >= 0

    assert "created_at" in result
    assert "updated_at" in result


@pytest.mark.asyncio
async def test_rename_favorite_folder(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_id = SEED_ALICE_FOLDER_ID
    new_folder_name = str(uuid.uuid4()) + "-service-test"

    service = FolderService(session)
    new_folder = await service.rename_favorite_folder(
        user_id, folder_id, name=new_folder_name
    )

    assert isinstance(new_folder, GriverFavoriteFolder)

    assert new_folder.id == folder_id
    assert new_folder.user_id == user_id
    assert new_folder.name == new_folder_name

    # 测试再次重命名是否幂等
    new_folder = await service.rename_favorite_folder(
        user_id, folder_id, name=new_folder_name
    )
    assert new_folder.id == folder_id
    assert new_folder.user_id == user_id
    assert new_folder.name == new_folder_name


@pytest.mark.asyncio
async def test_rename_favorite_folder_len_exception(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_id = SEED_ALICE_FOLDER_ID
    new_folder_name = "   "

    service = FolderService(session)

    with pytest.raises(FavoriteFolderNameInvalidException):
        await service.rename_favorite_folder(user_id, folder_id, name=new_folder_name)
