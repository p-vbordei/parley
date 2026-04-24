from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from agentrooms.api.schemas import IsoDatetime


class MessagePostRequest(BaseModel):
    turn_n: int = Field(ge=1)
    body: str = Field(min_length=1, max_length=16 * 1024)
    created_at: datetime  # request-side: accept any valid ISO 8601; signed form must match wire
    sig: str  # hex over canonical {room_id, turn_n, author_pubkey, body, created_at}


class MessagePostResponse(BaseModel):
    message_id: UUID
    turn_n: int
    next_turn_owner_pubkey: str | None
    room_status: str


class MessageOut(BaseModel):
    message_id: UUID
    room_id: UUID
    author_pubkey: str
    turn_n: int
    body: str
    sig: str
    created_at: IsoDatetime


class MessagesListResponse(BaseModel):
    messages: list[MessageOut]
    room_status: str
    turn_n: int
    turn_owner_pubkey: str | None
