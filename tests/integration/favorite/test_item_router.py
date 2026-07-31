"""Item Router 集成测试：AsyncClient + 真实 DB + seed。"""

import asyncio
import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from main import app

SEED_ALICE_ID = uuid.UUID("fa500001-0001-4000-8000-000000000001")
SEED_INTELLIGENCE_ID = uuid.UUID("fa700001-0001-4000-8000-000000000001")
SEED_INTELLIGENCE_DELETED_ID = uuid.UUID("fa700001-0001-4000-8000-000000000099")

FOLDERS_URL = "/grapi/v1/favorite/folders"
ITEMS_URL = FOLDERS_URL + "/{folder_id}/items"
ITEM_MOVE_URL = "/grapi/v1/favorite/items/{item_id}/move"


async def _create_folder(client: AsyncClient, name: str | None = None) -> str:
    folder_name = name or f"item-integration-{uuid.uuid4()}"
    response = await client.post(
        FOLDERS_URL,
        json={"user_id": str(SEED_ALICE_ID), "name": folder_name},
    )
    assert response.status_code == 201
    assert response.json()["code"] == 0
    return response.json()["data"]["id"]


async def _add_item(
    client: AsyncClient,
    folder_id: str,
    intelligence_id: uuid.UUID = SEED_INTELLIGENCE_ID,
) -> dict:
    response = await client.post(
        ITEMS_URL.format(folder_id=folder_id),
        json={
            "user_id": str(SEED_ALICE_ID),
            "intelligence_id": str(intelligence_id),
        },
    )
    return response


async def _list_items(
    client: AsyncClient, folder_id: str, keyword: str | None = None
) -> dict:
    params: dict = {"user_id": str(SEED_ALICE_ID), "page": 1, "page_size": 10}
    if keyword is not None:
        params["keyword"] = keyword
    response = await client.get(
        ITEMS_URL.format(folder_id=folder_id),
        params=params,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    return body["data"]


@pytest.mark.asyncio
async def test_add_item_success():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        folder_id = await _create_folder(client)
        response = await _add_item(client, folder_id)

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == 0
    assert body["msg"] == "success"

    data = body["data"]
    assert data["user_id"] == str(SEED_ALICE_ID)
    assert data["target_id"] == str(SEED_INTELLIGENCE_ID)
    assert data["target_type"] == "intelligence"
    assert data["is_deleted"] is False


@pytest.mark.asyncio
async def test_add_item_duplicate_in_same_folder():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        folder_id = await _create_folder(client)
        first = await _add_item(client, folder_id)
        assert first.status_code == 201

        second = await _add_item(client, folder_id)

    assert second.status_code == 200
    body = second.json()
    assert body["code"] == 409041
    assert body["msg"] == "FAVORITE_ITEM_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_add_item_same_intelligence_in_different_folders():
    """F9：同一情报可存在于多个 folder。"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        folder_a = await _create_folder(client, f"cross-a-{uuid.uuid4()}")
        folder_b = await _create_folder(client, f"cross-b-{uuid.uuid4()}")

        resp_a = await _add_item(client, folder_a)
        resp_b = await _add_item(client, folder_b)

    assert resp_a.status_code == 201
    assert resp_b.status_code == 201
    assert resp_a.json()["data"]["id"] != resp_b.json()["data"]["id"]
    assert (
        resp_a.json()["data"]["target_id"]
        == resp_b.json()["data"]["target_id"]
        == str(SEED_INTELLIGENCE_ID)
    )


@pytest.mark.asyncio
async def test_add_item_intelligence_deleted():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        folder_id = await _create_folder(client)
        response = await _add_item(client, folder_id, SEED_INTELLIGENCE_DELETED_ID)

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 404042
    assert body["msg"] == "INTELLIGENCE_NOT_EXISTS"


@pytest.mark.asyncio
async def test_add_item_folder_deleted():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        folder_id = await _create_folder(client)
        delete_resp = await client.delete(
            f"{FOLDERS_URL}/{folder_id}",
            params={"user_id": str(SEED_ALICE_ID)},
        )
        assert delete_resp.status_code == 200
        assert delete_resp.json()["code"] == 0

        response = await _add_item(client, folder_id)

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 404001
    assert body["msg"] == "FAVORITE_FOLDER_NOT_EXISTS"


@pytest.mark.asyncio
async def test_move_item_success():
    """R7：移动后来源列表无、目标列表有。"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        src_id = await _create_folder(client, f"move-src-{uuid.uuid4()}")
        dst_id = await _create_folder(client, f"move-dst-{uuid.uuid4()}")

        add_resp = await _add_item(client, src_id)
        assert add_resp.status_code == 201
        item_id = add_resp.json()["data"]["id"]

        src_before = await _list_items(client, src_id)
        dst_before = await _list_items(client, dst_id)
        assert src_before["total"] == 1
        assert dst_before["total"] == 0

        move_resp = await client.put(
            ITEM_MOVE_URL.format(item_id=item_id),
            json={
                "user_id": str(SEED_ALICE_ID),
                "target_folder_id": dst_id,
            },
        )
        assert move_resp.status_code == 200
        move_body = move_resp.json()
        assert move_body["code"] == 0
        assert move_body["data"]["folder_id"] == dst_id

        src_after = await _list_items(client, src_id)
        dst_after = await _list_items(client, dst_id)
        assert src_after["total"] == 0
        assert src_after["items"] == []
        assert dst_after["total"] == 1
        assert dst_after["items"][0]["intelligence_id"] == str(SEED_INTELLIGENCE_ID)


@pytest.mark.asyncio
async def test_list_items_keyword_hit_and_miss():
    """keyword 对 intelligence.title ILIKE；命中/未命中。"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        folder_id = await _create_folder(client)
        add_resp = await _add_item(client, folder_id)
        assert add_resp.status_code == 201

        hit = await _list_items(client, folder_id, keyword="alice-01")
        assert hit["total"] >= 1
        titles = [item["title"] for item in hit["items"]]
        assert any("alice-01" in title for title in titles)

        miss = await _list_items(client, folder_id, keyword="NO_SUCH_TITLE_XYZ")
        assert miss["total"] == 0
        assert miss["items"] == []


# ----- 并发测试 添加item Start ------
async def _add_once_item(
    client: AsyncClient,
    folder_id: str,
    user_id: uuid.UUID,
    intelligence_id: uuid.UUID,
):

    return await client.post(
        ITEMS_URL.format(folder_id=folder_id),
        json={
            "user_id": str(user_id),
            "intelligence_id": str(intelligence_id),
        },
    )


@pytest.mark.asyncio
async def test_concurrent_add_same_intelligence_same_folder():

    N = 20
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        folder_id = await _create_folder(client)
        task = [
            _add_once_item(
                client,
                folder_id=folder_id,
                user_id=SEED_ALICE_ID,
                intelligence_id=SEED_INTELLIGENCE_ID,
            )
            for _ in range(N)
        ]

        responses = await asyncio.gather(*task)

        success = [
            r for r in responses if r.status_code == 201 and r.json()["code"] == 0
        ]

        duplicates = [
            r
            for r in responses
            if r.json().get("msg") == "FAVORITE_ITEM_ALREADY_EXISTS"
        ]

        assert len(success) == 1
        assert len(duplicates) == N - 1

        listed = await _list_items(client, folder_id)
        assert listed["total"] == 1


# # ----- 并发测试 添加item End ------
