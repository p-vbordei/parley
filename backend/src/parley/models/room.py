import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import DateTime, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from parley.models.base import Base, TimestampMixin


def _default_ttl() -> datetime:
    return datetime.now(UTC) + timedelta(hours=24)


class Room(Base, TimestampMixin):
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic: Mapped[str] = mapped_column(String(256), nullable=False)
    creator_pubkey: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    turn_owner_pubkey: Mapped[bytes | None] = mapped_column(LargeBinary(32), nullable=True)
    turn_n: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
    ttl_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_default_ttl
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_pubkey: Mapped[bytes | None] = mapped_column(LargeBinary(32), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
