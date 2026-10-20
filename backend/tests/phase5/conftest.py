"""
PostgreSQL fixtures for testing row-level security (F5.2).

SQLite has no row-level security, so the RLS policies cannot be exercised
there. These fixtures run the real policies against a real PostgreSQL, and
skip cleanly when no PostgreSQL is reachable, so the suite stays green on a
laptop and tests the real thing in CI.

The CI workflow already provides a PostgreSQL service and sets
``DATABASE_URL``. Point it at a database the test may drop and recreate.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from secondroute.core.db import Base, set_session_org_id
from secondroute.feedback.audit import setup_audit_listeners

#: The environment variable that points at the PostgreSQL to test against.
POSTGRES_URL_ENV = "TEST_POSTGRES_URL"


def _postgres_url() -> str | None:
    """Return the PostgreSQL URL to test against, if one was given.

    ``TEST_POSTGRES_URL`` is the explicit opt-in. ``DATABASE_URL`` is
    also accepted, because CI sets it, but only when it names PostgreSQL -
    the default test database is SQLite and must not be used here.
    """
    explicit = os.environ.get(POSTGRES_URL_ENV)
    if explicit:
        return explicit

    from_env = os.environ.get("DATABASE_URL", "")
    if from_env.startswith("postgresql"):
        return from_env
    return None


@pytest.fixture(scope="session")
def postgres_url() -> str:
    """The PostgreSQL URL to test against.

    The test skips when there is none, rather than failing: the RLS
    policies need PostgreSQL, but the rest of the suite does not.
    """
    url = _postgres_url()
    if not url:
        pytest.skip(
            f"No PostgreSQL available. Set {POSTGRES_URL_ENV} to run the row-level security tests."
        )
    return url


@pytest.fixture(scope="session")
async def postgres_engine(postgres_url: str) -> AsyncGenerator[Any, None]:
    """A PostgreSQL engine with the migrated schema.

    The schema is created by running the Alembic migrations, not by
    ``create_all``: the policies are part of the migrations, and a schema
    built any other way would not have them.
    """
    engine = create_async_engine(postgres_url, poolclass=NullPool, echo=False)

    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")

    # Alembic runs synchronously, so it needs the sync form of the URL.
    sync_url = postgres_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

    def _upgrade() -> None:
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
        command.upgrade(alembic_cfg, "head")

    import anyio

    await anyio.to_thread.run_sync(_upgrade)

    # The audit listeners are attached to the Session class, so they have to
    # be registered for these sessions too - the SQLite fixture may never
    # have run before this test.
    setup_audit_listeners()

    yield engine

    await engine.dispose()


@pytest.fixture(scope="function")
async def pg_session(postgres_engine: Any) -> AsyncGenerator[AsyncSession, None]:
    """A session on the PostgreSQL database, with the schema migrated.

    Every test starts from a clean database, so one test's rows cannot
    make another test's isolation look better than it is.
    """
    session_factory = async_sessionmaker(
        postgres_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )

    async with postgres_engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE backtest_runs, audit_log, outcomes, overrides, photos, "
                "inspections, decisions, units, skus, organizations "
                "RESTART IDENTITY CASCADE"
            )
        )

    async with session_factory() as session:
        yield session


async def switch_org(session: AsyncSession, org_id: str | None) -> None:
    """Switch the session to act for a different organisation."""
    await set_session_org_id(session, org_id)
