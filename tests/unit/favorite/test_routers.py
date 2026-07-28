import datetime
import uuid
from unittest.mock import MagicMock

from starlette.testclient import TestClient

from apps.favorite.dependencies import get_folder_service
from main import app

client = TestClient(app)

def test_create_folder():
        mock_service = MagicMock()
        folder_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_service.create_folder.return_value = {
                "folder_id": str(folder_id),
                "name": "好运来",
                "created_at": datetime.datetime.now(datetime.UTC)
        }

        app.dependency_overrides[get_folder_service] = lambda: mock_service

        response = client.post("/grapi/v1/favorite/folders", json={
                "user_id": str(user_id),
                "name": "好运来",
        })

        assert response.status_code == 201
        assert response.json() == {
                "code": 1,
                "msg": "create successful",
                "data": {
                        "folder_id": folder_id,
                        "name": "好运来",
                        "created_at": datetime.datetime.now()
                }
        }

        app.dependency_overrides.clear()