import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.favorite.models import GriverFavoriteFolder, Intelligence, GriverFavoriteItem
from apps.favorite.repositories.folder import (
    favorite_create_folder,
    favorite_folder_find_by_id_and_user,
    favorite_folder_count_by_name,
    favorite_folder_list_by_user,
    favorite_folder_count_items,
    favorite_folder_update_name,
    favorite_folder_soft_delete,
    favorite_item_soft_delete_by_folder_id,
)
from apps.favorite.repositories.intelligence import intelligence_find_by_id_not_deleted
from apps.favorite.repositories.item import (
    favorite_item_create,
    favorite_item_find_by_id_and_user,
    favorite_item_find_in_folder,
    favorite_item_soft_delete,
    favorite_item_list_by_folder,
)
from apps.favorite.repositories.operation_log import operation_log_create
from apps.favorite.repositories.user import user_find_active_by_id

SEED_ALICE_ID = uuid.UUID("fa500001-0001-4000-8000-000000000001")
SEED_BOB_ID = uuid.UUID("fa500001-0002-4000-8000-000000000002")
SEED_ALICE_FOLDER_ID = uuid.UUID("fa500001-0001-4000-8000-000000000101")
SEED_INTELLIGENCE_ID = uuid.UUID("fa700001-0001-4000-8000-000000000001")
SEED_INTELLIGENCE_DELETED_ID = uuid.UUID("fa700001-0001-4000-8000-000000000099")


@pytest.mark.asyncio
async def test_user_find_active_by_id(session: AsyncSession):
    found = await user_find_active_by_id(session, SEED_ALICE_ID)
    assert found is not None
    assert found.id == SEED_ALICE_ID
    assert found.is_deleted is False

    assert await user_find_active_by_id(session, uuid.uuid4()) is None


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
    keyword = f"情报-{uuid.uuid4()}"
    folder_name = f"TDD{keyword}"
    await favorite_create_folder(session, user_id, folder_name)

    items, total = await favorite_folder_list_by_user(session, user_id, 1, 10, keyword)

    assert isinstance(items, list)
    assert total == 1
    assert len(items) == 1
    assert items[0].name == folder_name
    assert items[0].user_id == user_id
    assert items[0].is_deleted is False


@pytest.mark.asyncio
async def test_favorite_folder_list_by_user_without_keyword(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_name = f"all-{uuid.uuid4()}"
    await favorite_create_folder(session, user_id, folder_name)

    items, total = await favorite_folder_list_by_user(
        session, user_id, 1, 10, folder_name
    )
    assert total == 1
    assert len(items) == 1

    items_ws, total_ws = await favorite_folder_list_by_user(
        session, user_id, 1, 10, "   "
    )
    assert total_ws >= total
    assert len(items_ws) >= 1


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
    user_id = SEED_ALICE_ID
    folder = await favorite_create_folder(session, user_id, f"rename-{uuid.uuid4()}")
    new_folder_name = str(uuid.uuid4()) + "-repo-test"

    new_folder = await favorite_folder_update_name(session, folder, new_folder_name)

    assert isinstance(new_folder, GriverFavoriteFolder)
    assert new_folder.id == folder.id
    assert new_folder.name == new_folder_name


@pytest.mark.asyncio
async def test_favorite_folder_soft_delete(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder = await favorite_create_folder(session, user_id, f"del-{uuid.uuid4()}")

    delete_folder = await favorite_folder_soft_delete(session, folder)

    assert delete_folder.id == folder.id
    assert delete_folder.name == folder.name
    assert delete_folder.is_deleted is True


@pytest.mark.asyncio
async def test_favorite_item_soft_delete_by_folder_id(session: AsyncSession):
    folder_id = SEED_ALICE_FOLDER_ID

    items = await favorite_item_soft_delete_by_folder_id(session, folder_id)

    if len(items) > 0:
        assert isinstance(items, list)
        assert isinstance(items[0], GriverFavoriteItem)

        assert items[0].folder_id == folder_id
        assert items[0].is_deleted is True


@pytest.mark.asyncio
async def test_favorite_item_create(session: AsyncSession):
    folder_id = SEED_ALICE_FOLDER_ID
    user_id = SEED_ALICE_ID

    target_id = uuid.uuid4()
    target_type = "test-type"
    new_item = await favorite_item_create(
        session,
        folder_id=folder_id,
        user_id=user_id,
        target_id=target_id,
        target_type=target_type,
    )

    assert new_item.folder_id == folder_id
    assert new_item.user_id == user_id
    assert new_item.target_id == target_id
    assert new_item.target_type == target_type
    assert new_item.is_deleted is False
    assert new_item.created_at is not None


@pytest.mark.asyncio
async def test_favorite_item_find_by_id_and_user(session: AsyncSession):
    user_id = SEED_ALICE_ID
    item = await favorite_item_create(
        session,
        folder_id=SEED_ALICE_FOLDER_ID,
        user_id=user_id,
        target_id=uuid.uuid4(),
        target_type="test-type",
    )

    find_item = await favorite_item_find_by_id_and_user(
        session, item_id=item.id, user_id=user_id
    )
    assert find_item is not None
    if find_item:
        assert isinstance(find_item, GriverFavoriteItem)
        assert find_item.id == item.id
        assert find_item.user_id == user_id

        assert find_item.is_deleted is False


@pytest.mark.asyncio
async def test_favorite_item_find_in_folder(session: AsyncSession):
    folder_id = SEED_ALICE_FOLDER_ID
    target_id = uuid.uuid4()
    target_type = "test-type"
    await favorite_item_create(
        session,
        folder_id=folder_id,
        user_id=SEED_ALICE_ID,
        target_id=target_id,
        target_type=target_type,
    )

    item = await favorite_item_find_in_folder(
        session, folder_id=folder_id, target_id=target_id, target_type=target_type
    )

    assert item is not None

    if item is not None:
        assert isinstance(item, GriverFavoriteItem)
        assert item.folder_id == folder_id
        assert item.target_id == target_id
        assert item.target_type == target_type

        assert item.is_deleted is False


@pytest.mark.asyncio
async def test_favorite_item_soft_delete(session: AsyncSession):
    user_id = SEED_ALICE_ID
    delete_item = await favorite_item_create(
        session,
        folder_id=SEED_ALICE_FOLDER_ID,
        user_id=user_id,
        target_id=uuid.uuid4(),
        target_type="test-type",
    )

    deleted_item = await favorite_item_soft_delete(session=session, item=delete_item)
    assert isinstance(deleted_item, GriverFavoriteItem)
    assert deleted_item.id == delete_item.id
    assert deleted_item.is_deleted is True


@pytest.mark.asyncio
async def test_favorite_item_list_by_folder_basic_success(session: AsyncSession):
    """测试基本查询功能：成功返回 (GriverFavoriteItem, Intelligence) 元组列表和总数"""
    folder_id = SEED_ALICE_FOLDER_ID
    page = 1
    page_size = 10
    keyword = "  "

    rows, total = await favorite_item_list_by_folder(
        session, folder_id=folder_id, page=page, page_size=page_size, keyword=keyword
    )

    assert isinstance(rows, list)
    assert isinstance(total, int)
    assert total >= 0

    if rows:
        for item, intel in rows:
            assert isinstance(item, GriverFavoriteItem)
            assert isinstance(intel, Intelligence)

            assert item.folder_id == folder_id
            assert item.is_deleted is False
            assert item.target_type == "intelligence"
            assert item.target_id == intel.id


@pytest.mark.asyncio
async def test_favorite_item_list_by_folder_keyword_filter(session: AsyncSession):
    """TDD 测试：动态关键词 (ILIKE) 过滤功能"""
    folder_id = SEED_ALICE_FOLDER_ID

    # 准备带有特殊关键词的测试数据
    target_kw = f"TDD_TEST_{uuid.uuid4().hex[:8]}"

    intel = Intelligence(
        id=uuid.uuid4(), user_id=SEED_ALICE_ID, title=f"Important {target_kw} Report"
    )
    session.add(intel)
    await session.flush()

    item = GriverFavoriteItem(
        id=uuid.uuid4(),
        user_id=SEED_ALICE_ID,
        folder_id=folder_id,
        target_type="intelligence",
        target_id=intel.id,
        is_deleted=False,
    )
    session.add(item)
    await session.flush()

    rows, total = await favorite_item_list_by_folder(
        session, folder_id=folder_id, page=1, page_size=10, keyword=target_kw
    )

    assert total >= 1
    matched_titles = [intel_obj.title for _, intel_obj in rows]
    assert any(target_kw in title for title in matched_titles)

    rows_empty, total_empty = await favorite_item_list_by_folder(
        session,
        folder_id=folder_id,
        page=1,
        page_size=10,
        keyword="NON_EXISTENT_KW_999",
    )

    assert total_empty == 0
    assert len(rows_empty) == 0


@pytest.mark.asyncio
async def test_favorite_item_list_by_folder_exclude_soft_deleted(session: AsyncSession):
    """TDD 测试：确保已被软删除 (is_deleted=True) 的收藏项不会被查出"""
    folder_id = SEED_ALICE_FOLDER_ID

    intel = Intelligence(
        id=uuid.uuid4(),
        user_id=SEED_ALICE_ID,
        title=f"Deleted_Intel_{uuid.uuid4().hex[:6]}",
    )
    session.add(intel)
    await session.flush()

    deleted_item = GriverFavoriteItem(
        id=uuid.uuid4(),
        user_id=SEED_ALICE_ID,
        folder_id=folder_id,
        target_type="intelligence",
        target_id=intel.id,
        is_deleted=True,
    )
    session.add(deleted_item)
    await session.flush()

    rows, _ = await favorite_item_list_by_folder(
        session, folder_id=folder_id, page=1, page_size=100
    )

    returned_item_ids = [item.id for item, _ in rows]
    assert deleted_item.id not in returned_item_ids


@pytest.mark.asyncio
async def test_favorite_item_list_by_folder_pagination_clamp(session: AsyncSession):
    """TDD 测试：验证分页边界限制（如 page <= 0, page_size > 100 自动修正）"""
    folder_id = SEED_ALICE_FOLDER_ID

    rows, total = await favorite_item_list_by_folder(
        session, folder_id=folder_id, page=0, page_size=500
    )

    assert isinstance(rows, list)
    assert len(rows) <= 100


# test_operation_log_create_success 插入后 DB 有行，字段正确
@pytest.mark.asyncio
async def test_operation_log_create_success(session: AsyncSession):
    event_id = uuid.uuid4()
    user_id = SEED_ALICE_ID
    folder_id = SEED_ALICE_FOLDER_ID
    intelligence_id = SEED_INTELLIGENCE_ID
    action = "repo-test"

    row = await operation_log_create(
        session,
        event_id=event_id,
        user_id=user_id,
        folder_id=folder_id,
        intelligence_id=intelligence_id,
        action=action,
    )

    assert row.event_id == event_id
    assert row.user_id == user_id
    assert row.folder_id == folder_id
    assert row.intelligence_id == intelligence_id


# test_operation_log_duplicate_event_id_raises 同一 event_id 插两次 → IntegrityError
@pytest.mark.asyncio
async def test_operation_log_duplicate_event_id_raises(session: AsyncSession):
    event_id = uuid.uuid4()
    user_id = SEED_ALICE_ID
    folder_id = SEED_ALICE_FOLDER_ID
    intelligence_id = SEED_INTELLIGENCE_ID
    action = "repo-test"

    await operation_log_create(
        session,
        event_id=event_id,
        user_id=user_id,
        folder_id=folder_id,
        intelligence_id=intelligence_id,
        action=action,
    )

    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        await operation_log_create(
            session,
            event_id=event_id,
            user_id=user_id,
            folder_id=folder_id,
            intelligence_id=intelligence_id,
            action=action,
        )
