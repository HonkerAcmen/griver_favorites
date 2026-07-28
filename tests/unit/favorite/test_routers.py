import datetime
import uuid
from unittest.mock import MagicMock

from starlette.testclient import TestClient

from apps.favorite.dependencies import get_folder_service
from main import app

client = TestClient(app)

def test_create_folder():
        mock_service = MagicMock()
        folder_id = "bc047d8d-05f4-4712-90b6-b5010d534ca7"
        user_id = "bc047d8d-05f4-4712-90b6-b5010d534cab"
        created_at = datetime.datetime(2026, 7, 28, 12, 0, 0, tzinfo=datetime.UTC)

        mock_service.create_folder.return_value = {
                "folder_id": folder_id,
                "name": "好运来",
                "created_at": created_at.isoformat()
        }

        app.dependency_overrides[get_folder_service] = lambda: mock_service

        response = client.post("/grapi/v1/favorite/folders", json={
                "user_id": user_id,
                "name": "好运来",
        })

        assert response.status_code == 201
        assert response.json() == {
                "code": 0,
                "msg": "create successful",
                "data": {
                        "folder_id": folder_id,
                        "name": "好运来",
                        "created_at": created_at.isoformat()
                }
        }

        app.dependency_overrides.clear()