"""
Tests for the confidence gate and SAFE_DEFAULT (F2.7).
"""

from __future__ import annotations

from datetime import datetime, timezone, UTC
from uuid import UUID

import numpy as np
import pytest

from secondroute.condition.grades import InspectionSignals
from secondroute.costs.service import CostBook
from secondroute.decision.confidence import (
    SAFE_DEFAULT,
    apply_confidence_gate,
    compute_confidence,
    highest_p10_channel,
)
from secondroute.decision.evaluator import EvaluationInput, evaluate_channels
from tests.phase2.decision_fixtures import FixedPriceSource

AS_OF = datetime(2025, 6, 1, tzinfo=UTC)


def make_input(cost_book: CostBook, sku_id: UUID) -> EvaluationInput:
    """Build an evaluation input for a test."""
    signals = InspectionSignals(
        battery_health_pct=95.0,
        cosmetic_grade="A",
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


def source_for(means: dict[tuple[str, str], float], stddev: float = 0.0) -> FixedPriceSource:
    """Build a fixed price source from a ``(grade, channel)`` mapping."""
    return FixedPriceSource(means, stddev=stddev, source_tag="fixture", observations=16)


class TestComputeConfidence:
    """The confidence metric itself."""

    def test_clear_winner_has_high_confidence(self) -> None:
        """One channel dominating gives a high confidence."""
        joint = np.array([[1000.0] * 100, [500.0] * 100])
        confidence, _ = compute_confidence(joint, 0)
        assert confidence == pytest.approx(1.0)

    def test_overlapping_channels_have_low_confidence(self) -> None:
        """Two indistinguishable channels give a low confidence."""
        rng = np.random.default_rng(0)
        joint = np.vstack([rng.normal(800.0, 300.0, 500), rng.normal(790.0, 300.0, 500)])
        confidence, _ = compute_confidence(joint, 0)
        assert confidence < 0.5

    def test_out_of_range_index_is_rejected(self) -> None:
        """An invalid row index is an error."""
        joint = np.array([[1.0, 2.0]])
        with pytest.raises(IndexError):
            compute_confidence(joint, 5)

    def test_empty_draws_give_zero_confidence(self) -> None:
        """No draws means no confidence."""
        confidence, within = compute_confidence(np.zeros((0, 0)), 0)
        assert confidence == 0.0
        assert within == 0.0

    def test_within_margin_share_is_reported(self) -> None:
        """The plain within-margin share is reported separately."""
        joint = np.array([[1000.0] * 10, [500.0] * 10])
        confidence, within = compute_confidence(joint, 0)
        assert within == pytest.approx(1.0)
        assert confidence == pytest.approx(1.0)


class TestSafeDefault:
    """The gate must fall back when the evidence is weak."""

    def test_gate_passes_for_a_clear_winner(self) -> None:
        """A decisive result is returned as-is."""
        from secondroute.decision.evaluator import ChannelEvaluation, CostBreakdown

        channels = (
            ChannelEvaluation(
                channel="WINNER",
                eligible=True,
                exclusion_reason=None,
                net_samples=np.array([1000.0]),
                mean=1000.0,
                stddev=10.0,
                p10=990.0,
                p50=1000.0,
                p90=1010.0,
                breakdown=CostBreakdown(1000.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                grade_probabilities={},
            ),
        )
        joint = np.array([[1000.0] * 50])
        channel, fallback, result = apply_confidence_gate(
            channels, joint, 0, "WINNER", threshold=0.70
        )
        assert channel == "WINNER"
        assert fallback is False
        assert result.passed is True

    def test_gate_falls_back_to_safe_default(self) -> None:
        """A weak result returns SAFE_DEFAULT."""
        from secondroute.decision.evaluator import ChannelEvaluation, CostBreakdown

        channels = (
            ChannelEvaluation(
                channel="A",
                eligible=True,
                exclusion_reason=None,
                net_samples=np.array([800.0]),
                mean=800.0,
                stddev=300.0,
                p10=500.0,
                p50=800.0,
                p90=1100.0,
                breakdown=CostBreakdown(800.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                grade_probabilities={},
            ),
            ChannelEvaluation(
                channel="B",
                eligible=True,
                exclusion_reason=None,
                net_samples=np.array([790.0]),
                mean=790.0,
                stddev=300.0,
                p10=490.0,
                p50=790.0,
                p90=1090.0,
                breakdown=CostBreakdown(790.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                grade_probabilities={},
            ),
        )
        rng = np.random.default_rng(4)
        joint = np.vstack([rng.normal(800.0, 300.0, 400), rng.normal(790.0, 300.0, 400)])

        channel, fallback, result = apply_confidence_gate(channels, joint, 0, "A", threshold=0.70)
        assert channel == SAFE_DEFAULT
        assert fallback is True
        assert result.confidence < 0.70
        assert result.fallback_channel in {"A", "B"}

    def test_highest_p10_channel_is_the_conservative_floor(self) -> None:
        """The SAFE_DEFAULT floor is the channel with the highest p10."""
        from secondroute.decision.evaluator import ChannelEvaluation, CostBreakdown

        def channel(name: str, p10: float) -> ChannelEvaluation:
            return ChannelEvaluation(
                channel=name,
                eligible=True,
                exclusion_reason=None,
                net_samples=np.array([float(p10)]),
                mean=float(p10),
                stddev=0.0,
                p10=float(p10),
                p50=float(p10),
                p90=float(p10),
                breakdown=CostBreakdown(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                grade_probabilities={},
            )

        channels = (channel("HIGH_P10", 900.0), channel("LOW_P10", 800.0))
        assert highest_p10_channel(channels) == "HIGH_P10"

    def test_highest_p10_ignores_ineligible_channels(self) -> None:
        """An ineligible channel cannot be the floor."""
        from secondroute.decision.evaluator import ChannelEvaluation, CostBreakdown

        blocked = ChannelEvaluation(
            channel="BLOCKED",
            eligible=False,
            exclusion_reason="blocked",
            net_samples=np.array([]),
            mean=0.0,
            stddev=0.0,
            p10=0.0,
            p50=0.0,
            p90=0.0,
            breakdown=CostBreakdown(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            grade_probabilities={},
        )
        allowed = ChannelEvaluation(
            channel="ALLOWED",
            eligible=True,
            exclusion_reason=None,
            net_samples=np.array([10.0]),
            mean=10.0,
            stddev=0.0,
            p10=10.0,
            p50=10.0,
            p90=10.0,
            breakdown=CostBreakdown(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            grade_probabilities={},
        )
        assert highest_p10_channel((blocked, allowed)) == "ALLOWED"


class TestEndToEndGating:
    """The gate behaves correctly with the real engine."""

    @pytest.mark.asyncio
    async def test_clear_winner_returns_the_winner(self, cost_book: CostBook, sku_id: UUID) -> None:
        """A unit with a big price advantage is routed to the better channel."""
        means = {
            ("A", "RESELL_OPEN_BOX"): 1800.0,
            ("A", "RESELL_REFURB"): 900.0,
            ("A", "RECYCLE"): 60.0,
            ("A", "DONATE"): 0.0,
            ("B", "RESELL_OPEN_BOX"): 1400.0,
            ("B", "RESELL_REFURB"): 700.0,
            ("B", "RECYCLE"): 50.0,
            ("B", "DONATE"): 0.0,
            ("C", "RESELL_OPEN_BOX"): 900.0,
            ("C", "RESELL_REFURB"): 450.0,
            ("C", "RECYCLE"): 40.0,
            ("C", "DONATE"): 0.0,
            ("D", "RESELL_OPEN_BOX"): 500.0,
            ("D", "RESELL_REFURB"): 250.0,
            ("D", "RECYCLE"): 30.0,
            ("D", "DONATE"): 0.0,
        }
        result = await evaluate_channels(
            make_input(cost_book, sku_id),
            source_for(means),
            samples=4000,
            seed=13,
        )
        open_box = result.by_channel("RESELL_OPEN_BOX")
        refurb = result.by_channel("RESELL_REFURB")
        assert open_box is not None
        assert refurb is not None

        channel, fallback, confidence_result = apply_confidence_gate(
            result.channels,
            result.joint_draws,
            result.joint_index("RESELL_OPEN_BOX"),
            "RESELL_OPEN_BOX",
            threshold=0.70,
        )
        assert channel == "RESELL_OPEN_BOX"
        assert fallback is False
        assert confidence_result.confidence >= 0.70

    @pytest.mark.asyncio
    async def test_overlapping_distributions_return_safe_default(
        self, cost_book: CostBook, sku_id: UUID
    ) -> None:
        """Two channels with overlapping prices fall back to SAFE_DEFAULT."""
        means = {
            (grade, channel): 800.0
            for grade in ("A", "B", "C", "D")
            for channel in ("RESELL_OPEN_BOX", "RESELL_REFURB")
        }
        means.update({(grade, "RECYCLE"): 60.0 for grade in ("A", "B", "C", "D")})
        means.update({(grade, "DONATE"): 0.0 for grade in ("A", "B", "C", "D")})

        source = FixedPriceSource(means, stddev=400.0, source_tag="overlapping", observations=32)
        result = await evaluate_channels(
            make_input(cost_book, sku_id),
            source,
            samples=4000,
            seed=21,
        )

        channel, fallback, confidence_result = apply_confidence_gate(
            result.channels,
            result.joint_draws,
            result.joint_index("RESELL_OPEN_BOX"),
            "RESELL_OPEN_BOX",
            threshold=0.70,
        )
        assert channel == SAFE_DEFAULT
        assert fallback is True
        assert confidence_result.confidence < 0.70
        assert confidence_result.fallback_channel is not None
