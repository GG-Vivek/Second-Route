"""
The restore drill, as a test (Phase 5 - F5.8).

F5.8's acceptance criterion is "a restore into a fresh environment
reproduces row counts and passes the smoke test". A backup that has never
been restored is a hope, not a backup, so the drill runs here rather than
only when a restore is needed.

The drill needs a real PostgreSQL, ``pg_dump`` and restic. It skips when
any of them is missing, so the suite stays green on a machine that has
none of them, and it runs for real in an environment that does.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path
from urllib.parse import urlparse

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "scripts"
DRILL = SCRIPTS / "verify_restore.sh"

#: The environment variable that points at the PostgreSQL to drill.
POSTGRES_URL_ENV = "TEST_POSTGRES_URL"


def _missing_tools() -> list[str]:
    """Return the tools the drill needs that are not installed."""
    return [
        tool
        for tool in ("pg_dump", "pg_restore", "restic", "psql", "createdb")
        if not shutil.which(tool)
    ]


def _postgres_url() -> str | None:
    """Return the PostgreSQL URL to drill against, if one was given."""
    url = os.environ.get(POSTGRES_URL_ENV, "")
    return url or None


pytestmark = pytest.mark.skipif(
    bool(_missing_tools()) or _postgres_url() is None,
    reason=(
        "The restore drill needs PostgreSQL, pg_dump, pg_restore and restic. "
        f"Set {POSTGRES_URL_ENV} to a database the drill may use."
    ),
)


@pytest.fixture
def postgres_url() -> str:
    """The PostgreSQL URL the drill runs against."""
    url = _postgres_url()
    assert url is not None
    return url


@pytest.fixture
def backup_url(postgres_url: str) -> str:
    """The URL of the role the backup uses.

    The application's role is held to the tenant-isolation policies, and
    pg_dump refuses to dump a table whose rows the policies would filter.
    The backup needs a role that can read every row. When
    ``TEST_POSTGRES_BACKUP_URL`` is not given, the application URL is
    used, and the drill then fails - which is the point: a deployment
    that backs up with the application's role cannot take a backup at all.
    """
    backup = os.environ.get("TEST_POSTGRES_BACKUP_URL", "")
    return backup or postgres_url


@pytest.fixture
def restic_repository(tmp_path: Path) -> str:
    """An empty restic repository for the drill to use."""
    repository = tmp_path / "restic-repo"
    environment = {
        **os.environ,
        "RESTIC_REPOSITORY": str(repository),
        "RESTIC_PASSWORD": "drill-only-password",
    }
    subprocess.run(
        ["restic", "init"],
        env=environment,
        check=True,
        capture_output=True,
    )
    return str(repository)


async def _seed(url: str) -> None:
    """Put some rows in the database, so the drill has something to compare."""
    engine = create_async_engine(url, poolclass=NullPool, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    # A unique variant, so that seeding twice against the same database
    # does not collide with the catalogue's unique constraint.
    variant = uuid.uuid4().hex[:8]
    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO organizations (id, name, risk_profile, created_at) "
                "VALUES (:id, 'Drill Org', 'balanced', now())"
            ),
            {"id": uuid.uuid4()},
        )
        await session.execute(
            text(
                "INSERT INTO skus (id, family, model_name, year, storage_gb, ram_gb, "
                "color, region, specs_json, source, as_of) "
                "VALUES (:id, 'MacBook Pro', :model, '2023', '512', '18', "
                "'Gray', 'US', '{}'::json, 'test', current_date)"
            ),
            {"id": uuid.uuid4(), "model": f"Drill {variant}"},
        )
        await session.commit()
    await engine.dispose()


class TestRestoreDrill:
    """The drill has to pass, against a real database."""

    @pytest.mark.asyncio
    async def test_a_backup_restores_into_a_fresh_database(
        self, postgres_url: str, backup_url: str, restic_repository: str, tmp_path: Path
    ) -> None:
        """A backup restores into a fresh database with the same rows.

        This is the acceptance criterion for F5.8: the restore reproduces
        the row counts and the application runs against the result.
        """
        await _seed(postgres_url)

        environment = {
            **os.environ,
            "DATABASE_URL": postgres_url,
            "BACKUP_DATABASE_URL": backup_url,
            "RESTIC_REPOSITORY": restic_repository,
            "RESTIC_PASSWORD": "drill-only-password",
            # The drill drops its database when it is done. A name of its
            # own keeps it clear of the database being backed up.
            "DRILL_DATABASE": f"secondroute_drill_{uuid.uuid4().hex[:8]}",
        }

        result = subprocess.run(
            ["bash", str(DRILL)],
            env=environment,
            capture_output=True,
            text=True,
            timeout=600,
            # The drill's exit status is the assertion, not an exception.
            check=False,
        )

        output = result.stdout + result.stderr
        assert result.returncode == 0, f"The drill failed:\n{output}"
        assert "DRILL PASSED" in output
        # The row counts have to have been compared, not skipped.
        assert "tables match" in output
