"""单元测试 DB fixture：Connection 外层事务回滚，Service commit 也不污染真实库。"""

import pytest_asyncio

from apps.core.database import SessionLocal, engine


@pytest_asyncio.fixture
async def session():
    async with engine.connect() as conn:
        trans = await conn.begin()
        async with SessionLocal(
            bind=conn, join_transaction_mode="create_savepoint"
        ) as s:
            yield s
        await trans.rollback()
