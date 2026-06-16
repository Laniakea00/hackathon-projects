from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID
from typing import Optional


class CandidateBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    city: str = Field(..., min_length=1, max_length=255)
    resume_text: Optional[str] = None


class CandidateCreate(CandidateBase):
    pass


class CandidateResponse(CandidateBase):
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

