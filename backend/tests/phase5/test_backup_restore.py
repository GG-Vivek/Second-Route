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
import sys
import uuid
from pathlib import Path
from urllib.parse import ParseResult, urlparse

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


def _parsed(url: str) -> ParseResult:
    """Return the parts of a connection URL."""
    return urlparse(url.replace("postgresql+asyncpg://", "postgresql://"))


def _without_database(url: str) -> str:
    """Return the URL without its database name."""
    parsed = _parsed(url)
    return f"postgresql://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}"


def _database_of(url: str) -> str:
    """Return the database name of a connection URL."""
    return _parsed(url).path.lstrip("/")


def _libpq_environment(url: str) -> dict[str, str]:
    """Return the environment the libpq tools need to reach a database."""
    parsed = _parsed(url)
    return {
        **os.environ,
        "PGHOST": parsed.hostname or "localhost",
        "PGPORT": str(parsed.port or 5432),
        "PGUSER": parsed.username or "postgres",
        "PGPASSWORD": parsed.password or "",
        "PGDATABASE": _database_of(url),
    }


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
        # A unit as well, because the units table is one of the tables the
        # tenant-isolation policies cover. A drill that only seeded the
        # catalogue would compare zero against zero for every table that
        # holds tenant data, and would pass even if the restore had lost
        # every unit.
        await session.execute(
            text(
                "INSERT INTO units (id, org_id, sku_id, serial, received_at, "
                "return_reason_code, order_channel, status) "
                "VALUES (:id, (SELECT id FROM organizations LIMIT 1), "
                "(SELECT id FROM skus LIMIT 1), :serial, now(), "
                "'BUYER_REMORSE', 'ONLINE', 'RECEIVED')"
            ),
            {"id": uuid.uuid4(), "serial": f"DRILL-{variant}"},
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
        # The seed runs as the backup role: the tenant-isolation policies
        # would refuse the insert, and the unit is exactly the row the
        # comparison has to be able to see.
        await _seed(backup_url)

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

    @pytest.mark.asyncio
    async def test_a_lossy_restore_is_caught(
        self, postgres_url: str, backup_url: str, restic_repository: str, tmp_path: Path
    ) -> None:
        """A restore that loses a row has to be noticed.

        The row counts are read with a role that bypasses the tenant
        isolation policies, because the application's role reads no rows at
        all from the tables that hold tenant data when there is no
        organisation in context. Comparing the counts the application's
        role sees would compare zero against zero and pass even if the
        restore had lost every unit.

        This is the test that the drill's own comparison is worth having:
        it takes a backup, restores it, throws a unit away, and insists
        that the comparison notices.
        """
        # The seed runs as the backup role: the tenant-isolation policies
        # would refuse the insert, and the unit is exactly the row the
        # comparison has to be able to see.
        await _seed(backup_url)

        lossy_database = f"secondroute_drill_lossy_{uuid.uuid4().hex[:8]}"
        environment = {
            **os.environ,
            "DATABASE_URL": postgres_url,
            "BACKUP_DATABASE_URL": backup_url,
            "RESTIC_REPOSITORY": restic_repository,
            "RESTIC_PASSWORD": "drill-only-password",
            "DRILL_DATABASE": f"secondroute_drill_{uuid.uuid4().hex[:8]}",
        }

        # Take the backup the lossy copy is made from.
        backup = subprocess.run(
            ["bash", str(SCRIPTS / "backup.sh")],
            env=environment,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        assert backup.returncode == 0, f"The backup failed:\n{backup.stdout}{backup.stderr}"

        # Restore it into a fresh database, then lose a unit.
        created = subprocess.run(
            ["createdb", "--maintenance-db", _database_of(postgres_url), lossy_database],
            env=_libpq_environment(postgres_url),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert created.returncode == 0, f"Could not create the database:\n{created.stderr}"

        lossy_url = f"{_without_database(postgres_url)}/{lossy_database}"
        restored = subprocess.run(
            ["bash", str(SCRIPTS / "restore.sh")],
            env={
                **environment,
                "DATABASE_URL": lossy_url,
                "BACKUP_DATABASE_URL": f"{_without_database(backup_url)}/{lossy_database}",
            },
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        assert restored.returncode == 0, f"The restore failed:\n{restored.stdout}{restored.stderr}"

        # The unit is there before it is thrown away.
        counted = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "row_counts.py"),
                "--source",
                backup_url,
                "--target",
                f"{_without_database(backup_url)}/{lossy_database}",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert counted.returncode == 0, (
            f"The counts did not match:\n{counted.stdout}{counted.stderr}"
        )

        thrown_away = subprocess.run(
            [
                "psql",
                "--dbname",
                f"{_without_database(backup_url)}/{lossy_database}",
                "--command",
                "DELETE FROM units",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert thrown_away.returncode == 0, f"Could not delete the unit:\n{thrown_away.stderr}"

        # Now the comparison has to notice.
        after = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "row_counts.py"),
                "--source",
                backup_url,
                "--target",
                f"{_without_database(backup_url)}/{lossy_database}",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert after.returncode != 0, "The comparison did not notice the lost unit"
        assert "units" in after.stdout + after.stderr

        subprocess.run(
            ["dropdb", "--if-exists", "--force", lossy_database],
            env=_libpq_environment(postgres_url),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
