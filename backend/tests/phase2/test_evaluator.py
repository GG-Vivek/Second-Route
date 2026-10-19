"""
Tests for the Monte Carlo channel evaluator (F2.5).
"""

from __future__ import annotations

from datetime import datetime, timezone, UTC
from uuid import UUID

import numpy as np
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from secondroute.condition.grades import InspectionSignals
from secondroute.costs.models import CostKind
from secondroute.costs.service import CostBook
from secondroute.decision.evaluator import (
    PHASE2_CHANNELS,
    EvaluationInput,
    derive_seed,
    evaluate_channels,
)
from tests.phase2.decision_fixtures import FixedPriceSource, build_cost_book

AS_OF = datetime(2025, 6, 1, tzinfo=UTC)


def make_input(
    cost_book: CostBook,
    sku_id: UUID,
    *,
    battery: float = 95.0,
    cosmetic_grade: str = "A",
) -> EvaluationInput:
    """Build an evaluation input for a test."""
    signals = InspectionSignals(
        battery_health_pct=battery,
        cosmetic_grade=cosmetic_grade,
        functional_tests={"display": True, "keyboard": True},
        accessories={"charger": True},
        activation_lock="none",
    )
    return EvaluationInput(
        sku_id=sku_id,
        signals=signals,
        cost_book=cost_book,
        as_of=AS_OF,
    )


def uniform_source(mean: float, stddev: float = 0.0) -> FixedPriceSource:
    """Return a price source that returns the same distribution for every cell."""
    return FixedPriceSource(
        {("*", "*"): mean},
        stddev=stddev,
        source_tag="uniform",
        observations=16,
    )


class TestSeededDeterminism:
    """The same seed must always give the same answer."""

    @pytest.mark.asyncio
    async def test_same_seed_same_result(self, cost_book: CostBook, sku_id: UUID) -> None:
        """Two runs with the same seed produce identical numbers."""
        evaluation_input = make_input(cost_book, sku_id)
        source = uniform_source(1000.0)

        first = await evaluate_channels(evaluation_input, source, samples=2000, seed=42)
        second = await evaluate_channels(evaluation_input, source, samples=2000, seed=42)

        for channel in first.channels:
            other = second.by_channel(channel.channel)
            assert other is not None
            assert channel.mean == pytest.approx(other.mean, abs=1e-9)
            assert channel.p10 == pytest.approx(other.p10, abs=1e-9)
            assert channel.p50 == pytest.approx(other.p50, abs=1e-9)
            assert channel.p90 == pytest.approx(other.p90, abs=1e-9)
            assert np.array_equal(channel.net_samples, other.net_samples)

    @pytest.mark.asyncio
    async def test_different_seed_gives_different_samples(
        self, cost_book: CostBook, sku_id: UUID
    ) -> None:
        """A different seed produces a different sample path."""
        evaluation_input = make_input(cost_book, sku_id)
        source = uniform_source(1000.0, stddev=100.0)

        first = await evaluate_channels(evaluation_input, source, samples=2000, seed=1)
        second = await evaluate_channels(evaluation_input, source, samples=2000, seed=2)

        first_channel = first.by_channel("RESELL_OPEN_BOX")
        second_channel = second.by_channel("RESELL_OPEN_BOX")
        assert first_channel is not None
        assert second_channel is not None
        assert not np.array_equal(first_channel.net_samples, second_channel.net_samples)

    def test_derive_seed_is_stable(self) -> None:
        """Sub-seed derivation is deterministic."""
        assert derive_seed(42, "RESELL_OPEN_BOX", "A") == derive_seed(42, "RESELL_OPEN_BOX", "A")
        assert derive_seed(42, "RESELL_OPEN_BOX", "A") != derive_seed(42, "RESELL_REFURB", "A")


class TestChannelEvaluation:
    """Every channel is evaluated with the right statistics."""

    @pytest.mark.asyncio
    async def test_every_channel_is_evaluated(self, cost_book: CostBook, sku_id: UUID) -> None:
        """All four channels are evaluated."""
        result = await evaluate_channels(
            make_input(cost_book, sku_id), uniform_source(1000.0), samples=500, seed=1
        )
        assert set(result.channel_names()) == set(PHASE2_CHANNELS)

    @pytest.mark.asyncio
    async def test_quantiles_are_ordered(self, cost_book: CostBook, sku_id: UUID) -> None:
        """p10 <= p50 <= p90 for every channel."""
        result = await evaluate_channels(
            make_input(cost_book, sku_id),
            uniform_source(1000.0, stddev=100.0),
            samples=2000,
            seed=1,
        )
        for channel in result.channels:
            if not channel.eligible:
                continue
            assert channel.p10 <= channel.p50 + 1e-9
            assert channel.p50 <= channel.p90 + 1e-9

    @pytest.mark.asyncio
    async def test_probability_best_sums_to_one(self, cost_book: CostBook, sku_id: UUID) -> None:
        """The probabilities of being best form a distribution."""
        result = await evaluate_channels(
            make_input(cost_book, sku_id),
            uniform_source(1000.0, stddev=100.0),
            samples=2000,
            seed=1,
        )
        assert sum(result.probability_best.values()) == pytest.approx(1.0, abs=1e-6)

    @pytest.mark.asyncio
    async def test_ineligible_channel_is_skipped(self, cost_book: CostBook, sku_id: UUID) -> None:
        """A blocked channel produces no samples and is excluded from the joint draws."""
        from secondroute.condition.grades import channel_eligibility, grade_distribution

        signals = InspectionSignals(
            battery_health_pct=95.0,
            cosmetic_grade="A",
            functional_tests={"display": True},
            accessories={"charger": True},
            activation_lock="present",
        )
        distribution = grade_distribution(signals)
        eligibility = channel_eligibility(signals, distribution)

        evaluation_input = EvaluationInput(
            sku_id=sku_id,
            signals=signals,
            cost_book=cost_book,
            as_of=AS_OF,
            eligibility=eligibility,
        )
        result = await evaluate_channels(
            evaluation_input, uniform_source(1000.0), samples=500, seed=1
        )

        open_box = result.by_channel("RESELL_OPEN_BOX")
        assert open_box is not None
        assert open_box.eligible is False
        assert open_box.exclusion_reason
        assert "RESELL_OPEN_BOX" not in result.joint_index_by_channel
        assert "RESELL_OPEN_BOX" not in result.probability_best

    @pytest.mark.asyncio
    async def test_breakdown_adds_up(self, cost_book: CostBook, sku_id: UUID) -> None:
        """The cost breakdown is internally consistent."""
        result = await evaluate_channels(
            make_input(cost_book, sku_id),
            uniform_source(1000.0, stddev=50.0),
            samples=2000,
            seed=1,
        )
        channel = result.by_channel("RESELL_OPEN_BOX")
        assert channel is not None
        breakdown = channel.breakdown
        assert breakdown.total_cost == pytest.approx(
            breakdown.fees
            + breakdown.logistics
            + breakdown.handling
            + breakdown.repair
            + breakdown.holding,
            rel=1e-9,
        )
        assert breakdown.net == pytest.approx(breakdown.sale_price - breakdown.total_cost, rel=1e-9)


class TestFeeMonotonicity:
    """Net value must decrease as fees increase."""

    @pytest.mark.asyncio
    async def test_net_decreases_as_fee_increases(self, cost_book: CostBook, sku_id: UUID) -> None:
        """Raising the platform fee lowers the expected net."""
        base = await evaluate_channels(
            make_input(cost_book, sku_id), uniform_source(1000.0), samples=2000, seed=7
        )
        higher_book = cost_book.with_override(CostKind.CHANNEL_FEE_PCT, "RESELL_OPEN_BOX", 0.40)
        higher = await evaluate_channels(
            make_input(higher_book, sku_id),
            uniform_source(1000.0),
            samples=2000,
            seed=7,
        )

        base_channel = base.by_channel("RESELL_OPEN_BOX")
        higher_channel = higher.by_channel("RESELL_OPEN_BOX")
        assert base_channel is not None
        assert higher_channel is not None
        assert higher_channel.mean < base_channel.mean

    @pytest.mark.asyncio
    async def test_every_channel_net_decreases_as_its_fee_increases(
        self, cost_book: CostBook, sku_id: UUID
    ) -> None:
        """The property holds for every channel."""
        for channel_name in PHASE2_CHANNELS:
            base = await evaluate_channels(
                make_input(cost_book, sku_id),
                uniform_source(1000.0),
                samples=1000,
                seed=11,
            )
            higher_book = cost_book.with_override(CostKind.CHANNEL_FEE_PCT, channel_name, 0.35)
            higher = await evaluate_channels(
                make_input(higher_book, sku_id),
                uniform_source(1000.0),
                samples=1000,
                seed=11,
            )
            base_channel = base.by_channel(channel_name)
            higher_channel = higher.by_channel(channel_name)
            assert base_channel is not None
            assert higher_channel is not None
            assert higher_channel.mean < base_channel.mean


@settings(max_examples=8, deadline=None)
@given(
    low_fee=st.floats(min_value=0.0, max_value=0.4),
    high_fee=st.floats(min_value=0.0, max_value=0.6),
    price=st.floats(min_value=200.0, max_value=5000.0),
)
def test_net_value_decreases_as_fees_increase(
    low_fee: float, high_fee: float, price: float
) -> None:
    """Property: net value is monotonically decreasing in the fee.

    The real evaluator is exercised, so the property covers the whole cost
    stack rather than just the fee arithmetic.
    """
    import asyncio

    assume(high_fee >= low_fee)

    sku = UUID("99999999-8888-7777-6666-555555555555")
    book = build_cost_book()
    source = FixedPriceSource({("*", "*"): price}, source_tag="flat", observations=8)

    async def evaluate(fee: float) -> float:
        overridden = book.with_override(CostKind.CHANNEL_FEE_PCT, "RESELL_OPEN_BOX", fee)
        result = await evaluate_channels(make_input(overridden, sku), source, samples=800, seed=5)
        channel = result.by_channel("RESELL_OPEN_BOX")
        assert channel is not None
        return channel.mean

    low_mean = asyncio.run(evaluate(low_fee))
    high_mean = asyncio.run(evaluate(high_fee))

    assert high_mean <= low_mean + 1e-6


class TestCostUncertainty:
    """Cost components carry their own uncertainty."""

    @pytest.mark.asyncio
    async def test_repair_uncertainty_widens_the_distribution(
        self, cost_book: CostBook, sku_id: UUID
    ) -> None:
        """A higher repair estimate widens the p10-p90 range."""
        low = cost_book.with_override(CostKind.REPAIR_COST, "RESELL_OPEN_BOX:B", 10.0)
        high = cost_book.with_override(CostKind.REPAIR_COST, "RESELL_OPEN_BOX:B", 400.0)

        low_result = await evaluate_channels(
            make_input(low, sku_id), uniform_source(1000.0), samples=2000, seed=3
        )
        high_result = await evaluate_channels(
            make_input(high, sku_id), uniform_source(1000.0), samples=2000, seed=3
        )

        low_channel = low_result.by_channel("RESELL_OPEN_BOX")
        high_channel = high_result.by_channel("RESELL_OPEN_BOX")
        assert low_channel is not None
        assert high_channel is not None
        assert (high_channel.p90 - high_channel.p10) > (low_channel.p90 - low_channel.p10)
