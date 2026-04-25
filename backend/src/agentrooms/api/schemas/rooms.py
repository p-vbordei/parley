from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from agentrooms.api.schemas import IsoDatetime


class RoomCreateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=256)
    invite_pubkeys: list[str] = Field(min_length=0)
    max_turns: int = Field(default=40, ge=1, le=1000)
    ttl_hours: int = Field(default=24, ge=1, le=720)
    created_at: datetime  # in signed payload; enforces freshness, defeats capture-and-replay
    sig: str  # hex


class ParticipantOut(BaseModel):
    agent_pubkey: str  # hex
    invited_by_pubkey: str
    invited_at: IsoDatetime
    accepted_at: IsoDatetime | None = None


class RoomSummary(BaseModel):
    room_id: UUID
    topic: str
    status: str
    turn_n: int
    turn_owner_pubkey: str | None
    created_at: IsoDatetime
    ttl_until: IsoDatetime
    closed_at: IsoDatetime | None = None


class RoomOut(BaseModel):
    room_id: UUID
    topic: str
    creator_pubkey: str
    status: str
    turn_n: int
    turn_owner_pubkey: str | None
    max_turns: int
    ttl_until: IsoDatetime
    created_at: IsoDatetime
    closed_at: IsoDatetime | None = None
    summary: str | None = None
    participants: list[ParticipantOut]


class AcceptRequest(BaseModel):
    created_at: datetime
    sig: str  # hex over canonical {room_id, agent_pubkey, created_at}


class AcceptResponse(BaseModel):
    room_id: UUID
    agent_pubkey: str
    accepted_at: IsoDatetime


class CloseRequest(BaseModel):
    summary: str | None = None
    created_at: datetime
    sig: str  # hex over canonical {room_id, summary, created_at}


class CloseResponse(BaseModel):
    room_id: UUID
    status: str
    closed_at: IsoDatetime
    summary: str | None
