from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.base import Base


class Vacancy(Base):
    __tablename__ = "vacancies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    employer_id = Column(UUID(as_uuid=True), ForeignKey("employers.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(JSON, nullable=True)
    location = Column(String, nullable=False)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    max_questions = Column(Integer, default=3, nullable=False, comment="Maximum interview questions (3-8)")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    employer = relationship("Employer", back_populates="vacancies")
    responses = relationship("CandidateResponse", back_populates="vacancy", cascade="all, delete-orphan")

