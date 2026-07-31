import uuid

from pydantic import BaseModel


class FavoriteItemCreateInSchema(BaseModel):
    user_id: uuid.UUID
    intelligence_id: uuid.UUID


class FavoriteItemMoveInSchema(BaseModel):
    user_id: uuid.UUID
    target_folder_id: uuid.UUID
