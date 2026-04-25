"""Messages HTTP layer."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from agentrooms import errors
from agentrooms.api.deps import get_agent_pubkey, get_db
from agentrooms.api.schemas.messages import (
    MessageOut,
    MessagePostRequest,
    MessagePostResponse,
    MessagesListResponse,
)
from agentrooms.crypto import canonical_json, verify
from agentrooms.services import messages as messages_svc
from agentrooms.services import participants as participants_svc
from agentrooms.services import rooms as rooms_svc

router = APIRouter(prefix="/v1/rooms", tags=["messages"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
PubkeyDep = Annotated[bytes, Depends(get_agent_pubkey)]


def _parse_sig_hex(s: str) -> bytes:
    try:
        sig = bytes.fromhex(s)
    except ValueError as e:
        raise errors.bad_signature() from e
    if len(sig) != 64:
        raise errors.bad_signature()
    return sig


@router.post("/{room_id}/messages", response_model=MessagePostResponse)
async def post_message(
    room_id: UUID,
    payload: MessagePostRequest,
    db: DbDep,
    agent_pubkey: PubkeyDep,
) -> MessagePostResponse:
    if len(payload.body.encode("utf-8")) > messages_svc.MAX_BODY_BYTES:
        raise errors.body_too_large()

    sig = _parse_sig_hex(payload.sig)

    bundle = await rooms_svc.get_room_with_participants(db, room_id)
    if bundle is None:
        raise errors.room_not_found()
    room, parts = bundle

    if room.status != "open" or await rooms_svc.is_expired(room):
        raise errors.room_closed()

    p = next((x for x in parts if x.agent_pubkey == agent_pubkey), None)
    if p is None or not participants_svc.is_accepted(p):
        raise errors.not_a_participant()

    if room.turn_owner_pubkey != agent_pubkey:
        raise errors.not_turn_owner()

    expected_turn = room.turn_n + 1
    if payload.turn_n != expected_turn:
        raise errors.turn_conflict(expected_turn, payload.turn_n)

    if not messages_svc.is_timestamp_fresh(payload.created_at):
        raise errors.stale_timestamp()

    signed = canonical_json(
        {
            "room_id": str(room_id),
            "turn_n": payload.turn_n,
            "author_pubkey": agent_pubkey.hex(),
            "body": payload.body,
            "created_at": payload.created_at.isoformat(),
        }
    )
    if not verify(agent_pubkey, signed, sig):
        raise errors.bad_signature()

    msg = await messages_svc.post_message(
        db,
        room=room,
        participants=parts,
        author_pubkey=agent_pubkey,
        turn_n=payload.turn_n,
        body=payload.body,
        sig=sig,
        created_at=payload.created_at,
    )
    await db.commit()
    return MessagePostResponse(
        message_id=msg.id,
        turn_n=msg.turn_n,
        next_turn_owner_pubkey=room.turn_owner_pubkey.hex() if room.turn_owner_pubkey else None,
        room_status=room.status,
    )


@router.get("/{room_id}/messages", response_model=MessagesListResponse)
async def list_messages(
    room_id: UUID,
    db: DbDep,
    agent_pubkey: PubkeyDep,
    since: Annotated[int, Query(ge=-1)] = -1,
) -> MessagesListResponse:
    bundle = await rooms_svc.get_room_with_participants(db, room_id)
    if bundle is None:
        raise errors.room_not_found()
    room, parts = bundle

    if not any(p.agent_pubkey == agent_pubkey for p in parts):
        raise errors.not_a_participant()

    rows = await messages_svc.list_since(db, room_id=room_id, since=since)
    return MessagesListResponse(
        messages=[
            MessageOut(
                message_id=m.id,
                room_id=m.room_id,
                author_pubkey=m.author_pubkey.hex(),
                turn_n=m.turn_n,
                body=m.body,
                sig=m.sig.hex(),
                created_at=m.created_at,
            )
            for m in rows
        ],
        room_status=room.status,
        turn_n=room.turn_n,
        turn_owner_pubkey=room.turn_owner_pubkey.hex() if room.turn_owner_pubkey else None,
    )
