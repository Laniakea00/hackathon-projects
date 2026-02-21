"""Pydantic schemas for user auth."""

import uuid

from pydantic import BaseModel

from backend.models.user import UserRole


class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole = UserRole.PATIENT


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    role: UserRole

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
