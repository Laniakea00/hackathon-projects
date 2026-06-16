"""SQLAlchemy ORM models for clinical protocols and their vector chunks."""

from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from backend.database.base import Base

# Must match the SentenceTransformer model used during ingestion.
# intfloat/multilingual-e5-large → 1024 dimensions.
EMBEDDING_DIM: int = 1024


class Protocol(Base):
    __tablename__ = "protocols"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source_file: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text: Mapped[str] = mapped_column(Text, nullable=False)

    diagnoses: Mapped[list["Diagnosis"]] = relationship(  # type: ignore[name-defined]
        "Diagnosis",
        back_populates="protocol",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chunks: Mapped[list["ProtocolChunk"]] = relationship(
        "ProtocolChunk",
        back_populates="protocol",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ProtocolChunk(Base):
    """A cleaned, chunked fragment of a Protocol with its vector embedding."""

    __tablename__ = "protocol_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    protocol_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("protocols.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # pgvector type not yet Mapped-compatible universally; use Column() directly.
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "protocol_id", "chunk_index", name="uq_chunk_protocol_index"
        ),
    )

    protocol: Mapped["Protocol"] = relationship("Protocol", back_populates="chunks")
