import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from apps.core.database import SessionLocal, engine
from apps.favorite.models import GriverFavoriteFolder, Intelligence
from apps.favorite.repositories.folder import (
    favorite_create_folder,
    favorite_folder_find_by_id_and_user,
    favorite_folder_count_by_name,
    favorite_folder_list_by_user,
    favorite_folder_count_items,
    favorite_folder_update_name,
)
from apps.favorite.repositories.intelligence import intelligence_find_by_id_not_deleted


@pytest_asyncio.fixture
async def session():
    async with SessionLocal() as s:
        try:
            yield s
        finally:
            await s.rollback()
    await engine.dispose()


SEED_ALICE_ID = uuid.UUID("fa500001-0001-4000-8000-000000000001")
SEED_BOB_ID = uuid.UUID("fa500001-0002-4000-8000-000000000002")
SEED_ALICE_FOLDER_ID = uuid.UUID("fa500001-0001-4000-8000-000000000101")
SEED_INTELLIGENCE_ID = uuid.UUID("fa700001-0001-4000-8000-000000000001")
SEED_INTELLIGENCE_DELETED_ID = uuid.UUID("fa700001-0001-4000-8000-000000000099")


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

    result = await favorite_folder_find_by_id_and_user(session, folder_id, user_id)
    assert result.id is not None
    assert result.name == folder_name
    assert result.user_id == user_id
    assert result.id == folder_id
    assert result.is_deleted is False


@pytest.mark.asyncio
async def test_favorite_folder_find_by_id_and_user_returns_none(session: AsyncSession):
    user_id = SEED_ALICE_ID

    result = await favorite_folder_find_by_id_and_user(session, uuid.uuid4(), user_id)
    assert result is None

    result = await favorite_folder_find_by_id_and_user(
        session, SEED_ALICE_FOLDER_ID, SEED_BOB_ID
    )
    assert result is None


@pytest.mark.asyncio
async def test_favorite_folder_count_by_name_returns_counts(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_name = "TDD测试收藏夹个数"

    assert await favorite_folder_count_by_name(session, user_id, folder_name) == 0

    await favorite_create_folder(session, user_id, folder_name)

    result = await favorite_folder_count_by_name(session, user_id, folder_name)

    assert result == 1

    result = await favorite_folder_count_by_name(session, user_id, "TDD收藏夹个数2")
    assert result == 0


@pytest.mark.asyncio
async def test_favorite_folder_list_by_user_returns_tuple(session: AsyncSession):
    user_id = SEED_ALICE_ID
    page = 1
    page_size = 10
    keyword = "情报"

    items, total = await favorite_folder_list_by_user(
        session, user_id, page, page_size, keyword
    )

    assert isinstance(items, list)
    assert isinstance(total, int)
    assert total == 1
    assert len(items) == 1

    assert all(isinstance(f, GriverFavoriteFolder) for f in items)

    assert items[0].name == "重点情报"
    assert items[0].user_id == user_id
    assert items[0].is_deleted is False


@pytest.mark.asyncio
async def test_favorite_folder_list_by_user_without_keyword(session: AsyncSession):
    user_id = SEED_ALICE_ID

    items, total = await favorite_folder_list_by_user(session, user_id, 1, 10, "")
    assert total == 3
    assert len(items) == 3

    items_ws, total_ws = await favorite_folder_list_by_user(
        session, user_id, 1, 10, "   "
    )
    assert total_ws == 3
    assert len(items_ws) == 3


@pytest.mark.asyncio
async def test_favorite_folder_list_by_user_orders_by_updated_at_desc(
    session: AsyncSession,
):
    user_id = SEED_ALICE_ID

    items, _ = await favorite_folder_list_by_user(session, user_id, 1, 10, "")

    updated_at_list = [folder.updated_at for folder in items]
    assert updated_at_list == sorted(updated_at_list, reverse=True)


@pytest.mark.asyncio
async def test_favorite_folder_list_by_user_keyword_percent_is_literal(
    session: AsyncSession,
):
    user_id = SEED_ALICE_ID
    folder_name = f"TDD-{uuid.uuid4()}-100%-off"

    await favorite_create_folder(session, user_id, folder_name)

    items, total = await favorite_folder_list_by_user(session, user_id, 1, 10, "%")
    assert total == 1
    assert len(items) == 1
    assert items[0].name == folder_name

    _, all_total = await favorite_folder_list_by_user(session, user_id, 1, 10, "")
    assert all_total > total


@pytest.mark.asyncio
async def test_intelligence_find_by_id_not_deleted_returns_bool_or_none(
    session: AsyncSession,
):
    intelligence_id = SEED_INTELLIGENCE_ID
    res: Intelligence = await intelligence_find_by_id_not_deleted(
        session, intelligence_id
    )

    assert isinstance(res, Intelligence)

    res: Intelligence = await intelligence_find_by_id_not_deleted(session, uuid.uuid4())
    assert res is None

    result = await intelligence_find_by_id_not_deleted(
        session, SEED_INTELLIGENCE_DELETED_ID
    )
    assert result is None


@pytest.mark.asyncio
async def test_favorite_folder_count_items_returns_count(session: AsyncSession):
    folder_id = SEED_ALICE_FOLDER_ID
    result = await favorite_folder_count_items(session, folder_id)

    assert isinstance(result, int)
    assert result >= 0


@pytest.mark.asyncio
async def test_favorite_folder_update_name_returns_folder(session: AsyncSession):
    folder_id = SEED_ALICE_FOLDER_ID
    res = await favorite_folder_find_by_id_and_user(session, folder_id, SEED_ALICE_ID)

    new_folder_name = str(uuid.uuid4()) + "-repo-test"

    new_folder = await favorite_folder_update_name(session, res, new_folder_name)

    assert isinstance(new_folder, GriverFavoriteFolder)

    assert new_folder.id == folder_id
    assert new_folder.name == new_folder_name
