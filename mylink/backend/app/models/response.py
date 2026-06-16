from sqlalchemy import Column, String, Float, Text, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.db.base import Base


class ResponseStatus(str, enum.Enum):
    NEW = "new"
    IN_CHAT = "in_chat"
    APPROVED = "approved"
    REJECTED = "rejected"


class CandidateResponse(Base):
    __tablename__ = "candidate_responses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    vacancy_id = Column(UUID(as_uuid=True), ForeignKey("vacancies.id", ondelete="CASCADE"), nullable=False)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(ResponseStatus), default=ResponseStatus.NEW, nullable=False)
    relevance_score = Column(Float, nullable=True)
    rejection_reasons = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # AI Interview fields
    mismatch_analysis = Column(JSON, nullable=True, comment="Initial mismatch detection results from AI")
    dialog_findings = Column(JSON, nullable=True, comment="Collected answers and findings during interview")
    language_preference = Column(String(5), default="ru", nullable=False, comment="Interview language: ru, kk, en")
    
    # Relationships
    vacancy = relationship("Vacancy", back_populates="responses")
    candidate = relationship("Candidate", back_populates="responses")
    chat_session = relationship("ChatSession", back_populates="response", uselist=False, cascade="all, delete-orphan")

