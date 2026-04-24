"""Rooms HTTP layer. Pure plumbing — business logic lives in services/."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agentrooms import errors
from agentrooms.api.deps import get_agent_pubkey, get_db
from agentrooms.api.schemas.rooms import (
    AcceptRequest,
    AcceptResponse,
    CloseRequest,
    CloseResponse,
    ParticipantOut,
    RoomCreateRequest,
    RoomOut,
    RoomSummary,
)
from agentrooms.crypto import canonical_json, verify
from agentrooms.services import participants as participants_svc
from agentrooms.services import rooms as rooms_svc

router = APIRouter(prefix="/v1/rooms", tags=["rooms"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
PubkeyDep = Annotated[bytes, Depends(get_agent_pubkey)]


def _hex(b: bytes | None) -> str | None:
    return b.hex() if b is not None else None


def _to_room_out(room, parts) -> RoomOut:
    return RoomOut(
        room_id=room.id,
        topic=room.topic,
        creator_pubkey=room.creator_pubkey.hex(),
        status=room.status,
        turn_n=room.turn_n,
        turn_owner_pubkey=_hex(room.turn_owner_pubkey),
        max_turns=room.max_turns,
        ttl_until=room.ttl_until,
        created_at=room.created_at,
        closed_at=room.closed_at,
        summary=room.summary,
        participants=[
            ParticipantOut(
                agent_pubkey=p.agent_pubkey.hex(),
                invited_by_pubkey=p.invited_by_pubkey.hex(),
                invited_at=p.invited_at,
                accepted_at=p.accepted_at,
            )
            for p in parts
        ],
    )


def _parse_pubkey_hex(s: str) -> bytes:
    try:
        b = bytes.fromhex(s)
    except ValueError as e:
        raise errors.invalid_pubkey() from e
    if len(b) != 32:
        raise errors.invalid_pubkey()
    return b


def _parse_sig_hex(s: str) -> bytes:
    try:
        sig = bytes.fromhex(s)
    except ValueError as e:
        raise errors.bad_signature() from e
    if len(sig) != 64:
        raise errors.bad_signature()
    return sig


@router.post("", response_model=RoomOut)
async def create_room(
    payload: RoomCreateRequest, db: DbDep, agent_pubkey: PubkeyDep
) -> RoomOut:
    invitees = [_parse_pubkey_hex(p) for p in payload.invite_pubkeys]
    sig = _parse_sig_hex(payload.sig)

    signed = canonical_json(
        {
            "topic": payload.topic,
            "invite_pubkeys": payload.invite_pubkeys,
            "max_turns": payload.max_turns,
            "ttl_hours": payload.ttl_hours,
        }
    )
    if not verify(agent_pubkey, signed, sig):
        raise errors.bad_signature()

    room = await rooms_svc.create_room(
        db,
        creator_pubkey=agent_pubkey,
        topic=payload.topic,
        invite_pubkeys=invitees,
        max_turns=payload.max_turns,
        ttl_hours=payload.ttl_hours,
    )
    parts = await participants_svc.list_for_room(db, room.id)
    await db.commit()
    return _to_room_out(room, parts)


@router.get("", response_model=list[RoomSummary])
async def list_rooms(db: DbDep, agent_pubkey: PubkeyDep) -> list[RoomSummary]:
    """Mine-only: rooms where the caller is a participant."""
    rows = await rooms_svc.list_rooms_for_agent(db, agent_pubkey)
    return [
        RoomSummary(
            room_id=r.id,
            topic=r.topic,
            status=r.status,
            turn_n=r.turn_n,
            turn_owner_pubkey=_hex(r.turn_owner_pubkey),
            created_at=r.created_at,
            ttl_until=r.ttl_until,
            closed_at=r.closed_at,
        )
        for r in rows
    ]


@router.get("/{room_id}", response_model=RoomOut)
async def get_room(room_id: UUID, db: DbDep, agent_pubkey: PubkeyDep) -> RoomOut:
    bundle = await rooms_svc.get_room_with_participants(db, room_id)
    if bundle is None:
        raise errors.room_not_found()
    room, parts = bundle
    if not any(p.agent_pubkey == agent_pubkey for p in parts):
        raise errors.not_a_participant()
    return _to_room_out(room, parts)


@router.post("/{room_id}/accept", response_model=AcceptResponse)
async def accept_room(
    room_id: UUID, payload: AcceptRequest, db: DbDep, agent_pubkey: PubkeyDep
) -> AcceptResponse:
    sig = _parse_sig_hex(payload.sig)
    p = await participants_svc.get(db, room_id, agent_pubkey)
    if p is None:
        raise errors.not_a_participant()

    signed = canonical_json({"room_id": str(room_id), "agent_pubkey": agent_pubkey.hex()})
    if not verify(agent_pubkey, signed, sig):
        raise errors.bad_signature()

    if p.accepted_at is None:
        await participants_svc.accept(db, participant=p, sig=sig)
        await db.commit()
    return AcceptResponse(
        room_id=room_id, agent_pubkey=agent_pubkey.hex(), accepted_at=p.accepted_at
    )


@router.post("/{room_id}/close", response_model=CloseResponse)
async def close_room(
    room_id: UUID, payload: CloseRequest, db: DbDep, agent_pubkey: PubkeyDep
) -> CloseResponse:
    sig = _parse_sig_hex(payload.sig)
    room = await rooms_svc.get_room(db, room_id)
    if room is None:
        raise errors.room_not_found()
    if room.status != "open":
        raise errors.room_closed()

    # Auth: only creator OR current turn_owner can close.
    if agent_pubkey != room.creator_pubkey and agent_pubkey != room.turn_owner_pubkey:
        raise errors.not_a_participant()

    signed = canonical_json(
        {"room_id": str(room_id), "summary": payload.summary}
    )
    if not verify(agent_pubkey, signed, sig):
        raise errors.bad_signature()

    await rooms_svc.close_room(db, room=room, by_pubkey=agent_pubkey, summary=payload.summary)
    await db.commit()
    return CloseResponse(
        room_id=room_id, status=room.status, closed_at=room.closed_at, summary=room.summary
    )
