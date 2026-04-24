from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agentrooms.config import settings
from agentrooms.models import Base


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(settings.database_url)
    async with eng.connect() as conn:
        names = await conn.run_sync(lambda c: inspect(c).get_table_names())
    missing = {t.name for t in Base.metadata.sorted_tables} - set(names)
    if missing:
        await eng.dispose()
        raise RuntimeError(
            f"Missing tables {missing}; run `alembic upgrade head` against {settings.database_url}"
        )
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncIterator[AsyncSession]:
    """Per-test session that rolls back so tests are isolated and the DB stays clean."""
    async with engine.connect() as conn:
        trans = await conn.begin()
        Session = async_sessionmaker(bind=conn, expire_on_commit=False)
        async with Session() as s:
            yield s
        if trans.is_active:
            await trans.rollback()
