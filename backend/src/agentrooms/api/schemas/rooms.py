from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RoomCreateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=256)
    invite_pubkeys: list[str] = Field(min_length=0)
    max_turns: int = Field(default=40, ge=1, le=1000)
    ttl_hours: int = Field(default=24, ge=1, le=720)
    sig: str  # hex


class ParticipantOut(BaseModel):
    agent_pubkey: str  # hex
    invited_by_pubkey: str
    invited_at: datetime
    accepted_at: datetime | None = None


class RoomOut(BaseModel):
    room_id: UUID
    topic: str
    creator_pubkey: str
    status: str
    turn_n: int
    turn_owner_pubkey: str | None
    max_turns: int
    ttl_until: datetime
    created_at: datetime
    closed_at: datetime | None = None
    summary: str | None = None
    participants: list[ParticipantOut]


class AcceptRequest(BaseModel):
    sig: str  # hex over canonical {room_id, agent_pubkey}


class AcceptResponse(BaseModel):
    room_id: UUID
    agent_pubkey: str
    accepted_at: datetime


class CloseRequest(BaseModel):
    summary: str | None = None
    sig: str  # hex over canonical body sans sig


class CloseResponse(BaseModel):
    room_id: UUID
    status: str
    closed_at: datetime
    summary: str | None
