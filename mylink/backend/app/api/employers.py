from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.schemas.employer import EmployerCreate, EmployerResponse
from app.schemas.auth import Token
from app.models.employer import Employer
from app.utils.auth import get_password_hash, create_access_token, get_current_employer

router = APIRouter(prefix="/employers", tags=["Employers"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_employer(
    employer_data: EmployerCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new employer
    Returns JWT access token
    """
    # Check if email already exists
    result = await db.execute(
        select(Employer).where(Employer.email == employer_data.email)
    )
    existing_employer = result.scalar_one_or_none()
    
    if existing_employer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new employer
    new_employer = Employer(
        company_name=employer_data.company_name,
        email=employer_data.email,
        password_hash=get_password_hash(employer_data.password)
    )
    
    db.add(new_employer)
    await db.flush()
    await db.refresh(new_employer)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(new_employer.id), "email": new_employer.email}
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=EmployerResponse)
async def get_current_employer_info(
    current_employer: Employer = Depends(get_current_employer)
):
    """Get current employer information"""
    return current_employer

