from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional, List
from app.models.chat import SenderType


class ChatMessageBase(BaseModel):
    sender_type: SenderType
    message_text: str


class ChatMessageResponse(ChatMessageBase):
    id: UUID
    session_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatSessionResponse(BaseModel):
    id: UUID
    response_id: UUID
    started_at: datetime
    ended_at: Optional[datetime] = None
    messages: List[ChatMessageResponse] = []
    
    class Config:
        from_attributes = True

