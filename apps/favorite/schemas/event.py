import datetime
import uuid
from typing import Literal

from pydantic import BaseModel


class FavoriteAddedEvent(BaseModel):
    event_id: uuid.UUID
    user_id: uuid.UUID
    folder_id: uuid.UUID
    intelligence_id: uuid.UUID
    action: Literal["favorite_add"] = "favorite_add"
    occurred_at: datetime.datetime
