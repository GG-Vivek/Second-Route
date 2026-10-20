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

# Import all models so that they are registered with Base.metadata.
#
# Without these the target metadata is empty, and "alembic check" and
# "alembic revision --autogenerate" would both believe the database holds
# no tables at all.
import secondroute.identity.models  # noqa: F401
import secondroute.identity.organizations  # noqa: F401
import secondroute.intake.models  # noqa: F401
import secondroute.condition.models  # noqa: F401
import secondroute.pricing.models  # noqa: F401
import secondroute.costs.models  # noqa: F401
import secondroute.decision.models  # noqa: F401
import secondroute.feedback.models  # noqa: F401
import secondroute.backtest.models  # noqa: F401
import secondroute.ingest.models  # noqa: F401
import secondroute.learning.registry  # noqa: F401
import secondroute.learning.shadow  # noqa: F401
import secondroute.learning.promotion  # noqa: F401
import secondroute.learning.drift  # noqa: F401
import secondroute.learning.exploration  # noqa: F401
import secondroute.learning.expert_review  # noqa: F401
import secondroute.analytics.models  # noqa: F401

# Alembic Config object
config = context.config

# Override sqlalchemy.url with application settings, unless the caller
# already chose one. A caller that wants to migrate a different database -
# a test that migrates a throwaway PostgreSQL, for example - sets the URL
# on the Alembic config, and that choice has to survive this line.
if not config.get_main_option("sqlalchemy.url", None):
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
