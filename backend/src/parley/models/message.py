import uuid

from sqlalchemy import ForeignKey, Integer, LargeBinary, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from parley.models.base import Base, TimestampMixin


class Message(Base, TimestampMixin):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("room_id", "turn_n", name="uq_messages_room_turn"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_pubkey: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    turn_n: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sig: Mapped[bytes] = mapped_column(LargeBinary(64), nullable=False)
