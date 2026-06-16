from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.schemas.auth import Token
from app.schemas.employer import EmployerLogin
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.schemas.candidate import CandidateCreate
from app.models.candidate import Candidate
from app.utils.auth import get_password_hash
from app.models.employer import Employer
from app.utils.auth import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(
    credentials: EmployerLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Login endpoint for employers
    Returns JWT access token
    """
    # Find employer by email
    result = await db.execute(
        select(Employer).where(Employer.email == credentials.email)
    )
    employer = result.scalar_one_or_none()
    
    # Verify credentials
    if not employer or not verify_password(credentials.password, employer.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(employer.id), "email": employer.email}
    )
    
    return Token(access_token=access_token, token_type="bearer")


class CandidateRegister(BaseModel):
    full_name: str
    email: EmailStr
    city: str
    phone: Optional[str] = None
    password: Optional[str] = None
    resume_text: Optional[str] = None


@router.post("/candidate/register", response_model=Token)
async def candidate_register(body: CandidateRegister, db: AsyncSession = Depends(get_db)):
    """Register a candidate (mirrors employer register but simpler)."""
    # If candidate with same email exists, reuse it; otherwise create new
    res = await db.execute(select(Candidate).where(Candidate.email == body.email))
    cand = res.scalars().first()
    if not cand:
        cand = Candidate(full_name=body.full_name, email=body.email, phone=body.phone, city=body.city, resume_text=body.resume_text)
        db.add(cand)
        await db.flush()
    # Return token embedding candidate id in sub (prefix for clarity)
    token = create_access_token(data={"sub": str(cand.id), "email": cand.email, "role": "candidate"})
    return Token(access_token=token, token_type="bearer", candidate_id=cand.id)


class CandidateLogin(BaseModel):
    email: EmailStr
    password: Optional[str] = None


@router.post("/candidate/login", response_model=Token)
async def candidate_login(body: CandidateLogin, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Candidate).where(Candidate.email == body.email))
    cand = res.scalars().first()
    if not cand:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Candidate not found")
    token = create_access_token(data={"sub": str(cand.id), "email": cand.email, "role": "candidate"})
    return Token(access_token=token, token_type="bearer", candidate_id=cand.id)

