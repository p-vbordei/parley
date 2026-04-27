"""In-memory replay-detection for create_room signed payloads.

SPEC §10.1 (since v0.3.0). Rejects a second occurrence of the same
canonical-bytes-of-signed-payload within the 60s freshness window.
Closes the v0.2.0 residual where capture-and-immediately-replay produced
duplicate rooms.

Single-process: a multi-worker uvicorn deployment would need a shared
backing store (Redis / Postgres). v0.3 punts on that — single-worker is
the documented production shape; see SPEC §10.2.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta

WINDOW = timedelta(seconds=60)

_store: dict[str, datetime] = {}
_lock = asyncio.Lock()


async def check_and_mark(canonical_bytes: bytes) -> bool:
    """Return True if these bytes are new in the window (i.e. accept the request).

    Return False if we've already seen them — caller should reject as replay.
    Garbage-collects expired entries on each call.
    """
    now = datetime.now(UTC)
    h = hashlib.sha256(canonical_bytes).hexdigest()
    async with _lock:
        for k in [k for k, exp in _store.items() if exp < now]:
            del _store[k]
        if h in _store:
            return False
        _store[h] = now + WINDOW
        return True


def reset() -> None:
    """Test helper — clears the dedup store."""
    _store.clear()
