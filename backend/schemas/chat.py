"""Pydantic schemas for chat API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MessageCreate(BaseModel):
    session_id: Optional[int] = None
    content: str


class MessageOut(BaseModel):
    id: int
    session_id: int
    sender: str
    content: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class ChatSessionOut(BaseModel):
    id: int
    title: str
    created_at: datetime

    model_config = {"from_attributes": True}
