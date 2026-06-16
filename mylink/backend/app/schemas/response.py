from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any
from app.models.response import ResponseStatus


class ResponseCreate(BaseModel):
    vacancy_id: UUID
    candidate_id: UUID


class ResponseResponse(BaseModel):
    id: UUID
    vacancy_id: UUID
    candidate_id: UUID
    status: ResponseStatus
    relevance_score: Optional[float] = None
    rejection_reasons: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ResponseListItem(ResponseResponse):
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    candidate_city: Optional[str] = None

