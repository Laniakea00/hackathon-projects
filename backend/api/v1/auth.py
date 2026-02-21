"""Authentication endpoints: register and login."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.session import get_async_db
from backend.models.user import User
from backend.repositories.user import UserRepository
from backend.schemas.user import Token, UserCreate, UserOut
from backend.services.auth import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserCreate,
    session: AsyncSession = Depends(get_async_db),
) -> UserOut:
    """Create a new user account. Default role is PATIENT."""
    repo = UserRepository(session)
    if await repo.get_by_email(body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    user = await repo.create(user)
    await session.commit()
    return user


@router.post("/login", response_model=Token)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_async_db),
) -> Token:
    """Exchange email + password for a JWT access token.

    Uses standard OAuth2 Password flow — ``username`` field carries the email.
    """
    repo = UserRepository(session)
    user = await repo.get_by_email(form.username)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user.email, "role": user.role.value})
    return Token(access_token=token)
