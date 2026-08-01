"""Folder Router 集成测试：AsyncClient + 真实 DB + seed alice。"""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from main import app

SEED_ALICE_ID = uuid.UUID("fa500001-0001-4000-8000-000000000001")
SEED_ALICE_FOLDER_ID = uuid.UUID("fa500001-0001-4000-8000-000000000101")
SEED_INTELLIGENCE_ID = uuid.UUID("fa700001-0001-4000-8000-000000000001")

FOLDERS_URL = "/grapi/v1/favorite/folders"


async def _create_folder(
    client: AsyncClient, name: str | None = None
) -> tuple[str, str]:
    folder_name = name or f"integration-{uuid.uuid4()}"
    response = await client.post(
        FOLDERS_URL,
        json={"user_id": str(SEED_ALICE_ID), "name": folder_name},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["code"] == 0
    return body["data"]["id"], folder_name


@pytest.mark.asyncio
async def test_create_folder_success():
    folder_name = f"integration-{uuid.uuid4()}"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            FOLDERS_URL,
            json={"user_id": str(SEED_ALICE_ID), "name": folder_name},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == 0
    assert body["msg"] == "success"

    data = body["data"]
    assert "id" in data
    assert data["name"] == folder_name
    assert data["user_id"] == str(SEED_ALICE_ID)


@pytest.mark.asyncio
async def test_list_folders_with_keyword():
    keyword = f"重点-{uuid.uuid4().hex[:8]}"
    folder_name = f"集成{keyword}测试"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_resp = await client.post(
            FOLDERS_URL,
            json={"user_id": str(SEED_ALICE_ID), "name": folder_name},
        )
        assert create_resp.status_code == 201

        response = await client.get(
            FOLDERS_URL,
            params={
                "user_id": str(SEED_ALICE_ID),
                "page": 1,
                "page_size": 10,
                "keyword": keyword,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0

    names = [item["name"] for item in body["data"]["items"]]
    assert folder_name in names


@pytest.mark.asyncio
async def test_get_folder_detail_with_item_count():
    folder_name = f"detail-{uuid.uuid4()}"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_resp = await client.post(
            FOLDERS_URL,
            json={"user_id": str(SEED_ALICE_ID), "name": folder_name},
        )
        assert create_resp.status_code == 201
        folder_id = create_resp.json()["data"]["id"]

        response = await client.get(
            f"{FOLDERS_URL}/{folder_id}",
            params={"user_id": str(SEED_ALICE_ID)},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0

    data = body["data"]
    assert data["id"] == str(folder_id)
    assert data["name"] == folder_name
    assert "item_count" in data
    assert data["item_count"] >= 0


@pytest.mark.asyncio
async def test_create_duplicate_folder_name():
    folder_name = f"dup-{uuid.uuid4()}"
    payload = {"user_id": str(SEED_ALICE_ID), "name": folder_name}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        first = await client.post(FOLDERS_URL, json=payload)
        assert first.status_code == 201
        assert first.json()["code"] == 0

        second = await client.post(FOLDERS_URL, json=payload)

    body = second.json()
    assert body["code"] != 0
    assert "DUPLICATE" in body["msg"]


@pytest.mark.asyncio
async def test_get_folder_detail_not_found():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"{FOLDERS_URL}/{uuid.uuid4()}",
            params={"user_id": str(SEED_ALICE_ID)},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 404001
    assert body["msg"] == "FAVORITE_FOLDER_NOT_EXISTS"


@pytest.mark.asyncio
async def test_get_folder_detail_invalid_uuid_returns_422():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"{FOLDERS_URL}/not-a-valid-uuid",
            params={"user_id": str(SEED_ALICE_ID)},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_rename_folder_accepts_json_body():
    """测试是否为boyd传参"""
    new_name = f"body-rename-{uuid.uuid4()}"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        folder_id, _ = await _create_folder(client)

        query_only = await client.patch(
            f"{FOLDERS_URL}/{folder_id}",
            params={"user_id": str(SEED_ALICE_ID), "name": new_name},
        )
        assert query_only.status_code == 422

        response = await client.patch(
            f"{FOLDERS_URL}/{folder_id}",
            json={"user_id": str(SEED_ALICE_ID), "name": new_name},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["name"] == new_name


@pytest.mark.asyncio
async def test_patch_rename_folder_success():
    new_name = f"renamed-{uuid.uuid4()}"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        folder_id, _ = await _create_folder(client)
        response = await client.patch(
            f"{FOLDERS_URL}/{folder_id}",
            json={"user_id": str(SEED_ALICE_ID), "name": new_name},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["msg"] == "success"
    assert body["data"]["id"] == str(folder_id)
    assert body["data"]["name"] == new_name


@pytest.mark.asyncio
async def test_patch_rename_folder_duplicate_name():
    shared_name = f"dup-rename-{uuid.uuid4()}"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _create_folder(client, name=shared_name)
        folder_id, _ = await _create_folder(client)

        response = await client.patch(
            f"{FOLDERS_URL}/{folder_id}",
            json={"user_id": str(SEED_ALICE_ID), "name": shared_name},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] != 0
    assert "DUPLICATE" in body["msg"]


@pytest.mark.asyncio
async def test_delete_folder_then_detail_not_found():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        folder_id, _ = await _create_folder(client)

        delete_resp = await client.delete(
            f"{FOLDERS_URL}/{folder_id}",
            params={"user_id": str(SEED_ALICE_ID)},
        )
        assert delete_resp.status_code == 200
        assert delete_resp.json()["code"] == 0

        detail_resp = await client.get(
            f"{FOLDERS_URL}/{folder_id}",
            params={"user_id": str(SEED_ALICE_ID)},
        )

    body = detail_resp.json()
    assert body["code"] == 404001
    assert body["msg"] == "FAVORITE_FOLDER_NOT_EXISTS"


@pytest.mark.asyncio
async def test_removed_item_not_visible_in_folder_detail():
    """软删 item 后 item_count 归零；GET /items 未实现时用详情 item_count 验收。"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        folder_id, _ = await _create_folder(client)

        add_resp = await client.post(
            f"{FOLDERS_URL}/{folder_id}/items",
            json={
                "user_id": str(SEED_ALICE_ID),
                "intelligence_id": str(SEED_INTELLIGENCE_ID),
            },
        )
        assert add_resp.status_code == 201
        item_id = add_resp.json()["data"]["id"]

        detail_before = await client.get(
            f"{FOLDERS_URL}/{folder_id}",
            params={"user_id": str(SEED_ALICE_ID)},
        )
        assert detail_before.json()["data"]["item_count"] == 1

        remove_resp = await client.delete(
            f"{FOLDERS_URL}/{folder_id}/items/{item_id}",
            params={"user_id": str(SEED_ALICE_ID)},
        )
        assert remove_resp.status_code == 200
        assert remove_resp.json()["code"] == 0

        detail_after = await client.get(
            f"{FOLDERS_URL}/{folder_id}",
            params={"user_id": str(SEED_ALICE_ID)},
        )

    assert detail_after.json()["data"]["item_count"] == 0
