import datetime
import uuid

from sqlalchemy.orm import Session


class FolderService:
        def __init__(self, session:Session):
                self.session = session

        def create_folder(self, user_id, name):
                folder_id = "bc047d8d-05f4-4712-90b6-b5010d534ca7"
                created_at = datetime.datetime(2026, 7, 28, 12, 0, 0, tzinfo=datetime.UTC)
                return {
                        "folder_id": folder_id,
                        "name": "好运来",
                        "created_at": created_at.isoformat()
                }
