"""
Cost book service (Phase 2 - F2.4).

Loads the ``cost_tables`` rows into an immutable lookup the decision engine can
read without hitting the database inside the Monte Carlo loop. Every value
keeps its ``source`` and ``as_of`` so the decision card can display where the
number came from.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.logging import get_logger
from secondroute.costs.defaults import default_cost_seeds
from secondroute.costs.models import CostTable

logger = get_logger(__name__)

__all__ = ["CostBook", "CostBookEntry", "load_cost_book", "seed_default_costs"]


@dataclass(frozen=True, slots=True)
class CostBookEntry:
    """One cost value together with its provenance."""

    kind: str
    key: str
    value: float
    source: str
    as_of: date


@dataclass(frozen=True, slots=True)
class CostBook:
    """Immutable snapshot of the cost tables.

    Attributes:
        entries: All loaded entries, keyed by ``(kind, key)``.
    """

    entries: dict[tuple[str, str], CostBookEntry] = field(default_factory=dict)

    def get(self, kind: str, key: str, default: float = 0.0) -> float:
        """Return the value for ``(kind, key)`` or ``default`` when absent."""
        entry = self.entries.get((kind, key))
        return entry.value if entry is not None else default

    def has(self, kind: str, key: str) -> bool:
        """Return whether ``(kind, key)`` is present."""
        return (kind, key) in self.entries

    def entry(self, kind: str, key: str) -> CostBookEntry | None:
        """Return the full entry for ``(kind, key)``."""
        return self.entries.get((kind, key))

    def source_for(self, kind: str, key: str) -> str | None:
        """Return the source of ``(kind, key)`` when known."""
        entry = self.entries.get((kind, key))
        return entry.source if entry is not None else None

    def as_of_for(self, kind: str, key: str) -> date | None:
        """Return the as-of date of ``(kind, key)`` when known."""
        entry = self.entries.get((kind, key))
        return entry.as_of if entry is not None else None

    def kinds(self) -> list[str]:
        """Return the distinct kinds present in the book."""
        return sorted({kind for kind, _ in self.entries})

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of the book."""
        return {
            f"{kind}:{key}": {
                "value": entry.value,
                "source": entry.source,
                "as_of": entry.as_of.isoformat(),
            }
            for (kind, key), entry in sorted(self.entries.items())
        }

    def with_override(self, kind: str, key: str, value: float) -> CostBook:
        """Return a copy of the book with one value replaced.

        Used by the flip-condition sensitivity search so a perturbed cost can
        be evaluated without touching the database.

        Args:
            kind: Cost kind to override.
            key: Cost key to override.
            value: New value.

        Returns:
            A new cost book with the override applied.
        """
        entries = dict(self.entries)
        existing = entries.get((kind, key))
        entries[(kind, key)] = CostBookEntry(
            kind=kind,
            key=key,
            value=float(value),
            source=existing.source if existing else "sensitivity_override",
            as_of=existing.as_of if existing else date.today(),
        )
        return CostBook(entries=entries)


async def load_cost_book(
    session: AsyncSession,
    org_id: Any | None = None,
    *,
    include_defaults: bool = True,
) -> CostBook:
    """Load every cost row into a :class:`CostBook`.

    The default costs are always the floor. Rows stored in ``cost_tables``
    override them, so an operator can adjust a single value without having to
    seed the whole table first.

    Args:
        session: Database session.
        org_id: Restrict to one organisation's overrides when given.
        include_defaults: Whether the built-in defaults are included as the
            floor.

    Returns:
        The loaded cost book.
    """
    entries: dict[tuple[str, str], CostBookEntry] = {}

    if include_defaults:
        for seed in default_cost_seeds():
            entries[(seed.kind, seed.key)] = CostBookEntry(
                kind=seed.kind,
                key=seed.key,
                value=seed.value,
                source=seed.source,
                as_of=seed.as_of,
            )

    query = select(CostTable)
    if org_id is not None:
        query = query.where(CostTable.org_id == org_id)
    result = await session.execute(query)
    rows = result.scalars().all()

    for row in rows:
        entries[(row.kind, row.key)] = CostBookEntry(
            kind=row.kind,
            key=row.key,
            value=float(row.value),
            source=row.source,
            as_of=row.as_of,
        )
    return CostBook(entries=entries)


async def seed_default_costs(session: AsyncSession, org_id: Any | None = None) -> int:
    """Insert the default cost rows for an organisation.

    The rows belong to the organisation, because the cost book is
    something an organisation can adjust: the defaults are the floor and
    a row in the table overrides one value for one organisation. A row
    with no organisation would be shared, and the tenant-isolation policy
    refuses those, so the endpoint that seeds the costs could not write
    anything at all.

    The operation is idempotent.

    Args:
        session: Database session.
        org_id: The organisation the rows belong to. Nothing is written
            without one.

    Returns:
        The number of rows inserted.
    """
    if org_id is None:
        logger.info("cost_tables_not_seeded_without_an_organisation")
        return 0

    existing = await session.execute(
        select(CostTable.id).where(CostTable.org_id == org_id).limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        logger.info("cost_tables_already_seeded", org_id=str(org_id))
        return 0

    inserted = 0
    for seed in default_cost_seeds():
        session.add(
            CostTable(
                org_id=org_id,
                kind=seed.kind,
                key=seed.key,
                value=seed.value,
                source=seed.source,
                as_of=seed.as_of,
            )
        )
        inserted += 1

    await session.flush()
    logger.info("default_costs_seeded", rows=inserted, org_id=str(org_id))
    return inserted
