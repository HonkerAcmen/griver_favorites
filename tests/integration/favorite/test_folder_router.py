"""Folder Router 集成测试：AsyncClient + 真实 DB + seed alice。"""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from main import app

SEED_ALICE_ID = uuid.UUID("fa500001-0001-4000-8000-000000000001")
SEED_ALICE_FOLDER_ID = uuid.UUID("fa500001-0001-4000-8000-000000000101")

FOLDERS_URL = "/grapi/v1/favorite/folders"


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
