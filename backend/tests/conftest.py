from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, text
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
    """Per-test session that rolls back so model tests stay isolated."""
    async with engine.connect() as conn:
        trans = await conn.begin()
        Session = async_sessionmaker(bind=conn, expire_on_commit=False)
        async with Session() as s:
            yield s
        if trans.is_active:
            await trans.rollback()


@pytest_asyncio.fixture
async def clean_db(engine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE messages, participants, rooms RESTART IDENTITY"))


@pytest_asyncio.fixture
async def client(engine, clean_db) -> AsyncIterator[AsyncClient]:
    """ASGI test client.

    Each test gets a fresh per-loop engine; we override the FastAPI `get_db`
    dependency so the app uses that engine instead of the module-level one
    (which would be bound to whichever event loop happened to import db.py).
    """
    from agentrooms.api.deps import get_db
    from agentrooms.api.main import app

    TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override():
        async with TestSession() as s:
            yield s

    app.dependency_overrides[get_db] = _override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)
