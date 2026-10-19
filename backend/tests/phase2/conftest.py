"""
Isolated test setup for the Phase 2 decision engine.

The Phase 2 tests live in their own directory with their own database
fixtures so they do not depend on the shared ``tests/conftest.py`` (which
other agents are actively editing).
"""

from __future__ import annotations

import sys
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from secondroute.api.main import app
from secondroute.core.db import Base, get_session

# Register the Phase 2 tables with the metadata before any table is created.
import secondroute.condition.models  # noqa: F401
import secondroute.costs.models  # noqa: F401
import secondroute.decision.models  # noqa: F401
import secondroute.identity.models  # noqa: F401
import secondroute.intake.models  # noqa: F401
import secondroute.pricing.models  # noqa: F401

# Make the ml/ package importable (``from synthetic.generator import ...``)
ML_DIR = Path(__file__).parent.parent.parent.parent / "ml"
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from tests.phase2.decision_fixtures import (  # noqa: E402, F401
    cost_book,
    evaluation_input,
    good_signals,
    locked_signals,
    poor_signals,
    sku_id,
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def test_engine() -> AsyncGenerator[Any, None]:
    """Create a test database engine with every table."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_engine: Any) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session


@pytest.fixture(scope="function")
async def db_session(test_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Alias for ``test_session``."""
    yield test_session


@pytest.fixture(scope="function")
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with the database session overridden."""

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
