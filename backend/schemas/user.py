"""Pydantic v2 schemas for the user API."""

import uuid

from pydantic import BaseModel, EmailStr

from backend.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.PATIENT


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: UserRole

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: str
    role: UserRole
