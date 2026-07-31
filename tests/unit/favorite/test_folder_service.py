import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.favorite.exceptions import (
    FavoriteFolderNameInvalidException,
    FavoriteFolderNameDuplicateException,
    FavoriteFolderNotFoundException,
    FavoriteItemAlreadyExistsException,
    FavoriteItemNotFoundException,
)
from apps.favorite.models import GriverFavoriteFolder, GriverFavoriteItem
from apps.favorite.repositories.item import favorite_item_find_in_folder
from apps.favorite.schemas.folder import FavoriteFolderListQueryParams
from apps.favorite.services.folder import FolderService
from apps.favorite.services.item import ItemService

SEED_ALICE_ID = uuid.UUID("fa500001-0001-4000-8000-000000000001")
SEED_BOB_ID = uuid.UUID("fa500001-0002-4000-8000-000000000002")
SEED_ALICE_FOLDER_ID = uuid.UUID("fa500001-0001-4000-8000-000000000101")
SEED_INTELLIGENCE_ID = uuid.UUID("fa700001-0001-4000-8000-000000000001")
SEED_INTELLIGENCE_DELETED_ID = uuid.UUID("fa700001-0001-4000-8000-000000000099")


async def _create_folder(
    session: AsyncSession, user_id: uuid.UUID, name: str | None = None
) -> tuple[uuid.UUID, str]:
    folder_name = name or str(uuid.uuid4())
    service = FolderService(session=session)
    result = await service.create_folder(user_id=user_id, name=folder_name)
    return uuid.UUID(str(result["id"])), folder_name


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


@pytest.mark.asyncio
async def test_add_item_to_folder(session: AsyncSession):
    service = ItemService(session=session)
    folder_service = FolderService(session=session)
    folder_name = str(uuid.uuid4()) + "-service-test"
    intelligence_id = SEED_INTELLIGENCE_ID
    user_id = SEED_ALICE_ID

    # TODO 注意此处，情报需要创建新的，再添加到文件夹中，再删除出去，这里进行了简化，后期酌情修改
    create_folder = await folder_service.create_folder(
        user_id=user_id, name=folder_name
    )

    item = await service.add_item_to_folder(
        user_id=SEED_ALICE_ID,
        folder_id=create_folder["id"],
        intelligence_id=intelligence_id,
    )

    assert item is not None
    assert isinstance(item, dict)

    assert item["target_id"] == intelligence_id
    assert item["is_deleted"] is False

    await folder_service.delete_favorite_folder(user_id, create_folder["id"])
    with pytest.raises(FavoriteFolderNotFoundException):
        await service.add_item_to_folder(user_id, create_folder["id"], intelligence_id)

    # folder内item不重复
    create_folder = await folder_service.create_folder(
        user_id=user_id, name=folder_name
    )
    await service.add_item_to_folder(user_id, create_folder["id"], intelligence_id)
    with pytest.raises(FavoriteItemAlreadyExistsException):
        await service.add_item_to_folder(user_id, create_folder["id"], intelligence_id)
    await folder_service.delete_favorite_folder(user_id, create_folder["id"])


@pytest.mark.asyncio
async def test_remove_item_from_folder(session: AsyncSession):
    item_service = ItemService(session=session)
    folder_service = FolderService(session=session)
    user_id = SEED_ALICE_ID
    intelligence_id = SEED_INTELLIGENCE_ID

    create_folder = await folder_service.create_folder(
        user_id=user_id, name=f"remove-item-{uuid.uuid4()}"
    )
    folder_id = uuid.UUID(str(create_folder["id"]))

    # 遇到不存在的 item_id
    new_item = await item_service.add_item_to_folder(
        user_id=user_id, folder_id=folder_id, intelligence_id=intelligence_id
    )
    with pytest.raises(FavoriteItemNotFoundException):
        await item_service.remove_item_from_folder(
            user_id=user_id, folder_id=folder_id, item_id=uuid.uuid4()
        )

    await item_service.remove_item_from_folder(
        user_id=user_id, folder_id=folder_id, item_id=new_item["id"]
    )

    # 能正常删除
    new_item = await item_service.add_item_to_folder(
        user_id=user_id, folder_id=folder_id, intelligence_id=intelligence_id
    )
    delete_item = await item_service.remove_item_from_folder(
        user_id=user_id, folder_id=folder_id, item_id=new_item["id"]
    )
    assert delete_item["user_id"] == user_id
    assert delete_item["folder_id"] == folder_id
    assert delete_item["target_id"] == intelligence_id

    # TODO 遇到不存在的user_id 以后再补 不是本轮任务
    # new_item = await item_service.add_item_to_folder(user_id=user_id, folder_id=folder_id, intelligence_id=intelligence_id)

    # 遇到不存在的folder_id
    new_item = await item_service.add_item_to_folder(
        user_id=user_id, folder_id=folder_id, intelligence_id=intelligence_id
    )
    with pytest.raises(FavoriteItemNotFoundException):
        await item_service.remove_item_from_folder(
            user_id=user_id, folder_id=uuid.uuid4(), item_id=new_item["id"]
        )

    await item_service.remove_item_from_folder(
        user_id=user_id, folder_id=folder_id, item_id=new_item["id"]
    )

    # 被删除的item是不是这个folder的
    new_item = await item_service.add_item_to_folder(
        user_id=user_id, folder_id=folder_id, intelligence_id=intelligence_id
    )
    delete_item = await item_service.remove_item_from_folder(
        user_id=user_id, folder_id=folder_id, item_id=new_item["id"]
    )
    assert delete_item["folder_id"] == folder_id


@pytest.mark.asyncio
async def test_move_item(session: AsyncSession):
    item_service = ItemService(session=session)
    folder_service = FolderService(session=session)
    user_id = SEED_ALICE_ID
    intelligence_id = SEED_INTELLIGENCE_ID

    source_folder_id, _ = await _create_folder(
        session, user_id, f"move-src-{uuid.uuid4()}"
    )
    target_folder_id, _ = await _create_folder(
        session, user_id, f"move-dst-{uuid.uuid4()}"
    )

    # item 不存在
    with pytest.raises(FavoriteItemNotFoundException):
        await item_service.move_item(
            user_id=user_id,
            item_id=uuid.uuid4(),
            target_folder_id=target_folder_id,
        )

    item = await item_service.add_item_to_folder(
        user_id=user_id,
        folder_id=source_folder_id,
        intelligence_id=intelligence_id,
    )
    item_id = item["id"]

    # 非 item 所属 user
    with pytest.raises(FavoriteItemNotFoundException):
        await item_service.move_item(
            user_id=SEED_BOB_ID,
            item_id=item_id,
            target_folder_id=target_folder_id,
        )

    # 来源 folder 已不含该 item（已软删，R5）
    await item_service.remove_item_from_folder(
        user_id=user_id, folder_id=source_folder_id, item_id=item_id
    )
    with pytest.raises(FavoriteItemNotFoundException):
        await item_service.move_item(
            user_id=user_id,
            item_id=item_id,
            target_folder_id=target_folder_id,
        )

    # 重新添加，用于后续场景
    item = await item_service.add_item_to_folder(
        user_id=user_id,
        folder_id=source_folder_id,
        intelligence_id=intelligence_id,
    )
    item_id = item["id"]

    # 目标 folder 已有同一 intelligence（R6）
    await item_service.add_item_to_folder(
        user_id=user_id,
        folder_id=target_folder_id,
        intelligence_id=intelligence_id,
    )
    with pytest.raises(FavoriteItemAlreadyExistsException):
        await item_service.move_item(
            user_id=user_id,
            item_id=item_id,
            target_folder_id=target_folder_id,
        )

    # 成功移动：来源软删，目标新建
    success_src_id, _ = await _create_folder(
        session, user_id, f"move-ok-src-{uuid.uuid4()}"
    )
    success_dst_id, _ = await _create_folder(
        session, user_id, f"move-ok-dst-{uuid.uuid4()}"
    )
    movable = await item_service.add_item_to_folder(
        user_id=user_id,
        folder_id=success_src_id,
        intelligence_id=intelligence_id,
    )
    movable_id = movable["id"]

    moved = await item_service.move_item(
        user_id=user_id,
        item_id=movable_id,
        target_folder_id=success_dst_id,
    )

    assert moved["folder_id"] == success_dst_id
    assert moved["target_id"] == intelligence_id
    assert moved["is_deleted"] is False

    # 来源 item 已被软删
    source_row = await session.get(GriverFavoriteItem, movable_id)
    assert source_row is not None
    assert source_row.is_deleted is True
    assert source_row.folder_id == success_src_id

    # 来源 folder 查不到 active item
    assert (
        await favorite_item_find_in_folder(
            session,
            folder_id=success_src_id,
            target_type="intelligence",
            target_id=intelligence_id,
        )
        is None
    )

    # 目标 folder 有 active item
    target_row = await favorite_item_find_in_folder(
        session,
        folder_id=success_dst_id,
        target_type="intelligence",
        target_id=intelligence_id,
    )
    assert target_row is not None
    assert target_row.id == moved["id"]
    assert target_row.is_deleted is False

    # 清理
    await folder_service.delete_favorite_folder(user_id, source_folder_id)
    await folder_service.delete_favorite_folder(user_id, target_folder_id)
    await folder_service.delete_favorite_folder(user_id, success_src_id)
    await folder_service.delete_favorite_folder(user_id, success_dst_id)
