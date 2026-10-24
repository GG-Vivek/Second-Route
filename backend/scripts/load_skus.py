#!/usr/bin/env python
"""
SKU catalog seed loader.

Loads SKU data from CSV into the database idempotently.

The CSV is the catalogue. A row that already exists is brought back to what
the CSV says -- so a change of category, summary or source reaches the
database instead of being skipped -- and a row the CSV dropped is removed,
unless something still needs it (a unit, a serial prefix, a price
observation), in which case it stays and is counted as retained.

Each row must have source and as_of columns. Running twice changes nothing.
"""

from __future__ import annotations

import asyncio
import csv
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from secondroute.core.config import settings
from secondroute.core.db import close_db, get_session_context, init_db
from secondroute.identity.models import SKU, SerialPrefix
from secondroute.intake.models import Unit
from secondroute.pricing.models import PriceObservation

# The columns that say which product a row is. Everything else about a row
# (the specs, the source, the as_of) can be edited; these cannot, because a
# unit, a serial prefix or a price observation points at the product.
IDENTITY_FIELDS = (
    "family",
    "model_name",
    "year",
    "storage_gb",
    "ram_gb",
    "color",
    "region",
)


@dataclass(frozen=True)
class LoadResult:
    """What one pass of the loader did."""

    created: int
    updated: int
    skipped: int
    removed: int
    retained: int


def _row_key(row: dict[str, str]) -> tuple[str, ...]:
    """Which product this catalogue row describes."""
    return tuple(row[field] for field in IDENTITY_FIELDS)


def _sku_key(sku: SKU) -> tuple[str, ...]:
    """Which product this row in the database describes."""
    return tuple(str(getattr(sku, field) or "") for field in IDENTITY_FIELDS)


async def _is_referenced(session: AsyncSession, sku_id: UUID) -> bool:
    """Whether anything this session can see points at this product.

    A unit is the record of something that came back, a serial prefix maps
    serials onto it, a price observation is evidence about it. Removing the
    product out from under them would leave them describing nothing.

    The tenant policies hide other organisations' rows, so this is a first
    attempt rather than the last word. ``_remove_retired`` is the last word.
    """
    for model in (Unit, SerialPrefix, PriceObservation):
        count = await session.scalar(
            select(func.count()).select_from(model).where(model.sku_id == sku_id)
        )
        if count:
            return True
    return False


async def _remove_retired(session: AsyncSession, sku: SKU) -> bool:
    """Remove one product the catalogue has retired.

    Returns whether it went. The savepoint turns the database's own refusal
    into an answer: a foreign key violation means something still points at
    the product -- often another organisation's unit, which the tenant
    policies keep this session from seeing in ``_is_referenced``.
    """
    try:
        async with session.begin_nested():
            await session.delete(sku)
            await session.flush()
    except IntegrityError:
        return False
    return True


async def load_skus_from_csv(csv_path: Path, session: AsyncSession) -> LoadResult:
    """
    Load SKUs from CSV file idempotently.

    The CSV is the whole catalogue: rows are created when they are missing,
    refreshed when the CSV has changed its mind about one, and removed when
    the CSV no longer sells them and nothing needs them any more.

    Args:
        csv_path: Path to the CSV file
        session: Database session

    Returns:
        A LoadResult counting what happened.
    """
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    wanted = {_row_key(row): row for row in rows}
    existing = {_sku_key(sku): sku for sku in (await session.execute(select(SKU))).scalars().all()}

    created = 0
    updated = 0
    skipped = 0
    removed = 0
    retained = 0

    for key, row in wanted.items():
        specs = json.loads(row["specs_json"])
        source = row["source"]
        as_of = date.fromisoformat(row["as_of"])

        sku = existing.get(key)
        if sku is None:
            session.add(
                SKU(
                    family=row["family"],
                    model_name=row["model_name"],
                    year=row["year"],
                    storage_gb=row["storage_gb"],
                    ram_gb=row["ram_gb"],
                    color=row["color"],
                    region=row["region"],
                    specs_json=specs,
                    source=source,
                    as_of=as_of,
                )
            )
            created += 1
            continue

        if sku.specs_json == specs and sku.source == source and sku.as_of == as_of:
            skipped += 1
            continue

        sku.specs_json = specs
        sku.source = source
        sku.as_of = as_of
        updated += 1

    # The catalogue has stopped selling these. They go, unless something
    # still points at them, in which case they stay and are counted.
    for key, sku in existing.items():
        if key in wanted:
            continue
        if await _is_referenced(session, sku.id) or not await _remove_retired(session, sku):
            retained += 1
            continue
        removed += 1

    await session.flush()
    return LoadResult(
        created=created,
        updated=updated,
        skipped=skipped,
        removed=removed,
        retained=retained,
    )


async def main() -> None:
    """Main entry point."""
    # CSV is at project root /data/seeds/skus.csv
    csv_path = Path(__file__).parent.parent.parent / "data" / "seeds" / "skus.csv"

    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}")
        sys.exit(1)

    print(f"Loading SKUs from {csv_path}...")
    print(f"Database: {settings.database_url_sync}")

    # The session factory is a module-level global, so the engine has to
    # be set up before a session can be opened. Without this the script
    # fails with "The database is not initialised".
    await init_db()
    try:
        async with get_session_context() as session:
            result = await load_skus_from_csv(csv_path, session)
    finally:
        await close_db()

    print(
        f"Done! Created: {result.created}, Updated: {result.updated}, "
        f"Skipped (already correct): {result.skipped}, "
        f"Removed: {result.removed}, Kept (still in use): {result.retained}"
    )


if __name__ == "__main__":
    asyncio.run(main())
