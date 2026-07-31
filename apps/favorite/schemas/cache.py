"""收藏夹详情 Redis 缓存值 DTO：与 GET /folders/{id} 响应字段对齐，禁止直接缓存 ORM。"""

import datetime
import json
import uuid

from pydantic import BaseModel, ConfigDict

# 空值缓存标记键：folder 不存在时写入 {"__null__": true}，短 TTL 防穿透
NULL_SENTINEL_KEY = "__null__"


class FolderDetailCacheDTO(BaseModel):
    """收藏夹详情 + item_count，用于 Redis Cache-Aside 序列化。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    item_count: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    def to_json(self) -> str:
        """将 DTO 序列化为 JSON 字符串，供 redis.set / setex 写入。"""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, raw: str) -> "FolderDetailCacheDTO | None":
        """从 Redis 读出的 JSON 反序列化为 DTO。

        - 正常详情：返回 FolderDetailCacheDTO
        - 空值 sentinel（__null__）：返回 None，表示「已知 folder 不存在」
        """
        data = json.loads(raw)

        if data.get(NULL_SENTINEL_KEY) is True:
            return None

        return cls.model_validate(data)

    @classmethod
    def null_sentinel_json(cls) -> str:
        """生成空值缓存 JSON：folder 不存在时写入，TTL 60s，避免反复打 DB。"""
        return json.dumps({NULL_SENTINEL_KEY: True})

    @classmethod
    def from_service_dict(cls, d: dict) -> "FolderDetailCacheDTO":
        """从 FolderService.get_favorite_folder_detail 的 dict 构建 DTO，用于回写缓存。"""
        return cls(
            id=d["id"],
            name=d["name"],
            item_count=d["item_count"],
            created_at=d["created_at"],
            updated_at=d["updated_at"],
        )
