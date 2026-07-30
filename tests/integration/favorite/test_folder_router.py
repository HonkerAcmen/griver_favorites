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
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            FOLDERS_URL,
            params={
                "user_id": str(SEED_ALICE_ID),
                "page": 1,
                "page_size": 10,
                "keyword": "重点",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0

    items = body["data"]["items"]
    names = [item["name"] for item in items]
    assert "重点情报" in names


@pytest.mark.asyncio
async def test_get_folder_detail_with_item_count():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"{FOLDERS_URL}/{SEED_ALICE_FOLDER_ID}",
            params={"user_id": str(SEED_ALICE_ID)},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0

    data = body["data"]
    assert data["id"] == str(SEED_ALICE_FOLDER_ID)
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
