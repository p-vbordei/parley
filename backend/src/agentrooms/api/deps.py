from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Header
from sqlalchemy.ext.asyncio import AsyncSession

from agentrooms.db import SessionLocal
from agentrooms.errors import invalid_pubkey


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def get_agent_pubkey(x_agent_pubkey: Annotated[str, Header()]) -> bytes:
    try:
        pk = bytes.fromhex(x_agent_pubkey)
    except ValueError as e:
        raise invalid_pubkey() from e
    if len(pk) != 32:
        raise invalid_pubkey()
    return pk


DbDep = Annotated[AsyncSession, ...]
PubkeyDep = Annotated[bytes, ...]
