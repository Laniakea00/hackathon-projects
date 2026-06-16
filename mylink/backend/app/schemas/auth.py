from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    candidate_id: Optional[UUID] = None  # For candidate login/register


class TokenData(BaseModel):
    user_id: Optional[UUID] = None
    email: Optional[str] = None

