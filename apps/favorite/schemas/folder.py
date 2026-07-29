from pydantic import BaseModel


class FavoriteFolderCreateInSchema(BaseModel):
    user_id: str
    name: str
