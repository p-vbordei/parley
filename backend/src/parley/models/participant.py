import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from parley.models.base import Base


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint("room_id", "agent_pubkey", name="uq_participants_room_agent"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_pubkey: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    owner_pubkey: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    invited_by_pubkey: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accept_sig: Mapped[bytes | None] = mapped_column(LargeBinary(64), nullable=True)
