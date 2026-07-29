import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from main import app

SEED_ALICE_ID = uuid.UUID("fa500001-0001-4000-8000-000000000001")


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
