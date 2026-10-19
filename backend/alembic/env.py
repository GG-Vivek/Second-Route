# Alembic Environment Configuration
# https://alembic.sqlalchemy.org/en/latest/api/runtime.html#alembic.runtime.environment.EnvironmentContext

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection, create_engine

from alembic import context

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import application models and settings
from secondroute.core.config import settings
from secondroute.core.db import Base

# Import all models to ensure they're registered with Base.metadata
# These will be imported as models are created in each phase
# import secondroute.identity.models
# import secondroute.intake.models
# import secondroute.condition.models
# import secondroute.pricing.models
# import secondroute.costs.models
# import secondroute.decision.models
# import secondroute.feedback.models
# import secondroute.analytics.models

# Alembic Config object
config = context.config

# Override sqlalchemy.url with application settings
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with a database connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    A synchronous engine is used on purpose: the same code then works against
    PostgreSQL (psycopg2) and SQLite, which keeps the migration test in CI
    simple.
    """
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError("sqlalchemy.url is not configured")

    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
