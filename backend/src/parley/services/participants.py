"""Participant operations: invite (done in rooms.create_room), accept, list."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from parley.models import Participant


async def get(
    db: AsyncSession, room_id: UUID, agent_pubkey: bytes
) -> Participant | None:
    return (
        await db.execute(
            select(Participant).where(
                Participant.room_id == room_id, Participant.agent_pubkey == agent_pubkey
            )
        )
    ).scalar_one_or_none()


async def list_for_room(db: AsyncSession, room_id: UUID) -> list[Participant]:
    rows = (
        await db.execute(
            select(Participant)
            .where(Participant.room_id == room_id)
            .order_by(Participant.invited_at)
        )
    ).scalars().all()
    return list(rows)


async def accept(
    db: AsyncSession, *, participant: Participant, sig: bytes
) -> Participant:
    participant.accepted_at = datetime.now(UTC)
    participant.accept_sig = sig
    await db.flush()
    return participant


def is_accepted(p: Participant) -> bool:
    return p.accepted_at is not None
