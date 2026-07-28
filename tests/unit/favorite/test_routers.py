# import datetime
# import uuid
# from unittest.mock import MagicMock
#
# from starlette.testclient import TestClient
# from main import app
#
# client = TestClient(app)
#
# def test_create_folder():
#         mock_service = MagicMock()
#         folder_id = uuid.UUID
#         user_id = uuid.UUID
#
#         mock_service.create_folder.return_value = {
#                 "id": folder_id,
#                 "user_id": user_id,
#                 "name": "好运来",
#                 "is_deleted": "false",
#                 "created_at": datetime.datetime.now(),
#                 "update_at": datetime.datetime.now()
#         }
#
#         app.dependency_overrides[get_folder_service] = lambda: mock_service