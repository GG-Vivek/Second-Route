"""
Component price service (Phase 3 - F3.5, F3.6).

The prices of the parts a returned unit is made of. Two things matter:

* **Provenance.** Every price says where it came from and how much it can be
  trusted. A partner quote and a scaled FRED index are not the same thing.
* **Freshness.** A component price from a year ago is not a component price.
  Anything older than the configured limit is flagged stale, and a stale
  source drags the confidence of any decision that leans on it down.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone, UTC
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.config import settings
from secondroute.core.logging import get_logger
from secondroute.ingest.fred import parse_component_csv
from secondroute.ingest.models import ComponentPrice, TeardownYield

logger = get_logger(__name__)

__all__ = [
    "ComponentPriceView",
    "import_component_prices_csv",
    "is_stale",
    "list_component_prices",
    "upsert_component_price",
]


@dataclass(frozen=True, slots=True)
class ComponentPriceView:
    """A component price, with its freshness and provenance.

    Attributes:
        id: The row id.
        component_type: What the component is.
        price_per_unit: The price.
        unit: The unit the price is quoted in.
        source: Where the price came from.
        as_of: When the price was current.
        confidence_weight: How much the price can be trusted.
        is_stale: Whether the price is older than the freshness limit.
        age_days: How old the price is.
    """

    id: Any
    component_type: str
    price_per_unit: float
    unit: str
    source: str
    as_of: date
    confidence_weight: float
    is_stale: bool
    age_days: int

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of the price."""
        return {
            "id": str(self.id),
            "component_type": self.component_type,
            "price_per_unit": self.price_per_unit,
            "unit": self.unit,
            "source": self.source,
            "as_of": self.as_of.isoformat(),
            "confidence_weight": self.confidence_weight,
            "is_stale": self.is_stale,
            "age_days": self.age_days,
        }


def is_stale(as_of: date, *, today: date | None = None, max_age_days: int | None = None) -> bool:
    """Whether a price is older than the freshness limit.

    Args:
        as_of: The date the price was current.
        today: The reference date. Defaults to today.
        max_age_days: The limit. Defaults to the configured value.

    Returns:
        True when the price is stale.
    """
    today = today or datetime.now(UTC).date()
    limit = max_age_days if max_age_days is not None else settings.COMPONENT_PRICE_FRESHNESS_DAYS
    return (today - as_of).days > limit


def age_in_days(as_of: date, *, today: date | None = None) -> int:
    """How old a price is, in days."""
    today = today or datetime.now(UTC).date()
    return (today - as_of).days


async def list_component_prices(
    session: AsyncSession,
    *,
    component_type: str | None = None,
    today: date | None = None,
) -> list[ComponentPriceView]:
    """List the component prices, newest first per component.

    Args:
        session: Database session.
        component_type: Restrict to one component.
        today: The reference date for the staleness flag.

    Returns:
        The component prices, each flagged stale or not.
    """
    query = select(ComponentPrice)
    if component_type:
        query = query.where(ComponentPrice.component_type == component_type)
    result = await session.execute(
        query.order_by(ComponentPrice.component_type, ComponentPrice.as_of.desc())
    )
    rows = result.scalars().all()

    views: list[ComponentPriceView] = []
    for row in rows:
        views.append(
            ComponentPriceView(
                id=row.id,
                component_type=row.component_type,
                price_per_unit=row.price_per_unit,
                unit=row.unit,
                source=row.source,
                as_of=row.as_of,
                confidence_weight=row.confidence_weight,
                is_stale=is_stale(row.as_of, today=today),
                age_days=age_in_days(row.as_of, today=today),
            )
        )
    return views


async def upsert_component_price(
    session: AsyncSession,
    *,
    component_type: str,
    price_per_unit: float,
    source: str,
    as_of: date,
    unit: str = "USD",
    confidence_weight: float = 1.0,
) -> ComponentPrice:
    """Create or update a component price.

    Args:
        session: Database session.
        component_type: What the component is.
        price_per_unit: The price.
        source: Where the price came from.
        as_of: When the price was current.
        unit: The unit the price is quoted in.
        confidence_weight: How much the price can be trusted.

    Returns:
        The stored row.
    """
    result = await session.execute(
        select(ComponentPrice).where(
            ComponentPrice.component_type == component_type,
            ComponentPrice.source == source,
            ComponentPrice.as_of == as_of,
        )
    )
    row = result.scalars().first()
    if row is None:
        row = ComponentPrice(
            component_type=component_type,
            price_per_unit=price_per_unit,
            unit=unit,
            source=source,
            as_of=as_of,
            confidence_weight=confidence_weight,
        )
        session.add(row)
    else:
        row.price_per_unit = price_per_unit
        row.unit = unit
        row.confidence_weight = confidence_weight
    await session.flush()
    return row


async def import_component_prices_csv(
    session: AsyncSession,
    content: bytes,
    *,
    source: str = "partner_csv",
) -> tuple[int, list[str]]:
    """Import a partner component price CSV.

    Args:
        session: Database session.
        content: The raw file content.
        source: The source recorded on every imported row.

    Returns:
        A ``(rows_imported, errors)`` tuple.

    Raises:
        ValueError: When the file has no header row.
    """
    rows = parse_component_csv(content)
    imported = 0
    errors: list[str] = []

    for index, row in enumerate(rows, start=2):
        component_type = row.get("component_type", "")
        raw_price = row.get("price_per_unit", "")
        raw_as_of = row.get("as_of", "")

        if not component_type:
            errors.append(f"line {index}: component_type is empty")
            continue
        try:
            price = float(raw_price.replace(",", "").replace("$", ""))
        except ValueError:
            errors.append(f"line {index}: price {raw_price!r} is not a number")
            continue
        if price < 0:
            errors.append(f"line {index}: price must not be negative")
            continue
        try:
            as_of = datetime.strptime(raw_as_of, "%Y-%m-%d").date()
        except ValueError:
            errors.append(f"line {index}: as_of {raw_as_of!r} is not a date")
            continue

        confidence_raw = row.get("confidence_weight", "")
        try:
            confidence = float(confidence_raw) if confidence_raw else 1.0
        except ValueError:
            errors.append(f"line {index}: confidence_weight {confidence_raw!r} is not a number")
            continue

        await upsert_component_price(
            session,
            component_type=component_type,
            price_per_unit=price,
            source=source,
            as_of=as_of,
            unit=row.get("unit") or "USD",
            confidence_weight=confidence,
        )
        imported += 1

    await session.flush()
    logger.info("component_prices_imported", rows=imported, errors=len(errors), source=source)
    return imported, errors


async def list_teardown_yields(
    session: AsyncSession, *, sku_family: str | None = None
) -> list[TeardownYield]:
    """List the teardown yields.

    Args:
        session: Database session.
        sku_family: Restrict to one family. Rows with an empty family apply
            to every family.

    Returns:
        The teardown yield rows.
    """
    result = await session.execute(select(TeardownYield))
    rows = result.scalars().all()
    if sku_family is None:
        return list(rows)
    return [row for row in rows if row.sku_family in ("", sku_family)]


async def upsert_teardown_yield(
    session: AsyncSession,
    *,
    component_type: str,
    sku_family: str,
    yield_ratio: float,
    source: str,
    as_of: date,
    labor_hours: float = 0.0,
) -> TeardownYield:
    """Create or update a teardown yield.

    Args:
        session: Database session.
        component_type: The component.
        sku_family: The family it applies to. Empty means any family.
        yield_ratio: The share that can be recovered.
        source: Where the ratio came from.
        as_of: When the ratio was current.
        labor_hours: The labour the teardown takes.

    Returns:
        The stored row.
    """
    result = await session.execute(
        select(TeardownYield).where(
            TeardownYield.component_type == component_type,
            TeardownYield.sku_family == sku_family,
            TeardownYield.source == source,
            TeardownYield.as_of == as_of,
        )
    )
    row = result.scalars().first()
    if row is None:
        row = TeardownYield(
            component_type=component_type,
            sku_family=sku_family,
            yield_ratio=yield_ratio,
            labor_hours=labor_hours,
            source=source,
            as_of=as_of,
        )
        session.add(row)
    else:
        row.yield_ratio = yield_ratio
        row.labor_hours = labor_hours
    await session.flush()
    return row
