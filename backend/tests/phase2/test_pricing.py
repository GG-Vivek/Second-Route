"""
Tests for the price source interface (F2.2).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import numpy as np
import pytest

from secondroute.pricing.protocols import (
    PriceDistribution,
    PriceSource,
    PriceSourceNotFoundError,
)
from secondroute.pricing.sources import SyntheticPriceSource
from tests.phase2.decision_fixtures import FixedPriceSource


class TestProtocol:
    """Every adapter must satisfy the protocol."""

    def test_synthetic_source_satisfies_protocol(self) -> None:
        """The synthetic adapter implements the protocol."""
        assert isinstance(SyntheticPriceSource(), PriceSource)

    def test_fixed_source_satisfies_protocol(self) -> None:
        """A test double implements the protocol."""
        assert isinstance(FixedPriceSource({}), PriceSource)


class TestSwappingSources:
    """Two different implementations must be interchangeable."""

    @pytest.mark.asyncio
    async def test_two_sources_produce_different_outputs(self) -> None:
        """Swapping the source changes the numbers but not the interface."""
        sku_id = uuid4()
        as_of = datetime(2025, 6, 1, tzinfo=UTC)

        cheap = FixedPriceSource({("A", "RESELL_OPEN_BOX"): 100.0}, source_tag="cheap")
        rich = FixedPriceSource({("A", "RESELL_OPEN_BOX"): 900.0}, source_tag="rich")

        cheap_distribution = await cheap.get_distribution(sku_id, "A", "RESELL_OPEN_BOX", as_of)
        rich_distribution = await rich.get_distribution(sku_id, "A", "RESELL_OPEN_BOX", as_of)

        assert cheap_distribution.mean == pytest.approx(100.0, rel=0.05)
        assert rich_distribution.mean == pytest.approx(900.0, rel=0.05)
        assert cheap_distribution.source == "cheap"
        assert rich_distribution.source == "rich"

    @pytest.mark.asyncio
    async def test_decision_code_is_unchanged_by_the_source(self) -> None:
        """The same evaluation call works with either source."""
        from secondroute.condition.grades import InspectionSignals
        from secondroute.decision.evaluator import EvaluationInput, evaluate_channels
        from tests.phase2.decision_fixtures import build_cost_book

        sku_id = uuid4()
        as_of = datetime(2025, 6, 1, tzinfo=UTC)
        signals = InspectionSignals(
            battery_health_pct=95.0,
            cosmetic_grade="A",
            functional_tests={"display": True},
            accessories={"charger": True},
            activation_lock="none",
        )
        evaluation_input = EvaluationInput(
            sku_id=sku_id,
            signals=signals,
            cost_book=build_cost_book(),
            as_of=as_of,
        )

        cheap = FixedPriceSource({("A", "RESELL_OPEN_BOX"): 100.0}, source_tag="cheap")
        rich = FixedPriceSource({("A", "RESELL_OPEN_BOX"): 900.0}, source_tag="rich")

        cheap_result = await evaluate_channels(evaluation_input, cheap, samples=500, seed=1)
        rich_result = await evaluate_channels(evaluation_input, rich, samples=500, seed=1)

        cheap_open_box = cheap_result.by_channel("RESELL_OPEN_BOX")
        rich_open_box = rich_result.by_channel("RESELL_OPEN_BOX")
        assert cheap_open_box is not None
        assert rich_open_box is not None
        assert rich_open_box.mean > cheap_open_box.mean


class TestPriceDistribution:
    """The distribution type carries the statistics the engine needs."""

    def test_mean_and_stddev(self) -> None:
        """Mean and standard deviation are computed from the observations."""
        distribution = PriceDistribution(
            values=(10.0, 20.0, 30.0),
            weights=(1.0, 1.0, 1.0),
            source="test",
            as_of=datetime(2025, 1, 1, tzinfo=UTC),
        )
        assert distribution.mean == pytest.approx(20.0)
        assert distribution.stddev == pytest.approx(8.16496, rel=1e-4)
        assert distribution.sample_count == 3
        assert distribution.minimum == 10.0
        assert distribution.maximum == 30.0

    def test_weighted_mean(self) -> None:
        """Heavier observations pull the mean."""
        distribution = PriceDistribution(
            values=(0.0, 100.0),
            weights=(9.0, 1.0),
            source="test",
            as_of=datetime(2025, 1, 1, tzinfo=UTC),
        )
        assert distribution.mean == pytest.approx(10.0)

    def test_quantiles(self) -> None:
        """Quantiles are ordered correctly."""
        distribution = PriceDistribution(
            values=tuple(float(i) for i in range(101)),
            weights=tuple(1.0 for _ in range(101)),
            source="test",
            as_of=datetime(2025, 1, 1, tzinfo=UTC),
        )
        assert distribution.quantile(0.0) == pytest.approx(0.0, abs=1.5)
        assert distribution.quantile(0.5) == pytest.approx(50.0, abs=1.5)
        assert distribution.quantile(1.0) == pytest.approx(100.0, abs=1.5)

    def test_empty_distribution_is_rejected(self) -> None:
        """A distribution needs at least one observation."""
        with pytest.raises(ValueError, match="at least one observation"):
            PriceDistribution(
                values=(),
                weights=(),
                source="test",
                as_of=datetime(2025, 1, 1, tzinfo=UTC),
            )

    def test_mismatched_lengths_are_rejected(self) -> None:
        """Values and weights must line up."""
        with pytest.raises(ValueError, match="same length"):
            PriceDistribution(
                values=(1.0, 2.0),
                weights=(1.0,),
                source="test",
                as_of=datetime(2025, 1, 1, tzinfo=UTC),
            )

    def test_zero_total_weight_is_rejected(self) -> None:
        """Weights must sum to something positive."""
        with pytest.raises(ValueError, match="positive value"):
            PriceDistribution(
                values=(1.0,),
                weights=(0.0,),
                source="test",
                as_of=datetime(2025, 1, 1, tzinfo=UTC),
            )

    def test_sampling_is_reproducible(self) -> None:
        """The same seed produces the same sample."""
        distribution = PriceDistribution(
            values=(1.0, 2.0, 3.0, 4.0),
            weights=(1.0, 1.0, 1.0, 1.0),
            source="test",
            as_of=datetime(2025, 1, 1, tzinfo=UTC),
        )
        first = distribution.sample(np.random.default_rng(42), 100)
        second = distribution.sample(np.random.default_rng(42), 100)
        assert np.array_equal(first, second)

    def test_sampling_returns_the_right_size(self) -> None:
        """Sampling honours the requested size."""
        distribution = PriceDistribution(
            values=(1.0, 2.0),
            weights=(1.0, 1.0),
            source="test",
            as_of=datetime(2025, 1, 1, tzinfo=UTC),
        )
        assert distribution.sample(np.random.default_rng(1), 37).shape == (37,)

    def test_from_parameters_is_deterministic(self) -> None:
        """Building a distribution from parameters is reproducible."""
        kwargs: dict[str, Any] = {
            "mean": 500.0,
            "stddev": 60.0,
            "source": "test",
            "as_of": datetime(2025, 1, 1, tzinfo=UTC),
            "observations": 16,
        }
        first = PriceDistribution.from_parameters(**kwargs)
        second = PriceDistribution.from_parameters(**kwargs)
        assert first.values == second.values
        assert first.mean == pytest.approx(500.0, rel=0.15)

    def test_from_parameters_has_no_nan(self) -> None:
        """The generated support points are all finite."""
        distribution = PriceDistribution.from_parameters(
            mean=800.0,
            stddev=120.0,
            source="test",
            as_of=datetime(2025, 1, 1, tzinfo=UTC),
            observations=64,
        )
        assert all(np.isfinite(value) for value in distribution.values)
        assert min(distribution.values) > 0.0


class TestSyntheticPriceSource:
    """The synthetic adapter behaves predictably."""

    @pytest.mark.asyncio
    async def test_unknown_grade_raises(self) -> None:
        """An unknown grade is reported, not silently defaulted."""
        source = SyntheticPriceSource()
        with pytest.raises(PriceSourceNotFoundError):
            await source.get_distribution(
                uuid4(), "Z", "RESELL_OPEN_BOX", datetime(2025, 1, 1, tzinfo=UTC)
            )

    @pytest.mark.asyncio
    async def test_unknown_channel_raises(self) -> None:
        """An unknown channel is reported."""
        source = SyntheticPriceSource()
        with pytest.raises(PriceSourceNotFoundError):
            await source.get_distribution(uuid4(), "A", "MYSTERY", datetime(2025, 1, 1, tzinfo=UTC))

    @pytest.mark.asyncio
    async def test_higher_grade_worth_more(self) -> None:
        """Grade A is worth more than grade D."""
        source = SyntheticPriceSource()
        as_of = datetime(2025, 1, 1, tzinfo=UTC)
        grade_a = await source.get_distribution(uuid4(), "A", "RESELL_OPEN_BOX", as_of)
        grade_d = await source.get_distribution(uuid4(), "D", "RESELL_OPEN_BOX", as_of)
        assert grade_a.mean > grade_d.mean

    @pytest.mark.asyncio
    async def test_open_box_beats_refurb(self) -> None:
        """Open-box pays more than refurb."""
        source = SyntheticPriceSource()
        as_of = datetime(2025, 1, 1, tzinfo=UTC)
        open_box = await source.get_distribution(uuid4(), "A", "RESELL_OPEN_BOX", as_of)
        refurb = await source.get_distribution(uuid4(), "A", "RESELL_REFURB", as_of)
        assert open_box.mean > refurb.mean

    @pytest.mark.asyncio
    async def test_donate_has_no_value(self) -> None:
        """The donate channel recovers nothing."""
        source = SyntheticPriceSource()
        distribution = await source.get_distribution(
            uuid4(), "A", "DONATE", datetime(2025, 1, 1, tzinfo=UTC)
        )
        assert distribution.mean == pytest.approx(0.0)
