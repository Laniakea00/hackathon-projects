from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any


class VacancyBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    requirements: Optional[Dict[str, Any]] = None
    location: str = Field(..., min_length=1)
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    max_questions: int = Field(3, ge=3, le=8, description="Maximum interview questions (3-8)")


class VacancyCreate(VacancyBase):
    pass


class VacancyUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    requirements: Optional[Dict[str, Any]] = None
    location: Optional[str] = Field(None, min_length=1)
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    max_questions: Optional[int] = Field(None, ge=3, le=8)


class VacancyResponse(VacancyBase):
    id: UUID
    employer_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

