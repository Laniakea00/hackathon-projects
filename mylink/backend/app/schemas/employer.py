from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID
from typing import Optional


class EmployerBase(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr


class EmployerCreate(EmployerBase):
    password: str = Field(..., min_length=6)


class EmployerLogin(BaseModel):
    email: EmailStr
    password: str


class EmployerResponse(EmployerBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

