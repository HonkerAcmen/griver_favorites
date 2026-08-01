import random
import string
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.favorite.exceptions import (
    FavoriteFolderNameInvalidException,
    FavoriteFolderNameDuplicateException,
    FavoriteUserNotFoundException,
)
from apps.favorite.models import GriverFavoriteFolder, GriverFavoriteItem
from apps.favorite.schemas.folder import FavoriteFolderListQueryParams
from apps.favorite.services.folder import FolderService

SEED_ALICE_ID = uuid.UUID("fa500001-0001-4000-8000-000000000001")
SEED_BOB_ID = uuid.UUID("fa500001-0002-4000-8000-000000000002")


async def _create_folder(
    session: AsyncSession, user_id: uuid.UUID, name: str | None = None
) -> tuple[uuid.UUID, str]:
    folder_name = name or str(uuid.uuid4())
    service = FolderService(session=session)
    result = await service.create_folder(user_id=user_id, name=folder_name)
    return uuid.UUID(str(result["id"])), folder_name


@pytest.mark.asyncio
async def test_create_folder_invalid_user_raises(session: AsyncSession):
    service = FolderService(session=session)
    with pytest.raises(FavoriteUserNotFoundException):
        await service.create_folder(user_id=uuid.uuid4(), name="orphan-folder")


@pytest.mark.asyncio
async def test_create_folder_success(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_name = str(uuid.uuid4())
    server = FolderService(session=session)
    result = await server.create_folder(user_id=user_id, name=folder_name)

    assert result["user_id"] == user_id
    assert result["name"] == folder_name
    assert "id" in result


@pytest.mark.asyncio
async def test_create_folder_empty_name_raises(session: AsyncSession):
    user_id = SEED_ALICE_ID
    server = FolderService(session=session)
    with pytest.raises(FavoriteFolderNameInvalidException):
        await server.create_folder(user_id=user_id, name="    ")


@pytest.mark.asyncio
async def test_create_folder_name_too_long_raises(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_name = "k" * 101
    server = FolderService(session=session)
    with pytest.raises(FavoriteFolderNameInvalidException):
        await server.create_folder(user_id=user_id, name=folder_name)


@pytest.mark.asyncio
async def test_create_folder_duplicate_name_raises(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_name = f"dup-{uuid.uuid4()}"
    server = FolderService(session=session)

    await server.create_folder(user_id=user_id, name=folder_name)
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
    folder_id, folder_name = await _create_folder(session, user_id)

    service = FolderService(session=session)
    result = await service.get_favorite_folder_detail(
        user_id=user_id, folder_id=folder_id
    )
    assert result["id"] == folder_id
    assert result["name"] == folder_name
    assert "item_count" in result
    assert result["item_count"] >= 0
    assert "created_at" in result
    assert "updated_at" in result


@pytest.mark.asyncio
async def test_rename_favorite_folder(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_id, _ = await _create_folder(session, user_id)
    new_folder_name = str(uuid.uuid4()) + "-service-test"

    service = FolderService(session)
    new_folder = await service.rename_favorite_folder(
        user_id, folder_id, name=new_folder_name
    )

    assert isinstance(new_folder, GriverFavoriteFolder)
    assert new_folder.id == folder_id
    assert new_folder.user_id == user_id
    assert new_folder.name == new_folder_name

    # 同名再次重命名仍成功（幂等）
    again = await service.rename_favorite_folder(
        user_id, folder_id, name=new_folder_name
    )
    assert again.id == folder_id
    assert again.name == new_folder_name


@pytest.mark.asyncio
async def test_rename_favorite_folder_len_exception(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_id, _ = await _create_folder(session, user_id)
    service = FolderService(session)

    with pytest.raises(FavoriteFolderNameInvalidException):
        await service.rename_favorite_folder(user_id, folder_id, name="   ")


@pytest.mark.asyncio
async def test_delete_favorite_folder(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_id, _ = await _create_folder(session, user_id)

    service = FolderService(session)
    items, delete_folder = await service.delete_favorite_folder(user_id, folder_id)

    if items:
        assert isinstance(items[0], GriverFavoriteItem)
        assert items[0].is_deleted is True

    assert delete_folder.id == folder_id
    assert delete_folder.is_deleted is True


# --- A8：Folder Service 单测补全 ---


@pytest.mark.asyncio
async def test_list_folders_keyword_percent_is_literal(session: AsyncSession):
    """keyword 含 % 时按字面量匹配，不误匹配全表。"""
    user_id = SEED_ALICE_ID
    folder_name = f"TDD-{uuid.uuid4()}-100%-off"
    service = FolderService(session=session)

    await service.create_folder(user_id, folder_name)

    params = FavoriteFolderListQueryParams(
        user_id=user_id, page=1, page_size=10, keyword="%"
    )
    result = await service.list_favorite_folders(params)

    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0].name == folder_name


@pytest.mark.asyncio
async def test_list_folders_page_zero_treated_as_one(session: AsyncSession):
    """page=0 在 Repository 层按第 1 页处理。"""
    user_id = SEED_ALICE_ID
    folder_name = f"page0-{uuid.uuid4()}"
    service = FolderService(session=session)
    await service.create_folder(user_id, folder_name)

    params = FavoriteFolderListQueryParams.model_construct(
        user_id=user_id, page=0, page_size=10, keyword=folder_name
    )
    result = await service.list_favorite_folders(params)

    assert result["total"] == 1
    assert len(result["items"]) == 1


@pytest.mark.asyncio
async def test_list_folders_page_size_clamped_to_max(session: AsyncSession):
    """page_size=200 钳制为 PAGE_MAX(100)。"""
    service = FolderService(session=session)
    params = FavoriteFolderListQueryParams.model_construct(
        user_id=SEED_ALICE_ID, page=1, page_size=200, keyword=""
    )
    result = await service.list_favorite_folders(params)

    assert len(result["items"]) <= 100


@pytest.mark.asyncio
async def test_list_folders_excludes_soft_deleted(session: AsyncSession):
    """软删后 list 不可见。"""
    user_id = SEED_ALICE_ID
    folder_name = f"soft-del-{uuid.uuid4()}"
    service = FolderService(session=session)

    created = await service.create_folder(user_id, folder_name)
    folder_id = uuid.UUID(str(created["id"]))

    params = FavoriteFolderListQueryParams(
        user_id=user_id, page=1, page_size=10, keyword=folder_name
    )
    before = await service.list_favorite_folders(params)
    assert before["total"] == 1

    await service.delete_favorite_folder(user_id, folder_id)

    after = await service.list_favorite_folders(params)
    assert after["total"] == 0
    assert after["items"] == []


@pytest.mark.asyncio
async def test_create_folder_after_soft_delete_same_name(session: AsyncSession):
    """软删后同名可新建。"""
    user_id = SEED_ALICE_ID
    folder_name = f"reuse-{uuid.uuid4()}"
    service = FolderService(session=session)

    first = await service.create_folder(user_id, folder_name)
    first_id = uuid.UUID(str(first["id"]))

    await service.delete_favorite_folder(user_id, first_id)

    second = await service.create_folder(user_id, folder_name)
    assert second["name"] == folder_name
    assert uuid.UUID(str(second["id"])) != first_id


# 测试重命名
@pytest.mark.asyncio
async def test_rename_favorite_folder_rename(session: AsyncSession):
    user_id = SEED_ALICE_ID
    folder_name = str(uuid.uuid4()) + "-service-test-rename"
    new_folder_id, new_folder_name = await _create_folder(
        session=session, user_id=user_id, name=folder_name
    )
    assert folder_name == new_folder_name

    folder_service = FolderService(session)
    new_folder_name = str(uuid.uuid4()) + "-service-test-rename"

    rename_folder = await folder_service.rename_favorite_folder(
        user_id, new_folder_id, new_folder_name
    )
    assert rename_folder.name == new_folder_name

    # 测试名字限制 100 字符
    new_folder_name = str(uuid.uuid4()) + "".join(
        random.choices(string.ascii_letters + string.digits, k=110)
    )
    with pytest.raises(FavoriteFolderNameInvalidException):
        await folder_service.rename_favorite_folder(
            user_id, new_folder_id, new_folder_name
        )

    # 测试strip()
    new_folder_name = "    " + str(uuid.uuid4()) + "-service-test"
    strip_new_folder_name = new_folder_name.strip()
    rename_folder = await folder_service.rename_favorite_folder(
        user_id, new_folder_id, new_folder_name
    )
    assert rename_folder.name == strip_new_folder_name
