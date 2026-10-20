"""
Pytest configuration and fixtures for SecondRoute backend tests.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from secondroute.api.main import app
from secondroute.core.config import settings
from secondroute.core.db import Base, get_session
from secondroute.feedback.audit import setup_audit_listeners

# Import all models to ensure they're registered with Base.metadata
import secondroute.identity.models  # noqa: F401
import secondroute.intake.models  # noqa: F401
import secondroute.feedback.models  # noqa: F401

# Test database URL (in-memory SQLite for unit tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine() -> AsyncGenerator[Any, None]:
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # The audit listeners are attached to the Session, so they have to be
    # registered once the models are loaded.
    setup_audit_listeners()

    yield engine

    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_engine: Any) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def db_session(test_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Alias for test_session for test compatibility."""
    yield test_session


@pytest.fixture(scope="function")
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with overridden database session."""

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        # Mirror the real dependency: commit on success, roll back on error.
        try:
            yield test_session
            await test_session.commit()
        except Exception:
            await test_session.rollback()
            raise

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock settings for testing."""
    monkeypatch.setattr(settings, "DEBUG", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    monkeypatch.setattr(settings, "LOG_LEVEL", "DEBUG")
    monkeypatch.setattr(settings, "SECRET_KEY", "test-secret-key")
    monkeypatch.setattr(settings, "DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://localhost:6379/1")
