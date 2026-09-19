"""Async Database Session Engine for OmniBrain."""
import os
import sys
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://omnibrain:omnibrain_dev@localhost:5432/omnibrain",
)

# Use NullPool during pytest runs to avoid loop conflicts across test async functions
is_testing = bool(os.getenv("PYTEST_CURRENT_TEST") or "pytest" in sys.modules)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    poolclass=NullPool if is_testing else AsyncAdaptedQueuePool,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


def get_engine() -> AsyncEngine:
    """Returns the async SQLAlchemy engine."""
    return engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides an asynchronous database session."""
    async with async_session_maker() as session:
        yield session
