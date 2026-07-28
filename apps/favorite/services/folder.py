import datetime
import uuid

from sqlalchemy.orm import Session


class FolderService:
        def __init__(self, session:Session):
                self.session = session

        def create_folder(self, user_id, name):
                folder_id = uuid.uuid4()

                return {
                        "folder_id": folder_id,
                        "name": "好运来",
                        "created_at": datetime.datetime.now()
                }
