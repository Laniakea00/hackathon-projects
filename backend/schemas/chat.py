"""Pydantic v2 schemas for the clinical chat API."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from backend.models.chat import CaseStatus, MessageRole


class ClinicalCaseCreate(BaseModel):
    user_id: uuid.UUID
    title: str


class ClinicalCaseOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    status: CaseStatus

    model_config = {"from_attributes": True}


class ChatMessageCreate(BaseModel):
    case_id: uuid.UUID
    role: MessageRole
    content: str
    context_used: Optional[list[int]] = None


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    role: MessageRole
    content: str
    context_used: Optional[list[int]] = None

    model_config = {"from_attributes": True}


class UserCardCreate(BaseModel):
    case_id: uuid.UUID
    age: Optional[int] = None
    gender: Optional[str] = None
    chronic_diseases: Optional[list[str]] = None


class UserCardOut(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    age: Optional[int] = None
    gender: Optional[str] = None
    chronic_diseases: Optional[list[str]] = None

    model_config = {"from_attributes": True}
