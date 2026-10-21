"""
Database configuration and session management.

Provides async SQLAlchemy engine, session factory, and utilities.
"""

import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, AsyncGenerator, AsyncContextManager, AsyncIterator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy.pool import NullPool

from secondroute.core.config import settings

# Context variable for current org_id (for RLS emulation in SQLite)
current_org_id: ContextVar[str | None] = ContextVar("current_org_id", default=None)

# Context variable for the user the current request acts as.
#
# The audit log records who made a change. Until Phase 5 there was nobody
# to name, so every row said "anonymous". Now that the requests are
# authenticated, the name of the user is carried here and read by the
# audit listeners.
current_actor: ContextVar[str | None] = ContextVar("current_actor", default=None)

#: The actor recorded for a change made by an unauthenticated request.
ANONYMOUS_ACTOR = "anonymous"


class Base(DeclarativeBase):
    """Base class for all models."""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    def __repr__(self) -> str:
        cols = ", ".join(f"{c.name}={getattr(self, c.name)!r}" for c in self.__table__.columns)
        return f"<{self.__class__.__name__}({cols})>"


# Global async engine
engine: AsyncEngine | None = None
async_session_maker: async_sessionmaker | None = None


async def init_db() -> None:
    """Initialize database engine and bring the schema up to date."""
    # The engine and the session factory are process-wide singletons: one
    # pool for the whole application, created once at startup.
    global engine, async_session_maker  # noqa: PLW0603

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        poolclass=NullPool if "sqlite" in settings.DATABASE_URL else None,
        pool_pre_ping=True,
    )

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    await run_migrations()


def _alembic_paths() -> tuple[Path, Path]:
    """Return the Alembic config file and the migrations directory.

    Both are found relative to the installed package, not the working
    directory, so the migrations run wherever the application is started
    from - a container's ``/app``, for instance.
    """
    backend_root = Path(__file__).resolve().parents[3]
    return backend_root / "alembic.ini", backend_root / "alembic"


async def run_migrations() -> None:
    """Bring the database schema up to date.

    The schema is created by the migrations rather than by
    ``create_all``, because the migrations are where the tenant-isolation
    policies live. A schema built any other way would have the tables but
    none of the isolation, and the isolation is the point of the policies.

    Alembic runs synchronously, so it is run in a worker thread.
    """
    import asyncio

    from alembic import command
    from alembic.config import Config

    config_path, migrations_path = _alembic_paths()
    if not config_path.exists():
        raise RuntimeError(
            f"The Alembic configuration was not found at {config_path}. The application "
            f"cannot create its schema without it."
        )

    def _upgrade() -> None:
        config = Config(str(config_path))
        config.set_main_option("script_location", str(migrations_path))
        config.set_main_option("sqlalchemy.url", settings.database_url_sync)
        command.upgrade(config, "head")

    await asyncio.get_running_loop().run_in_executor(None, _upgrade)


async def close_db() -> None:
    """Close database engine."""
    global engine  # noqa: PLW0603
    if engine:
        await engine.dispose()
        engine = None


async def check_db_connection() -> bool:
    """Check if database connection is working."""
    if not engine:
        return False
    try:
        async with engine.connect() as conn:
            from sqlalchemy import text

            await conn.execute(text("SELECT 1"))
    except Exception:
        return False
    else:
        return True


def _require_session_maker() -> async_sessionmaker:
    """Return the session factory, or fail loudly when it is not set up.

    Returns:
        The session factory.

    Raises:
        RuntimeError: When ``init_db`` has not run yet.
    """
    if async_session_maker is None:
        raise RuntimeError("The database is not initialised. Call init_db() first.")
    return async_session_maker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session.

    The organisation context is applied to the connection here, before the
    route runs. The context variable is set by the request middleware (or
    by the authentication dependency, which knows the tenant from the
    token); this turns it into the PostgreSQL setting the row-level
    security policies read, on the same connection and inside the same
    transaction as the work.

    Without it the policies have nothing to match, and every write to a
    tenant-scoped table is refused.
    """
    maker = _require_session_maker()
    async with maker() as session:
        await set_session_org_id(session, get_current_org_id())
        try:
            yield session
            await commit_with_tenant(session)
        except Exception:
            await session.rollback()
            raise
        finally:
            # The organisation context is per request. Clearing it here
            # stops one request's tenant from leaking into the next one on
            # the same worker.
            current_org_id.set(None)


def async_session_factory() -> async_sessionmaker:
    """Get the async session factory."""
    return _require_session_maker()


async def commit_with_tenant(session: AsyncSession) -> None:
    """Commit, and keep the organisation.

    The organisation setting is transaction-local, so a commit clears it.
    Anything the request does after the commit would then run with no
    organisation, and the row-level security policies would refuse the
    writes. The setting is put back.

    Args:
        session: The session to commit.
    """
    await session.commit()
    await set_session_org_id(session, get_current_org_id())


def get_current_org_id() -> str | None:
    """Get the current org_id from context."""
    return current_org_id.get()


def current_org_uuid() -> uuid.UUID | None:
    """Return the organisation the request acts for, as an id.

    Returns:
        The organisation's id, or None when the request names no
        organisation.
    """
    raw = current_org_id.get()
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except (ValueError, AttributeError, TypeError):
        return None


def set_current_org_id(org_id: str | None) -> None:
    """Set the current org_id in context."""
    current_org_id.set(org_id)


def get_current_actor() -> str:
    """Return the user the current request acts as.

    Returns:
        The user's email, or ``anonymous`` when the request is not
        authenticated.
    """
    return current_actor.get() or ANONYMOUS_ACTOR


def set_current_actor(actor: str | None) -> None:
    """Set the user the current request acts as.

    Args:
        actor: The user's email, or None for an unauthenticated request.
    """
    current_actor.set(actor)


def _is_postgres(session: AsyncSession) -> bool:
    """Whether the session is talking to PostgreSQL."""
    try:
        bind = session.get_bind()
    except Exception:
        return False
    return bool(bind.dialect.name == "postgresql")


async def set_session_org_id(session: AsyncSession, org_id: str | None) -> None:
    """Set the organisation context for the current transaction.

    Two things have to agree about which organisation a session is acting
    for, or the isolation is only half implemented:

    - the application-level filter, which reads the ``current_org_id``
      context variable, and
    - the database-level row-level security policies, which read the
      PostgreSQL setting ``app.current_org_id``.

    Setting only the first leaves the policies with nothing to match, and
    setting only the second leaves the application filter open. This sets
    both.

    The setting is transaction-local, so it is discarded when the
    transaction ends and cannot leak into the next request on the same
    connection. On a database without row-level security - SQLite in the
    test suite - only the context variable is set.

    Args:
        session: The session to set the context on.
        org_id: The organisation, or ``None`` for no organisation.
    """
    set_current_org_id(org_id)
    if not _is_postgres(session):
        return
    # The setting is always written, including when there is no
    # organisation. Leaving a previous organisation's value in place would
    # let the next request on the same connection see that tenant's rows.
    await session.execute(
        text("SELECT set_config('app.current_org_id', :org_id, true)"),
        {"org_id": str(org_id) if org_id else ""},
    )


@asynccontextmanager
async def get_session_context() -> AsyncIterator[AsyncSession]:
    """Get a session context manager.

    The same session the application uses per request: one transaction,
    committed on success and rolled back on failure.
    """
    async for session in get_session():
        yield session


def with_org_filter(query: Any, model_class: type, org_id: str | None = None) -> Any:
    """Apply org_id filter to query if model has org_id column.

    If org_id is None (no org context set), returns a query that matches no rows
    for strict tenant isolation.
    """
    if org_id is None:
        org_id = current_org_id.get()
    if hasattr(model_class, "org_id"):
        from sqlalchemy.orm import InstrumentedAttribute
        import uuid

        if isinstance(getattr(model_class, "org_id", None), InstrumentedAttribute):
            if org_id is not None:
                # Convert string to UUID for comparison
                query = query.where(model_class.org_id == uuid.UUID(org_id))
            else:
                # Strict mode: no org context = no access
                query = query.where(
                    model_class.org_id == uuid.UUID("00000000-0000-0000-0000-000000000000")
                )
    return query
