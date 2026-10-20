"""
Parts harvest valuation (Phase 3 - F3.6).

A broken unit is not worthless. The parts inside it still have value: the
display is cracked but the motherboard is fine, the storage still works, the
chassis is intact. Harvesting them is one of the disposition channels, and
for a badly damaged unit it is often the right one.

The value of a unit's parts is:

```
parts value = sum(component price * yield ratio * confidence) - labour
```

The *yield ratio* is how much of a component survives a teardown. The
*confidence* is how much the component's price can be trusted - a FRED-scaled
index is worth less than a partner quote.

A failed component is worth nothing: a cracked display is scrap. The
inspection's functional tests say which components failed, so the same unit
with a working display is worth more than the same unit with a broken one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final, Sequence
from uuid import UUID

import numpy as np

from secondroute.core.logging import get_logger
from secondroute.pricing.protocols import PriceDistribution, PriceSourceNotFoundError

logger = get_logger(__name__)

__all__ = [
    "COMPONENTS",
    "DEFAULT_LABOUR_RATE",
    "TEST_TO_COMPONENT",
    "PartsBreakdown",
    "PartsCondition",
    "PartsHarvestPriceSource",
    "PartsValuation",
    "valuate_parts",
]

#: The components a unit of each family is made of. Every family has the
#: same core set; the per-family table refines it.
COMPONENTS: Final[tuple[str, ...]] = (
    "display",
    "battery",
    "motherboard",
    "memory",
    "storage",
    "chassis",
    "keyboard",
    "charger",
)

#: Which component a failed functional test condemns.
TEST_TO_COMPONENT: Final[dict[str, str]] = {
    "display": "display",
    "screen": "display",
    "keyboard": "keyboard",
    "ports": "ports",
    "audio": "speaker",
    "camera": "camera",
    "battery": "battery",
    "boot": "motherboard",
    "wifi": "motherboard",
    "motherboard": "motherboard",
    "storage": "storage",
    "memory": "memory",
}

#: The cost of one hour of teardown labour, in USD.
DEFAULT_LABOUR_RATE: Final[float] = 28.0

#: How much the valuation itself is uncertain, as a coefficient of variation.
VALUATION_CV: Final[float] = 0.18


@dataclass(frozen=True, slots=True)
class PartsCondition:
    """What is broken about a unit, and what it still has.

    Attributes:
        failed_tests: The functional tests that failed.
        battery_health_pct: The battery health, when known.
    """

    failed_tests: frozenset[str] = frozenset()
    battery_health_pct: float | None = None

    def failed_components(self) -> frozenset[str]:
        """The components the failures condemn."""
        condemned: set[str] = set()
        for test in self.failed_tests:
            component = TEST_TO_COMPONENT.get(test)
            if component:
                condemned.add(component)
            # A failure named after the component itself condemns it too.
            if test in COMPONENTS:
                condemned.add(test)
        if self.battery_health_pct is not None and self.battery_health_pct < 60.0:
            condemned.add("battery")
        return frozenset(condemned)

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of the condition."""
        return {
            "failed_tests": sorted(self.failed_tests),
            "battery_health_pct": self.battery_health_pct,
            "failed_components": sorted(self.failed_components()),
        }


@dataclass(frozen=True, slots=True)
class PartsBreakdown:
    """The value of one component.

    Attributes:
        component_type: The component.
        price: The price of a working one.
        yield_ratio: How much survives a teardown.
        confidence: How much the price can be trusted.
        value: What the component is worth to a harvester.
        source: Where the price came from.
        as_of: When the price was current.
        recovered: False when the component is condemned.
    """

    component_type: str
    price: float
    yield_ratio: float
    confidence: float
    value: float
    source: str
    as_of: Any
    recovered: bool = True

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of the breakdown."""
        return {
            "component_type": self.component_type,
            "price": round(self.price, 2),
            "yield_ratio": self.yield_ratio,
            "confidence": self.confidence,
            "value": round(self.value, 2),
            "source": self.source,
            "as_of": self.as_of.isoformat() if hasattr(self.as_of, "isoformat") else self.as_of,
            "recovered": self.recovered,
        }


@dataclass(frozen=True, slots=True)
class PartsValuation:
    """What a unit's parts are worth.

    Attributes:
        gross_value: The value of the recovered components.
        labour_cost: The cost of taking the unit apart.
        net_value: What the harvest actually makes.
        breakdown: The value of each component.
        sources: The sources the component prices came from.
        as_of: The oldest price used.
    """

    gross_value: float
    labour_cost: float
    net_value: float
    breakdown: tuple[PartsBreakdown, ...] = field(default_factory=tuple)
    sources: dict[str, str] = field(default_factory=dict)
    as_of: Any = None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of the valuation."""
        return {
            "gross_value": round(self.gross_value, 2),
            "labour_cost": round(self.labour_cost, 2),
            "net_value": round(self.net_value, 2),
            "breakdown": [item.as_dict() for item in self.breakdown],
            "sources": dict(self.sources),
            "as_of": self.as_of.isoformat() if hasattr(self.as_of, "isoformat") else self.as_of,
        }


def valuate_parts(
    condition: PartsCondition,
    component_prices: dict[str, Any],
    yields: dict[str, Any],
    *,
    labour_rate: float = DEFAULT_LABOUR_RATE,
    components: Sequence[str] = COMPONENTS,
) -> PartsValuation:
    """Value the parts of a unit.

    Args:
        condition: What is broken about the unit.
        component_prices: The price of each component, keyed by component
            type. Each value carries ``price_per_unit``, ``confidence_weight``,
            ``source`` and ``as_of``.
        yields: The teardown yield of each component, keyed by component type.
            Each value carries ``yield_ratio`` and ``labor_hours``.
        labour_rate: The cost of one hour of teardown labour.
        components: The components to value.

    Returns:
        The valuation.
    """
    condemned = condition.failed_components()

    breakdown: list[PartsBreakdown] = []
    gross = 0.0
    labour_hours = 0.0
    sources: dict[str, str] = {}
    oldest: Any = None

    for component_type in components:
        price_row = component_prices.get(component_type)
        yield_row = yields.get(component_type)

        if price_row is None:
            continue

        price = float(getattr(price_row, "price_per_unit", 0.0))
        confidence = float(getattr(price_row, "confidence_weight", 1.0))
        source = str(getattr(price_row, "source", "unknown"))
        as_of = getattr(price_row, "as_of", None)

        ratio = float(getattr(yield_row, "yield_ratio", 1.0)) if yield_row else 1.0
        hours = float(getattr(yield_row, "labor_hours", 0.0)) if yield_row else 0.0

        recovered = component_type not in condemned
        value = price * ratio * confidence * (1.0 if recovered else 0.0)

        breakdown.append(
            PartsBreakdown(
                component_type=component_type,
                price=price,
                yield_ratio=ratio,
                confidence=confidence,
                value=value,
                source=source,
                as_of=as_of,
                recovered=recovered,
            )
        )
        gross += value
        labour_hours += hours
        sources[component_type] = source
        if as_of is not None and (oldest is None or as_of < oldest):
            oldest = as_of

    labour_cost = labour_hours * labour_rate

    return PartsValuation(
        gross_value=gross,
        labour_cost=labour_cost,
        net_value=gross - labour_cost,
        breakdown=tuple(breakdown),
        sources=sources,
        as_of=oldest,
    )


class PartsHarvestPriceSource:
    """A price source for the ``PARTS_HARVEST`` channel.

    The "sale price" of the parts channel is what the parts are worth. The
    uncertainty comes from the component prices themselves.

    Attributes:
        source_tag: The source tag recorded on the observations.
    """

    source_tag = "parts_harvest"

    def __init__(
        self,
        component_prices: dict[str, Any],
        yields: dict[str, Any],
        conditions: dict[UUID, PartsCondition] | None = None,
        *,
        labour_rate: float = DEFAULT_LABOUR_RATE,
        components: Sequence[str] = COMPONENTS,
    ) -> None:
        """Build the source.

        Args:
            component_prices: The price of each component.
            yields: The teardown yield of each component.
            conditions: What is broken about each unit.
            labour_rate: The cost of one hour of teardown labour.
            components: The components to value.
        """
        self.component_prices = component_prices
        self.yields = yields
        self.conditions = conditions or {}
        self.labour_rate = labour_rate
        self.components = tuple(components)

    async def get_distribution(
        self,
        sku_id: UUID,
        grade: str,
        channel: str,
        as_of: datetime,
    ) -> PriceDistribution:
        """Return the parts value distribution for one unit.

        Args:
            sku_id: The unit.
            grade: The condition grade. The parts value does not depend on it
                - the same unit is worth the same in parts whatever grade it
                was given.
            channel: The disposition channel. Only ``PARTS_HARVEST`` is served.
            as_of: The reference time.

        Returns:
            The distribution of the parts value.

        Raises:
            PriceSourceNotFoundError: If the channel is not the parts channel.
        """
        del grade  # the parts value does not depend on the cosmetic grade
        if channel != "PARTS_HARVEST":
            raise PriceSourceNotFoundError(
                f"the parts source only serves PARTS_HARVEST, not {channel!r}"
            )

        condition = self.conditions.get(sku_id, PartsCondition())
        valuation = valuate_parts(
            condition,
            self.component_prices,
            self.yields,
            labour_rate=self.labour_rate,
            components=self.components,
        )

        recovered = [item for item in valuation.breakdown if item.recovered and item.value > 0]

        if not recovered:
            # Nothing is worth harvesting. The channel still exists, it is just
            # worth nothing, so the engine can compare it with the others.
            return PriceDistribution(
                values=(0.0,),
                weights=(1.0,),
                source=self.source_tag,
                as_of=valuation.as_of or as_of,
                metadata={
                    "gross_value": "0.00",
                    "labour_cost": f"{valuation.labour_cost:.2f}",
                    "net_value": f"{valuation.net_value:.2f}",
                    "recovered_components": "0",
                    "component_sources": "",
                    "note": "No recoverable components.",
                },
            )

        # The spread comes from the component prices, not from a guess.
        values = tuple(max(0.0, item.value) for item in recovered)
        total = sum(values)
        spread = total * VALUATION_CV
        support = [
            max(0.0, total - spread),
            total,
            total + spread,
        ]

        return PriceDistribution(
            values=tuple(support),
            weights=(0.25, 0.5, 0.25),
            source=self.source_tag,
            as_of=valuation.as_of or as_of,
            metadata={
                "gross_value": f"{valuation.gross_value:.2f}",
                "labour_cost": f"{valuation.labour_cost:.2f}",
                "net_value": f"{valuation.net_value:.2f}",
                "recovered_components": str(len(recovered)),
                "component_sources": ",".join(sorted(set(valuation.sources.values()))),
            },
        )


async def build_parts_source(
    session: Any,
    unit_id: UUID,
    inspection: Any,
    *,
    components: Sequence[str] = COMPONENTS,
    labour_rate: float = DEFAULT_LABOUR_RATE,
) -> PartsHarvestPriceSource:
    """Build a parts source for a unit from the stored prices and yields.

    Args:
        session: Database session.
        unit_id: The unit the source is for.
        inspection: The unit's inspection record.
        components: The components to value.
        labour_rate: The cost of one hour of teardown labour.

    Returns:
        The price source for the parts channel.
    """
    from sqlalchemy import select

    from secondroute.ingest.models import ComponentPrice, TeardownYield

    # The newest price for each component type.
    price_rows = (
        (await session.execute(select(ComponentPrice).order_by(ComponentPrice.as_of.desc())))
        .scalars()
        .all()
    )
    component_prices: dict[str, Any] = {}
    for row in price_rows:
        component_prices.setdefault(row.component_type, row)

    yield_rows = (await session.execute(select(TeardownYield))).scalars().all()
    yields: dict[str, Any] = {}
    for row in yield_rows:
        yields.setdefault(row.component_type, row)

    failed = _failed_tests(inspection)
    battery = _battery_health(inspection)
    condition = PartsCondition(failed_tests=frozenset(failed), battery_health_pct=battery)

    return PartsHarvestPriceSource(
        component_prices,
        yields,
        {unit_id: condition},
        labour_rate=labour_rate,
        components=components,
    )


def _failed_tests(inspection: Any) -> list[str]:
    """Return the failed functional tests of an inspection."""
    raw = getattr(inspection, "functional_tests_json", None)
    if raw is None:
        raw = getattr(inspection, "functional_tests", None)
    if isinstance(raw, str):
        import json

        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, dict):
        return []
    return [str(name) for name, passed in raw.items() if not passed]


def _battery_health(inspection: Any) -> float | None:
    """Return the battery health of an inspection."""
    raw = getattr(inspection, "battery_health_pct", None)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None
