from fastapi import Depends
from sqlalchemy.orm import Session

from apps.core.database import get_db_session
from apps.favorite.services.folder import FolderService


def get_folder_service(session:Session = Depends(get_db_session())):
        return FolderService(session)