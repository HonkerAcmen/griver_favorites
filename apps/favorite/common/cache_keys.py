import uuid

FOLDER_DETAIL_KEY_PREFIX = "folder:detail:"


def folder_detail_key_gen(user_id: uuid.UUID, folder_id: uuid.UUID) -> str:
    return f"{FOLDER_DETAIL_KEY_PREFIX}{user_id}:{folder_id}"
