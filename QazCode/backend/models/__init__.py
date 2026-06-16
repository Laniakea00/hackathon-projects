"""Exports all ORM models so SQLAlchemy's metadata is fully populated.

Import this package before calling Base.metadata.create_all() or running
Alembic migrations to ensure every table is registered.
"""

from backend.models.protocol import EMBEDDING_DIM, Protocol, ProtocolChunk  # noqa: F401
from backend.models.diagnosis import Diagnosis  # noqa: F401
from backend.models.user import User, UserRole  # noqa: F401
from backend.models.chat import ChatSession, Message  # noqa: F401

__all__ = [
    "EMBEDDING_DIM",
    "Protocol",
    "ProtocolChunk",
    "Diagnosis",
    "User",
    "UserRole",
    "ChatSession",
    "Message",
]
