"""Authentication endpoints: register and login."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.session import get_async_db
from backend.models.user import User
from backend.repositories.user import UserRepository
from backend.schemas.user import Token, UserCreate, UserOut
from backend.services.auth import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserCreate,
    session: AsyncSession = Depends(get_async_db),
) -> UserOut:
    repo = UserRepository(session)
    if await repo.get_by_username(body.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )
    user = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    user = await repo.create(user)
    await session.commit()
    return user


@router.post("/login", response_model=Token)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_async_db),
) -> Token:
    repo = UserRepository(session)
    user = await repo.get_by_username(body.username)
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user.username, "role": user.role.value})
    return Token(access_token=token)
