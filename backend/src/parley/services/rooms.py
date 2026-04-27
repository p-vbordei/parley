"""Room lifecycle: create, fetch, close. No HTTP concerns here."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from parley.models import Participant, Room


async def create_room(
    db: AsyncSession,
    *,
    creator_pubkey: bytes,
    topic: str,
    invite_pubkeys: list[bytes],
    max_turns: int,
    ttl_hours: int,
) -> Room:
    """Insert room + creator (auto-accepted) + invitees (pending).

    Creator goes first (turn_owner_pubkey == creator).
    Caller is responsible for committing.
    """
    now = datetime.now(UTC)
    room = Room(
        topic=topic,
        creator_pubkey=creator_pubkey,
        turn_owner_pubkey=creator_pubkey,
        max_turns=max_turns,
        ttl_until=now + timedelta(hours=ttl_hours),
    )
    db.add(room)
    await db.flush()

    db.add(
        Participant(
            room_id=room.id,
            agent_pubkey=creator_pubkey,
            owner_pubkey=creator_pubkey,
            invited_by_pubkey=creator_pubkey,
            accepted_at=now,
        )
    )
    seen: set[bytes] = {creator_pubkey}  # creator already added; SPEC §6.1: dedup silently
    for pk in invite_pubkeys:
        if pk in seen:
            continue
        seen.add(pk)
        db.add(
            Participant(
                room_id=room.id,
                agent_pubkey=pk,
                owner_pubkey=pk,
                invited_by_pubkey=creator_pubkey,
            )
        )
    await db.flush()
    return room


async def get_room(db: AsyncSession, room_id: UUID) -> Room | None:
    return (await db.execute(select(Room).where(Room.id == room_id))).scalar_one_or_none()


async def list_rooms_for_agent(db: AsyncSession, agent_pubkey: bytes) -> list[Room]:
    from parley.models import Participant

    rows = (
        await db.execute(
            select(Room)
            .join(Participant, Participant.room_id == Room.id)
            .where(Participant.agent_pubkey == agent_pubkey)
            .order_by(Room.created_at.desc())
        )
    ).scalars().all()
    return list(rows)


async def get_room_with_participants(
    db: AsyncSession, room_id: UUID
) -> tuple[Room, list[Participant]] | None:
    room = await get_room(db, room_id)
    if room is None:
        return None
    rows = (
        await db.execute(
            select(Participant)
            .where(Participant.room_id == room_id)
            .order_by(Participant.invited_at)
        )
    ).scalars().all()
    return room, list(rows)


async def close_room(
    db: AsyncSession, *, room: Room, by_pubkey: bytes, summary: str | None
) -> Room:
    room.status = "closed"
    room.closed_at = datetime.now(UTC)
    room.closed_by_pubkey = by_pubkey
    if summary is not None:
        room.summary = summary
    await db.flush()
    return room


async def is_expired(room: Room) -> bool:
    return datetime.now(UTC) >= room.ttl_until


__all__ = [
    "create_room",
    "get_room",
    "get_room_with_participants",
    "close_room",
    "is_expired",
    "selectinload",  # re-exported in case routers want eager-load helpers
]
