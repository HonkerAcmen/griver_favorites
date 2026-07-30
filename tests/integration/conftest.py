"""集成测试公共 fixture：每用例结束后释放 DB 连接池，避免 event loop 冲突。"""

import pytest_asyncio

from apps.core.database import engine


@pytest_asyncio.fixture(autouse=True)
async def dispose_db_engine_after_test():
    yield
    await engine.dispose()
