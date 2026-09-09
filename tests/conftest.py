"""Pytest fixtures for OmniBrain test suite."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from apps.api.main import app
from apps.api.deps import get_db
from apps.api.settings import get_settings


@pytest_asyncio.fixture
async def db_session():
    """Provide a fresh database session per test using NullPool."""
    settings = get_settings()
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    test_session_maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with test_session_maker() as session:
        yield session
    await test_engine.dispose()


@pytest_asyncio.fixture
async def test_client(db_session):
    """Provide an HTTP test client with database dependency override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session):
    """Provide a test user from the database."""
    from sqlalchemy import select
    from packages.core.db.models import User

    res = await db_session.execute(select(User).where(User.email == "admin@omnibrain.local"))
    user = res.scalar_one_or_none()
    if not user:
        user = User(
            email="admin@omnibrain.local",
            name="Admin User",
            role="owner",
            timezone="UTC",
            settings={},
        )
        db_session.add(user)
        await db_session.flush()
    return user
