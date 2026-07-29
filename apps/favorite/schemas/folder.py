import uuid

from pydantic import BaseModel


class FavoriteFolderCreateInSchema(BaseModel):
    user_id: uuid.UUID
    name: str
