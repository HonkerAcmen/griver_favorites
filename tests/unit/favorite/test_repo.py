import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from apps.core.database import SessionLocal
from apps.favorite.repositories.folder import (
    favorite_create_folder,
    favorite_folder_find_by_id_and_user,
)


@pytest_asyncio.fixture
async def session():
    async with SessionLocal() as s:
        yield s
        await s.rollback()


SEED_ALICE_ID = uuid.UUID("fa500001-0001-4000-8000-000000000001")


@pytest.mark.asyncio
async def test_favorite_folder_create_returns_persisted_id(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_name = "TDD收藏夹"
    folder = await favorite_create_folder(session, user_id, folder_name)
    assert folder.id is not None
    assert folder.name == folder_name
    assert folder.user_id == user_id
    assert folder.is_deleted is False


@pytest.mark.asyncio
async def test_favorite_folder_find_by_id_and_user_returns_folder(
    session: AsyncSession,
):
    user_id = SEED_ALICE_ID
    folder_name = "TDD查询收藏夹"

    folder = await favorite_create_folder(session, user_id, folder_name)
    folder_id = folder.id

    result = await favorite_folder_find_by_id_and_user(session, user_id, str(folder_id))
    assert result.id is not None
    assert result.name == folder_name
    assert result.user_id == user_id
    assert result.id == folder_id
    assert result.is_deleted is False
