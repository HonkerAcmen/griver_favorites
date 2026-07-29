import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from apps.favorite.schemas.folder import FavoriteFolderListQueryParams
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
