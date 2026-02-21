"""SQLAlchemy ORM models for clinical chat cases, messages, and user cards."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base


class CaseStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ClinicalCase(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    status: Mapped[CaseStatus] = mapped_column(
        SAEnum(CaseStatus, name="casestatus", create_type=True),
        nullable=False,
        default=CaseStatus.OPEN,
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="case",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    card: Mapped[Optional["UserCard"]] = relationship(
        "UserCard",
        back_populates="case",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MessageRole] = mapped_column(
        SAEnum(MessageRole, name="messagerole", create_type=True),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # list[int] of ProtocolChunk IDs used as context for this message.
    context_used = Column(JSON, nullable=True)

    case: Mapped["ClinicalCase"] = relationship("ClinicalCase", back_populates="messages")


class UserCard(Base):
    """Demographic / medical history card for a clinical case (one per case)."""

    __tablename__ = "user_cards"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # list[str] of chronic disease names.
    chronic_diseases = Column(JSON, nullable=True)

    case: Mapped["ClinicalCase"] = relationship("ClinicalCase", back_populates="card")
