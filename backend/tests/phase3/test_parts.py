"""
Tests for the parts harvest valuation (F3.6).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import uuid4

import pytest

from secondroute.decision.parts import (
    COMPONENTS,
    DEFAULT_LABOUR_RATE,
    PartsCondition,
    PartsHarvestPriceSource,
    valuate_parts,
)


@dataclass(frozen=True)
class FakePrice:
    """A stand-in for a component price row."""

    price_per_unit: float
    confidence_weight: float
    source: str
    as_of: date


@dataclass(frozen=True)
class FakeYield:
    """A stand-in for a teardown yield row."""

    yield_ratio: float
    labor_hours: float


def make_prices(**overrides: float) -> dict[str, FakePrice]:
    """Build a component price table."""
    base = {
        "display": 320.0,
        "battery": 85.0,
        "motherboard": 410.0,
        "memory": 95.0,
        "storage": 110.0,
        "chassis": 45.0,
        "keyboard": 70.0,
        "charger": 35.0,
    }
    base.update(overrides)
    return {
        name: FakePrice(
            price_per_unit=price,
            confidence_weight=1.0,
            source="partner_quote",
            as_of=date(2025, 5, 1),
        )
        for name, price in base.items()
    }


def make_yields(**overrides: float) -> dict[str, FakeYield]:
    """Build a teardown yield table."""
    base = {
        "display": 0.75,
        "battery": 0.85,
        "motherboard": 0.90,
        "memory": 0.95,
        "storage": 0.90,
        "chassis": 0.80,
        "keyboard": 0.70,
        "charger": 0.95,
    }
    base.update(overrides)
    return {name: FakeYield(yield_ratio=ratio, labor_hours=0.25) for name, ratio in base.items()}


class TestFailedComponents:
    """A failed test condemns a component."""

    def test_a_failed_display_condemns_the_display(self) -> None:
        """The display test condemns the display."""
        condition = PartsCondition(failed_tests=frozenset({"display"}))
        assert "display" in condition.failed_components()

    def test_a_failed_keyboard_condemns_the_keyboard(self) -> None:
        """The keyboard test condemns the keyboard."""
        condition = PartsCondition(failed_tests=frozenset({"keyboard"}))
        assert "keyboard" in condition.failed_components()

    def test_a_healthy_unit_condemns_nothing(self) -> None:
        """No failures means no condemned components."""
        condition = PartsCondition(failed_tests=frozenset())
        assert condition.failed_components() == frozenset()

    def test_a_worn_battery_condemns_the_battery(self) -> None:
        """A battery below 60% is scrap."""
        condition = PartsCondition(battery_health_pct=45.0)
        assert "battery" in condition.failed_components()

    def test_a_healthy_battery_is_fine(self) -> None:
        """A battery above 60% is not condemned."""
        condition = PartsCondition(battery_health_pct=85.0)
        assert "battery" not in condition.failed_components()


class TestValuation:
    """The parts valuation."""

    def test_an_intact_unit_is_worth_more_than_a_broken_one(self) -> None:
        """The acceptance criterion: a broken display is worth less."""
        prices = make_prices()
        yields = make_yields()

        intact = valuate_parts(PartsCondition(failed_tests=frozenset()), prices, yields)
        broken = valuate_parts(PartsCondition(failed_tests=frozenset({"display"})), prices, yields)

        assert broken.net_value < intact.net_value
        assert intact.gross_value - broken.gross_value == pytest.approx(320.0 * 0.75)

    def test_the_broken_component_contributes_nothing(self) -> None:
        """A condemned component has no value."""
        prices = make_prices()
        yields = make_yields()
        valuation = valuate_parts(
            PartsCondition(failed_tests=frozenset({"display"})), prices, yields
        )
        display = next(item for item in valuation.breakdown if item.component_type == "display")
        assert display.value == pytest.approx(0.0)
        assert display.recovered is False

    def test_the_yield_ratio_scales_the_value(self) -> None:
        """A higher yield means a higher value."""
        low = valuate_parts(PartsCondition(), make_prices(), make_yields(display=0.5))
        high = valuate_parts(PartsCondition(), make_prices(), make_yields(display=0.9))
        assert high.gross_value > low.gross_value

    def test_the_confidence_scales_the_value(self) -> None:
        """A less trusted price is worth less."""
        prices = make_prices()
        trusted = valuate_parts(PartsCondition(), prices, make_yields())
        discounted = {
            name: FakePrice(
                price_per_unit=price.price_per_unit,
                confidence_weight=0.5,
                source=price.source,
                as_of=price.as_of,
            )
            for name, price in prices.items()
        }
        less_trusted = valuate_parts(PartsCondition(), discounted, make_yields())
        assert less_trusted.gross_value < trusted.gross_value

    def test_labour_is_subtracted(self) -> None:
        """The teardown labour comes out of the gross value."""
        prices = make_prices()
        yields = make_yields()
        valuation = valuate_parts(PartsCondition(), prices, yields)
        assert valuation.net_value == pytest.approx(valuation.gross_value - valuation.labour_cost)
        assert valuation.labour_cost > 0

    def test_a_high_labour_rate_costs_more(self) -> None:
        """A higher labour rate costs more."""
        prices = make_prices()
        yields = make_yields()
        cheap = valuate_parts(PartsCondition(), prices, yields, labour_rate=10.0)
        expensive = valuate_parts(PartsCondition(), prices, yields, labour_rate=50.0)
        assert expensive.labour_cost > cheap.labour_cost
        assert expensive.net_value < cheap.net_value

    def test_the_sources_are_recorded(self) -> None:
        """Every component's source is recorded, so the card can show it."""
        prices = make_prices()
        prices["display"] = FakePrice(
            price_per_unit=320.0,
            confidence_weight=0.4,
            source="fred:PCU334433334433",
            as_of=date(2025, 1, 1),
        )
        valuation = valuate_parts(PartsCondition(), prices, make_yields())
        assert valuation.sources["display"] == "fred:PCU334433334433"
        assert valuation.sources["battery"] == "partner_quote"
        assert valuation.as_of == date(2025, 1, 1)

    def test_an_unknown_component_is_skipped(self) -> None:
        """A component with no price is not valued."""
        prices = make_prices()
        del prices["display"]
        valuation = valuate_parts(PartsCondition(), prices, make_yields())
        assert all(item.component_type != "display" for item in valuation.breakdown)

    def test_the_valuation_serialises(self) -> None:
        """The valuation can be serialised for the card."""
        valuation = valuate_parts(PartsCondition(), make_prices(), make_yields())
        payload = valuation.as_dict()
        assert payload["gross_value"] > 0
        assert payload["breakdown"]
        assert payload["sources"]


class TestPartsPriceSource:
    """The parts channel price source."""

    @pytest.mark.asyncio
    async def test_it_only_serves_the_parts_channel(self) -> None:
        """Another channel is an error, not a silent fallback."""
        source = PartsHarvestPriceSource(make_prices(), make_yields())
        with pytest.raises(Exception, match="only serves PARTS_HARVEST"):
            await source.get_distribution(
                uuid4(), "B", "RESELL_OPEN_BOX", __import__("datetime").datetime.now()
            )

    @pytest.mark.asyncio
    async def test_it_returns_a_distribution(self) -> None:
        """The parts value comes back as a distribution."""
        source = PartsHarvestPriceSource(make_prices(), make_yields())
        distribution = await source.get_distribution(
            uuid4(), "B", "PARTS_HARVEST", __import__("datetime").datetime.now()
        )
        assert distribution.sample_count == 3
        assert distribution.mean > 0
        assert distribution.source == "parts_harvest"

    @pytest.mark.asyncio
    async def test_the_metadata_records_the_sources(self) -> None:
        """The card can show where the component prices came from."""
        source = PartsHarvestPriceSource(make_prices(), make_yields())
        distribution = await source.get_distribution(
            uuid4(), "B", "PARTS_HARVEST", __import__("datetime").datetime.now()
        )
        assert "partner_quote" in distribution.metadata["component_sources"]
        assert float(distribution.metadata["net_value"]) > 0

    @pytest.mark.asyncio
    async def test_a_broken_unit_is_worth_less(self) -> None:
        """The acceptance criterion at the source level."""
        sku_id = uuid4()
        intact_source = PartsHarvestPriceSource(make_prices(), make_yields())
        broken_source = PartsHarvestPriceSource(
            make_prices(),
            make_yields(),
            {sku_id: PartsCondition(failed_tests=frozenset({"display"}))},
        )
        intact = await intact_source.get_distribution(
            sku_id, "B", "PARTS_HARVEST", __import__("datetime").datetime.now()
        )
        broken = await broken_source.get_distribution(
            sku_id, "B", "PARTS_HARVEST", __import__("datetime").datetime.now()
        )
        assert broken.mean < intact.mean

    @pytest.mark.asyncio
    async def test_a_unit_with_nothing_left_is_worth_nothing(self) -> None:
        """When every component is condemned the channel is worth nothing.

        It is not an error: the channel still exists, it just is not worth
        doing, and the engine has to be able to say so.
        """
        sku_id = uuid4()
        source = PartsHarvestPriceSource(
            make_prices(),
            make_yields(),
            {sku_id: PartsCondition(failed_tests=frozenset(COMPONENTS))},
        )
        distribution = await source.get_distribution(
            sku_id, "B", "PARTS_HARVEST", __import__("datetime").datetime.now()
        )
        assert distribution.mean == pytest.approx(0.0)
        assert distribution.metadata["recovered_components"] == "0"
