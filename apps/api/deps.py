"""FastAPI dependency injection — database sessions, auth, redis."""
from typing import AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.settings import get_settings
from packages.core.db.session import get_session
from packages.core.db.models import User
from packages.core.security.auth import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session."""
    async for session in get_session():
        yield session


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """Provide a Redis client."""
    settings = get_settings()
    client = redis.from_url(settings.REDIS_URL)
    try:
        yield client
    finally:
        await client.aclose()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode JWT token and return the authenticated user."""
    try:
        payload = decode_token(token)
        if payload.type != "access":
            raise ValueError("Not an access token")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = UUID(payload.sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
