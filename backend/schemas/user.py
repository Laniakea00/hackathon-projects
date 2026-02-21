"""Pydantic v2 schemas for the user API."""

import uuid

from pydantic import BaseModel, EmailStr

from backend.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.DOCTOR


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: UserRole

    model_config = {"from_attributes": True}
