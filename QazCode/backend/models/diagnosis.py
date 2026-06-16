"""SQLAlchemy ORM model for ICD-10 diagnoses linked to protocols."""

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base


class Diagnosis(Base):
    """Links a Protocol to one ICD-10 code (one row per code)."""

    __tablename__ = "diagnoses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    protocol_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("protocols.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    icd_code: Mapped[str] = mapped_column(String(20), nullable=False)

    __table_args__ = (
        UniqueConstraint("protocol_id", "icd_code", name="uq_diagnosis_protocol_code"),
    )

    protocol: Mapped["Protocol"] = relationship(  # type: ignore[name-defined]
        "Protocol", back_populates="diagnoses"
    )
