"""
Source health (Phase 3 - F3.9).

Every price, cost, component and demand number comes from somewhere, and
somewhere can go quiet. This module answers three questions:

* When did each source last say something?
* Is what it said fresh enough to trust?
* How many times has it failed?

A stale source is not silently ignored. The engine reduces the confidence of
any decision that leans on it, and the card says which source was stale and
why that matters. A decision made on last month's prices should not look as
sure as one made this morning.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone, UTC
from typing import Any, Final, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.config import settings
from secondroute.core.logging import get_logger
from secondroute.ingest.models import SourceHealth

logger = get_logger(__name__)

__all__ = [
    "FRESH",
    "MISSING",
    "STALE",
    "SourceStatus",
    "SourceHealthView",
    "collect_source_health",
    "record_source_error",
    "record_source_success",
    "stale_sources",
]

#: The source is fresh.
FRESH: Final[str] = "fresh"

#: The source is stale - it has not been updated recently.
STALE: Final[str] = "stale"

#: The source has never been seen.
MISSING: Final[str] = "missing"

#: How old a price source may be before it is considered stale.
DEFAULT_STALE_HOURS: Final[int] = 48


@dataclass(frozen=True, slots=True)
class SourceStatus:
    """The status of one source.

    Attributes:
        source: The source tag.
        kind: What kind of source it is (``price``, ``cost``, ``component``...).
        status: ``fresh``, ``stale`` or ``missing``.
        last_update: When the source last said something.
        age_hours: How long ago that was.
        error_count: How many errors the source has had.
        is_synthetic: Whether the source is synthetic.
        stale_limit_hours: The age at which the source goes stale.
    """

    source: str
    kind: str
    status: str
    last_update: datetime | None
    age_hours: float | None
    error_count: int
    is_synthetic: bool
    stale_limit_hours: int

    @property
    def is_stale(self) -> bool:
        """Whether the source is stale."""
        return self.status == STALE

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of the status."""
        return {
            "source": self.source,
            "kind": self.kind,
            "status": self.status,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "age_hours": round(self.age_hours, 2) if self.age_hours is not None else None,
            "error_count": self.error_count,
            "is_synthetic": self.is_synthetic,
            "stale_limit_hours": self.stale_limit_hours,
        }


#: The name of the view type. Kept as an alias so the module reads well.
SourceHealthView = SourceStatus


async def collect_source_health(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    stale_limit_hours: int = DEFAULT_STALE_HOURS,
) -> list[SourceStatus]:
    """Collect the health of every source the system knows about.

    Args:
        session: Database session.
        now: The reference time. Defaults to now.
        stale_limit_hours: The age at which a source goes stale.

    Returns:
        The status of every source, by kind then name.
    """
    from secondroute.costs.models import CostTable
    from secondroute.ingest.models import ComponentPrice, DemandSignal
    from secondroute.pricing.models import PriceObservation

    now = now or datetime.now(UTC)
    error_rows = (await session.execute(select(SourceHealth))).scalars().all()
    errors_by_source = {row.source: row for row in error_rows}

    statuses: list[SourceStatus] = []

    price_rows = (
        (
            await session.execute(
                select(PriceObservation).order_by(PriceObservation.observed_at.desc())
            )
        )
        .scalars()
        .all()
    )
    latest_price: dict[str, datetime] = {}
    synthetic_price: dict[str, bool] = {}
    for row in price_rows:
        if row.source not in latest_price:
            latest_price[row.source] = row.observed_at
            synthetic_price[row.source] = row.is_synthetic
    for source, last_update in latest_price.items():
        statuses.append(
            _status(
                source=source,
                kind="price",
                last_update=last_update,
                now=now,
                error_count=_error_count(errors_by_source, source),
                is_synthetic=synthetic_price.get(source, False),
                stale_limit_hours=stale_limit_hours,
            )
        )

    cost_rows = (
        (await session.execute(select(CostTable).order_by(CostTable.updated_at.desc())))
        .scalars()
        .all()
    )
    latest_cost: dict[str, datetime] = {}
    for row in cost_rows:
        latest_cost.setdefault(row.source, row.updated_at)
    for source, last_update in latest_cost.items():
        statuses.append(
            _status(
                source=source,
                kind="cost",
                last_update=last_update,
                now=now,
                error_count=_error_count(errors_by_source, source),
                is_synthetic=source.startswith("synthetic"),
                stale_limit_hours=stale_limit_hours,
            )
        )

    component_rows = (
        (await session.execute(select(ComponentPrice).order_by(ComponentPrice.created_at.desc())))
        .scalars()
        .all()
    )
    latest_component: dict[str, datetime] = {}
    for row in component_rows:
        latest_component.setdefault(row.source, row.created_at)
    for source, last_update in latest_component.items():
        statuses.append(
            _status(
                source=source,
                kind="component",
                last_update=last_update,
                now=now,
                error_count=_error_count(errors_by_source, source),
                is_synthetic=source.startswith("synthetic"),
                stale_limit_hours=stale_limit_hours,
            )
        )

    demand_rows = (
        (await session.execute(select(DemandSignal).order_by(DemandSignal.fetched_at.desc())))
        .scalars()
        .all()
    )
    latest_demand: dict[str, datetime] = {}
    for row in demand_rows:
        latest_demand.setdefault(row.source, row.fetched_at)
    for source, last_update in latest_demand.items():
        statuses.append(
            _status(
                source=source,
                kind="demand",
                last_update=last_update,
                now=now,
                error_count=_error_count(errors_by_source, source),
                is_synthetic=False,
                stale_limit_hours=stale_limit_hours,
            )
        )

    statuses.sort(key=lambda item: (item.kind, item.source))
    return statuses


def _error_count(errors_by_source: dict[str, SourceHealth], source: str) -> int:
    """The error count of a source."""
    row = errors_by_source.get(source)
    return row.error_count if row is not None else 0


def _as_aware(value: datetime | None) -> datetime | None:
    """Make a stored timestamp timezone-aware.

    The database stores naive UTC timestamps, so they are tagged as UTC here
    before they are compared with the current time.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _status(
    *,
    source: str,
    kind: str,
    last_update: datetime | None,
    now: datetime,
    error_count: int,
    is_synthetic: bool,
    stale_limit_hours: int,
) -> SourceStatus:
    """Build the status of one source."""
    last_update = _as_aware(last_update)
    if last_update is None:
        return SourceStatus(
            source=source,
            kind=kind,
            status=MISSING,
            last_update=None,
            age_hours=None,
            error_count=error_count,
            is_synthetic=is_synthetic,
            stale_limit_hours=stale_limit_hours,
        )

    age_hours = (now - last_update).total_seconds() / 3600.0
    status = STALE if age_hours > stale_limit_hours else FRESH

    return SourceStatus(
        source=source,
        kind=kind,
        status=status,
        last_update=last_update,
        age_hours=age_hours,
        error_count=error_count,
        is_synthetic=is_synthetic,
        stale_limit_hours=stale_limit_hours,
    )


def stale_sources(statuses: Sequence[SourceStatus]) -> set[str]:
    """The names of the stale sources.

    Args:
        statuses: The collected statuses.

    Returns:
        The set of stale source names.
    """
    return {status.source for status in statuses if status.is_stale}


async def record_source_error(session: AsyncSession, source: str, message: str) -> SourceHealth:
    """Record that a source failed.

    Args:
        session: Database session.
        source: The source tag.
        message: What went wrong.

    Returns:
        The health row.
    """
    row = await _get_or_create_health(session, source)
    row.error_count += 1
    row.last_error_at = datetime.now(UTC)
    row.message = message[:2000]
    await session.flush()
    logger.warning("source_error", source=source, errors=row.error_count)
    return row


async def record_source_success(session: AsyncSession, source: str) -> SourceHealth:
    """Record that a source answered.

    Args:
        session: Database session.
        source: The source tag.

    Returns:
        The health row.
    """
    row = await _get_or_create_health(session, source)
    row.last_success_at = datetime.now(UTC)
    await session.flush()
    return row


async def _get_or_create_health(session: AsyncSession, source: str) -> SourceHealth:
    """Get or create the health row of a source."""
    result = await session.execute(select(SourceHealth).where(SourceHealth.source == source))
    row = result.scalars().first()
    if row is None:
        row = SourceHealth(source=source)
        session.add(row)
        await session.flush()
    return row
