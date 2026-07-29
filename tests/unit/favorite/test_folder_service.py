import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from apps.core.database import SessionLocal, engine
from apps.favorite.exceptions import (
    FavoriteFolderNameInvalidException,
    FavoriteFolderNameDuplicateException,
)
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
