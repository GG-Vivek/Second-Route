#!/usr/bin/env python
"""
SKU catalog seed loader.

Loads SKU data from CSV into the database idempotently.
Each row must have source and as_of columns.
Running twice changes nothing.
"""

import csv
import sys
from datetime import date
from pathlib import Path
from uuid import UUID

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from secondroute.core.config import settings
from secondroute.core.db import Base, close_db, engine, get_session_context, init_db
from secondroute.identity.models import SKU, SerialPrefix


async def load_skus_from_csv(csv_path: Path, session: AsyncSession) -> tuple[int, int]:
    """
    Load SKUs from CSV file idempotently.

    Args:
        csv_path: Path to the CSV file
        session: Database session

    Returns:
        Tuple of (created_count, skipped_count)
    """
    created = 0
    skipped = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse specs_json
            import json

            specs = json.loads(row["specs_json"])

            # Check if SKU already exists (by variant)
            existing = await session.execute(
                select(SKU).where(
                    SKU.family == row["family"],
                    SKU.model_name == row["model_name"],
                    SKU.year == row["year"],
                    SKU.storage_gb == row["storage_gb"],
                    SKU.ram_gb == row["ram_gb"],
                    SKU.color == row["color"],
                    SKU.region == row["region"],
                )
            )
            sku = existing.scalar_one_or_none()

            if sku:
                skipped += 1
                continue

            # Create new SKU
            sku = SKU(
                family=row["family"],
                model_name=row["model_name"],
                year=row["year"],
                storage_gb=row["storage_gb"],
                ram_gb=row["ram_gb"],
                color=row["color"],
                region=row["region"],
                specs_json=specs,
                source=row["source"],
                as_of=date.fromisoformat(row["as_of"]),
            )
            session.add(sku)
            created += 1

    await session.flush()
    return created, skipped


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
            created, skipped = await load_skus_from_csv(csv_path, session)
    finally:
        await close_db()

    print(f"Done! Created: {created}, Skipped (already exist): {skipped}")


if __name__ == "__main__":
    asyncio.run(main())
