import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from apps.favorite.schemas.folder import (
    FavoriteFolderListQueryParams,
    FavoriteFolderUpdateInSchema,
    FavoriteFolderCreateInSchema,
)
from main import app

SEED_ALICE_ID = uuid.UUID("fa500001-0001-4000-8000-000000000001")
SEED_ALICE_FOLDER_ID = uuid.UUID("fa500001-0001-4000-8000-000000000101")
SEED_INTELLIGENCE_ID = uuid.UUID("fa700001-0001-4000-8000-000000000001")

SEED_BOB_ID = uuid.UUID("fa500001-0002-4000-8000-000000000002")
SEED_BOB_FOLDER_ID = uuid.UUID("fa500001-0002-4000-8000-000000000101")

FOLDER_DEFAULT_URL = "/grapi/v1/favorite/folders"
FOLDER_ITEMS_URL = FOLDER_DEFAULT_URL + "/{folder_id}/items"
ITEM_MOVE_URL = "/grapi/v1/favorite/items/{item_id}/move"


async def _list_folder_items(
    ac: AsyncClient, folder_id: str, user_id: uuid.UUID
) -> dict:
    resp = await ac.get(
        FOLDER_ITEMS_URL.format(folder_id=folder_id),
        params={"user_id": str(user_id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    return body["data"]


def _intel_ids(items: list[dict]) -> set[str]:
    return {item["intelligence_id"] for item in items}


@pytest.mark.asyncio
async def test_create_folder():
    user_id = SEED_ALICE_ID
    folder_name = str(uuid.uuid4()) + "-router-test"

    # 使用 AsyncClient 配合 ASGITransport 访问本地 FastAPI 应用
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/grapi/v1/favorite/folders",
            json={
                "user_id": str(user_id),
                "name": folder_name,
            },
        )

    assert response.status_code == 201

    res_data = response.json()
    assert res_data["code"] == 0
    assert res_data["msg"] == "success"

    folder_data = res_data["data"]
    assert folder_data["name"] == folder_name
    assert folder_data["user_id"] == str(user_id)

    assert "created_at" in folder_data
    assert "updated_at" in folder_data


@pytest.mark.asyncio
async def test_list_favorite_folders_router():
    query_params = FavoriteFolderListQueryParams(
        user_id=SEED_ALICE_ID,
        page=1,
        page_size=10,
        keyword=None,
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            "/grapi/v1/favorite/folders", params=query_params.model_dump(mode="json")
        )

    assert response.status_code == 200
    """
    return {
            "items": items,
            "total": total,
            "page": params.page,
            "page_size": params.page_size,
        }
    """
    res_data = response.json()
    assert res_data["code"] == 0
    assert res_data["msg"] == "success"

    data = res_data["data"]
    assert "total" in data
    assert data["page"] == query_params.page
    assert data["page_size"] == query_params.page_size

    assert isinstance(data["items"], list)

    if data["items"]:
        folder = data["items"][0]
        assert "id" in folder
        assert folder["user_id"] == str(SEED_ALICE_ID)
        assert "name" in folder


@pytest.mark.asyncio
async def test_service_get_favorite_folder_detail():
    user_id = SEED_ALICE_ID
    folder_name = f"detail-router-{uuid.uuid4()}"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        create_resp = await ac.post(
            FOLDER_DEFAULT_URL,
            json={"user_id": str(user_id), "name": folder_name},
        )
        assert create_resp.status_code == 201
        folder_id = create_resp.json()["data"]["id"]

        response = await ac.get(
            f"/grapi/v1/favorite/folders/{folder_id}",
            params={"user_id": str(user_id)},
        )

        res_data = response.json()
        assert res_data["code"] == 0
        assert res_data["msg"] == "success"

        data = res_data["data"]
        assert data["id"] == str(folder_id)
        assert data["name"] == folder_name
        assert len(data["name"]) <= 100
        assert "item_count" in data
        assert data["item_count"] >= 0
        assert "created_at" in data
        assert "updated_at" in data


@pytest.mark.asyncio
async def test_renamerename_favorite_folder_router():
    folder_name = str(uuid.uuid4()) + "-router-test"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        create_resp = await ac.post(
            FOLDER_DEFAULT_URL,
            json={"user_id": str(SEED_ALICE_ID), "name": f"rename-src-{uuid.uuid4()}"},
        )
        assert create_resp.status_code == 201
        folder_id = create_resp.json()["data"]["id"]

        params = FavoriteFolderUpdateInSchema(user_id=SEED_ALICE_ID, name=folder_name)
        response = await ac.patch(
            f"/grapi/v1/favorite/folders/{folder_id}",
            params=params.model_dump(mode="json"),
        )

        res_data = response.json()
        assert res_data["code"] == 0
        assert res_data["msg"] == "success"
        assert res_data["data"]["id"] == str(folder_id)
        assert "created_at" in res_data["data"]
        assert "updated_at" in res_data["data"]


@pytest.mark.asyncio
async def test_delete_favorite_folder_router():
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as ac:
        create_folder_params = FavoriteFolderCreateInSchema(
            user_id=SEED_BOB_ID, name="安心上路"
        )
        create_response = await ac.post(
            FOLDER_DEFAULT_URL, json=create_folder_params.model_dump(mode="json")
        )

        assert create_response.status_code == 201

        folder_id = create_response.json()["data"]["id"]
        user_id = SEED_BOB_ID

        response = await ac.delete(
            FOLDER_DEFAULT_URL + f"/{folder_id}", params={"user_id": str(user_id)}
        )

        res_data = response.json()
        print(res_data)
        assert res_data["code"] == 0
        assert res_data["data"] is None

        # 因为service的单元测试已经完成，就不测功能是否成功，只测接口消息体是否正常

        get_response = await ac.get(
            FOLDER_DEFAULT_URL + f"/{folder_id}",
            params={"user_id": str(user_id)},
        )
        get_data = get_response.json()
        assert get_data["code"] == 404001


@pytest.mark.asyncio
async def test_add_item_to_folder():
    user_id = SEED_ALICE_ID
    intelligence_id = SEED_INTELLIGENCE_ID
    folder_name = f"item-router-{uuid.uuid4()}"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        create_resp = await ac.post(
            FOLDER_DEFAULT_URL,
            json={"user_id": str(user_id), "name": folder_name},
        )
        assert create_resp.status_code == 201
        folder_id = create_resp.json()["data"]["id"]

        response = await ac.post(
            f"{FOLDER_DEFAULT_URL}/{folder_id}/items",
            json={
                "user_id": str(user_id),
                "intelligence_id": str(intelligence_id),
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == 0
    assert body["msg"] == "success"

    data = body["data"]
    assert "id" in data
    assert data["user_id"] == str(user_id)
    assert data["target_id"] == str(intelligence_id)
    assert data["target_type"] == "intelligence"
    assert data["is_deleted"] is False


@pytest.mark.asyncio
# 验收：移除后 GET items 无该条；intelligence 不变。
async def test_remove_item_from_folder():
    user_id = SEED_ALICE_ID
    intelligence_id = SEED_INTELLIGENCE_ID
    folder_name = f"remove-item-router-{uuid.uuid4()}"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        create_resp = await ac.post(
            FOLDER_DEFAULT_URL,
            json={"user_id": str(user_id), "name": folder_name},
        )
        assert create_resp.status_code == 201
        folder_id = create_resp.json()["data"]["id"]

        add_resp = await ac.post(
            f"{FOLDER_DEFAULT_URL}/{folder_id}/items",
            json={
                "user_id": str(user_id),
                "intelligence_id": str(intelligence_id),
            },
        )
        assert add_resp.status_code == 201
        item_id = add_resp.json()["data"]["id"]

        detail_before = await ac.get(
            f"{FOLDER_DEFAULT_URL}/{folder_id}",
            params={"user_id": str(user_id)},
        )
        assert detail_before.json()["code"] == 0
        assert detail_before.json()["data"]["item_count"] == 1

        delete_resp = await ac.delete(
            f"{FOLDER_DEFAULT_URL}/{folder_id}/items/{item_id}",
            params={"user_id": str(user_id)},
        )
        assert delete_resp.status_code == 200
        delete_body = delete_resp.json()
        assert delete_body["code"] == 0
        assert delete_body["msg"] == "success"

        detail_after = await ac.get(
            f"{FOLDER_DEFAULT_URL}/{folder_id}",
            params={"user_id": str(user_id)},
        )
        assert detail_after.json()["code"] == 0
        assert detail_after.json()["data"]["item_count"] == 0

        # GET /items 列表尚未实现，用 item_count + 可重复加入验证 intelligence 未被删除
        re_add_resp = await ac.post(
            f"{FOLDER_DEFAULT_URL}/{folder_id}/items",
            json={
                "user_id": str(user_id),
                "intelligence_id": str(intelligence_id),
            },
        )
        assert re_add_resp.status_code == 201
        assert re_add_resp.json()["code"] == 0
        assert re_add_resp.json()["data"]["target_id"] == str(intelligence_id)


@pytest.mark.asyncio
async def test_move_item_router():

    user_id = SEED_ALICE_ID
    intelligence_id = SEED_INTELLIGENCE_ID

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        src_resp = await ac.post(
            FOLDER_DEFAULT_URL,
            json={"user_id": str(user_id), "name": f"move-src-{uuid.uuid4()}"},
        )
        assert src_resp.status_code == 201
        src_folder_id = src_resp.json()["data"]["id"]

        dst_resp = await ac.post(
            FOLDER_DEFAULT_URL,
            json={"user_id": str(user_id), "name": f"move-dst-{uuid.uuid4()}"},
        )
        assert dst_resp.status_code == 201
        dst_folder_id = dst_resp.json()["data"]["id"]

        add_resp = await ac.post(
            FOLDER_ITEMS_URL.format(folder_id=src_folder_id),
            json={
                "user_id": str(user_id),
                "intelligence_id": str(intelligence_id),
            },
        )
        assert add_resp.status_code == 201
        item_id = add_resp.json()["data"]["id"]

        src_before = await _list_folder_items(ac, src_folder_id, user_id)
        dst_before = await _list_folder_items(ac, dst_folder_id, user_id)
        assert src_before["total"] == 1
        assert str(intelligence_id) in _intel_ids(src_before["items"])
        assert dst_before["total"] == 0
        assert dst_before["items"] == []

        move_resp = await ac.put(
            ITEM_MOVE_URL.format(item_id=item_id),
            json={
                "user_id": str(user_id),
                "target_folder_id": dst_folder_id,
            },
        )
        assert move_resp.status_code == 200
        move_body = move_resp.json()
        assert move_body["code"] == 0
        assert move_body["msg"] == "success"

        data = move_body["data"]
        assert data["id"] != item_id
        assert data["user_id"] == str(user_id)
        assert data["folder_id"] == dst_folder_id
        assert data["target_id"] == str(intelligence_id)
        assert data["target_type"] == "intelligence"
        assert data["is_deleted"] is False

        src_after = await _list_folder_items(ac, src_folder_id, user_id)
        dst_after = await _list_folder_items(ac, dst_folder_id, user_id)
        assert src_after["total"] == 0
        assert src_after["items"] == []
        assert dst_after["total"] == 1
        assert str(intelligence_id) in _intel_ids(dst_after["items"])

        # --- 异常：目标 folder 已有同一情报，移动失败，两边列表不变 ---
        rollback_src_resp = await ac.post(
            FOLDER_DEFAULT_URL,
            json={"user_id": str(user_id), "name": f"move-rollback-src-{uuid.uuid4()}"},
        )
        rollback_dst_resp = await ac.post(
            FOLDER_DEFAULT_URL,
            json={"user_id": str(user_id), "name": f"move-rollback-dst-{uuid.uuid4()}"},
        )
        rb_src_id = rollback_src_resp.json()["data"]["id"]
        rb_dst_id = rollback_dst_resp.json()["data"]["id"]

        rb_add_src = await ac.post(
            FOLDER_ITEMS_URL.format(folder_id=rb_src_id),
            json={
                "user_id": str(user_id),
                "intelligence_id": str(intelligence_id),
            },
        )
        rb_item_id = rb_add_src.json()["data"]["id"]
        await ac.post(
            FOLDER_ITEMS_URL.format(folder_id=rb_dst_id),
            json={
                "user_id": str(user_id),
                "intelligence_id": str(intelligence_id),
            },
        )

        rb_src_before = await _list_folder_items(ac, rb_src_id, user_id)
        rb_dst_before = await _list_folder_items(ac, rb_dst_id, user_id)
        assert rb_src_before["total"] == 1
        assert rb_dst_before["total"] == 1

        fail_resp = await ac.put(
            ITEM_MOVE_URL.format(item_id=rb_item_id),
            json={
                "user_id": str(user_id),
                "target_folder_id": rb_dst_id,
            },
        )
        assert fail_resp.status_code == 200
        fail_body = fail_resp.json()
        assert fail_body["code"] == 409041
        assert fail_body["msg"] == "FAVORITE_ITEM_ALREADY_EXISTS"

        rb_src_after = await _list_folder_items(ac, rb_src_id, user_id)
        rb_dst_after = await _list_folder_items(ac, rb_dst_id, user_id)
        assert rb_src_after["total"] == rb_src_before["total"]
        assert rb_dst_after["total"] == rb_dst_before["total"]
        assert _intel_ids(rb_src_after["items"]) == _intel_ids(rb_src_before["items"])
        assert _intel_ids(rb_dst_after["items"]) == _intel_ids(rb_dst_before["items"])
