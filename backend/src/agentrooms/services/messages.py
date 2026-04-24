"""Message posting + retrieval. Turn-ownership and signature verification
are enforced by callers (router layer)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentrooms.models import Message, Participant, Room

CLOCK_SKEW = timedelta(seconds=60)
MAX_BODY_BYTES = 16 * 1024


def is_timestamp_fresh(ts: datetime, *, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    return abs((ts - now).total_seconds()) <= CLOCK_SKEW.total_seconds()


def next_turn_owner(participants: list[Participant], current: bytes | None) -> bytes | None:
    """Round-robin over accepted participants, ordered by invited_at.

    If current isn't in the list (or list is empty), pick the first accepted one.
    """
    accepted = sorted(
        (p for p in participants if p.accepted_at is not None), key=lambda p: p.invited_at
    )
    pks = [p.agent_pubkey for p in accepted]
    if not pks:
        return None
    if current not in pks:
        return pks[0]
    idx = pks.index(current)
    return pks[(idx + 1) % len(pks)]


async def post_message(
    db: AsyncSession,
    *,
    room: Room,
    participants: list[Participant],
    author_pubkey: bytes,
    turn_n: int,
    body: str,
    sig: bytes,
    created_at: datetime,
) -> Message:
    """Insert message, advance room turn, rotate turn_owner. Auto-closes at max_turns.

    Caller must have already verified: room is open, author is accepted participant,
    author == current turn_owner, turn_n == room.turn_n + 1, body size, sig, freshness.
    """
    msg = Message(
        room_id=room.id,
        author_pubkey=author_pubkey,
        turn_n=turn_n,
        body=body,
        sig=sig,
        created_at=created_at,
    )
    db.add(msg)
    room.turn_n = turn_n
    if room.turn_n >= room.max_turns:
        room.status = "closed"
        room.closed_at = datetime.now(UTC)
        room.turn_owner_pubkey = None
    else:
        room.turn_owner_pubkey = next_turn_owner(participants, author_pubkey)
    await db.flush()
    return msg


async def list_since(db: AsyncSession, *, room_id: UUID, since: int) -> list[Message]:
    rows = (
        await db.execute(
            select(Message)
            .where(Message.room_id == room_id, Message.turn_n > since)
            .order_by(Message.turn_n)
        )
    ).scalars().all()
    return list(rows)
