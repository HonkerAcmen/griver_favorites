from sqlalchemy.orm import Session


class FolderService:
        def __init__(self, session:Session):
                self.session = session
