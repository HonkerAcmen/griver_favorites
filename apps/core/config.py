"""应用配置：从 .env / 环境变量加载，供 database、redis、mq 等模块使用。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # PostgreSQL（应用异步 + Alembic 同步）
    database_url: str
    database_url_sync: str

    # Redis Cache-Aside（读/写可同 URL）
    redis_read_url: str = "redis://localhost:6379/0"
    redis_write_url: str = "redis://localhost:6379/0"

    # RabbitMQ 收藏事件
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    favorite_event_exchange: str = "favorite.events"
    favorite_event_routing_key: str = "favorite.item.added"
    favorite_operation_log_queue: str = "favorite.operation_log"
    favorite_operation_log_dlq: str = "favorite.operation_log.dlq"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
