"""
Database configuration and session management.

Provides async SQLAlchemy engine, session factory, and utilities.
"""

from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import AsyncGenerator, AsyncContextManager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy.pool import NullPool

from secondroute.core.config import settings

# Context variable for current org_id (for RLS emulation in SQLite)
current_org_id: ContextVar[str | None] = ContextVar("current_org_id", default=None)


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
    """Initialize database engine and create tables."""
    global engine, async_session_maker

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

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database engine."""
    global engine
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
        return True
    except Exception:
        return False


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def async_session_factory() -> async_sessionmaker:
    """Get the async session factory."""
    return async_session_maker


# Context variable for current org_id (for RLS emulation in SQLite)
current_org_id: ContextVar[str | None] = ContextVar("current_org_id", default=None)


def get_current_org_id() -> str | None:
    """Get the current org_id from context."""
    return current_org_id.get()


def set_current_org_id(org_id: str | None) -> None:
    """Set the current org_id in context."""
    current_org_id.set(org_id)


def get_session_context() -> AsyncContextManager[AsyncSession]:
    """Get a session context manager."""
    return session_scope()


def with_org_filter(query, model_class, org_id: str | None = None):
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
                query = query.where(model_class.org_id == uuid.UUID('00000000-0000-0000-0000-000000000000'))
    return query
