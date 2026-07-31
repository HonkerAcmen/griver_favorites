from redis.asyncio import ConnectionPool, Redis

from apps.core.config import settings


class RedisService:
    def __init__(self):
        self.write_pool: ConnectionPool | None = None
        self.read_pool: ConnectionPool | None = None
        self._write_client: Redis | None = None
        self._read_client: Redis | None = None

    async def init_redis(self):
        self.write_pool = ConnectionPool.from_url(
            settings.redis_write_url, decode_responses=True, max_connections=20
        )
        self.read_pool = ConnectionPool.from_url(
            settings.redis_read_url, decode_responses=True, max_connections=50
        )

        self._write_client = Redis(connection_pool=self.write_pool)
        self._read_client = Redis(connection_pool=self.read_pool)

    async def close(self):
        if self._write_client:
            await self._write_client.aclose()
        if self._read_client:
            await self._read_client.aclose()

        if self.write_pool:
            await self.write_pool.disconnect()
        if self.read_pool:
            await self.read_pool.disconnect()

    @property
    def write_client(self) -> Redis:
        if not self._write_client:
            raise RuntimeError("Redis Client (write) is not initialized")
        return self._write_client

    @property
    def read_client(self) -> Redis:
        if not self._read_client:
            raise RuntimeError("Redis Client (Read) is not initialized")
        return self._read_client


redis_service = RedisService()


async def get_redis_write() -> Redis | None:
    try:
        return redis_service.write_client
    except RuntimeError:
        return None


async def get_redis_read() -> Redis | None:
    try:
        return redis_service.read_client
    except RuntimeError:
        return None
