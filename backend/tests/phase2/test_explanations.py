"""
Tests for the reasons and flip conditions (F2.8).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import numpy as np
import pytest

from secondroute.condition.grades import InspectionSignals
from secondroute.costs.service import CostBook
from secondroute.decision.confidence import apply_confidence_gate
from secondroute.decision.evaluator import (
    ChannelEvaluation,
    CostBreakdown,
    EvaluationInput,
    evaluate_channels,
)
from secondroute.decision.explanations import (
    FlipCondition,
    Reason,
    Recommendation,
    apply_flip_condition,
    build_flip_conditions,
    build_reasons,
)
from secondroute.decision.utility import rank_channels
from tests.phase2.decision_fixtures import FixedPriceSource, build_cost_book

AS_OF = datetime(2025, 6, 1, tzinfo=UTC)


def make_channel(
    channel: str,
    *,
    mean: float,
    eligible: bool = True,
    sale_price: float = 0.0,
    fees: float = 0.0,
    logistics: float = 0.0,
    handling: float = 0.0,
    repair: float = 0.0,
    holding: float = 0.0,
) -> ChannelEvaluation:
    """Build a channel evaluation for a test."""
    return ChannelEvaluation(
        channel=channel,
        eligible=eligible,
        exclusion_reason=None if eligible else "blocked",
        net_samples=np.array([mean]),
        mean=mean,
        stddev=0.0,
        p10=mean,
        p50=mean,
        p90=mean,
        breakdown=CostBreakdown(
            sale_price=sale_price,
            fees=fees,
            logistics=logistics,
            handling=handling,
            repair=repair,
            holding=holding,
        ),
        grade_probabilities={"A": 1.0},
    )


class TestReasons:
    """Reasons explain the gap between the top two channels."""

    def test_reasons_are_ranked_by_contribution(self) -> None:
        """The biggest contributor comes first."""
        recommended = make_channel(
            "A",
            mean=500.0,
            sale_price=700.0,
            fees=100.0,
            logistics=50.0,
            handling=30.0,
            repair=10.0,
            holding=10.0,
        )
        runner_up = make_channel(
            "B",
            mean=400.0,
            sale_price=600.0,
            fees=100.0,
            logistics=90.0,
            handling=30.0,
            repair=10.0,
            holding=10.0,
        )
        reasons = build_reasons(recommended, runner_up)
        assert reasons
        contributions = [abs(reason.contribution) for reason in reasons]
        assert contributions == sorted(contributions, reverse=True)

    def test_price_difference_is_the_top_reason_when_it_dominates(self) -> None:
        """A bigger sale price is reported as the main reason."""
        recommended = make_channel(
            "A",
            mean=500.0,
            sale_price=800.0,
            fees=100.0,
            logistics=50.0,
            handling=30.0,
            repair=10.0,
            holding=10.0,
        )
        runner_up = make_channel(
            "B",
            mean=400.0,
            sale_price=600.0,
            fees=100.0,
            logistics=50.0,
            handling=30.0,
            repair=10.0,
            holding=10.0,
        )
        reasons = build_reasons(recommended, runner_up)
        assert reasons[0].code == "favourable_sale_price"
        assert reasons[0].favours_recommended is True
        assert reasons[0].contribution == pytest.approx(200.0)

    def test_lower_costs_are_reported_as_favourable(self) -> None:
        """Paying less in logistics favours the recommended channel."""
        recommended = make_channel(
            "A",
            mean=500.0,
            sale_price=700.0,
            fees=100.0,
            logistics=30.0,
            handling=30.0,
            repair=10.0,
            holding=10.0,
        )
        runner_up = make_channel(
            "B",
            mean=400.0,
            sale_price=700.0,
            fees=100.0,
            logistics=80.0,
            handling=30.0,
            repair=10.0,
            holding=10.0,
        )
        reasons = build_reasons(recommended, runner_up)
        logistics_reason = next(r for r in reasons if r.code.endswith("logistics"))
        assert logistics_reason.favours_recommended is True
        assert logistics_reason.contribution == pytest.approx(50.0)

    def test_no_runner_up_is_handled(self) -> None:
        """A single eligible channel still produces a reason."""
        reasons = build_reasons(make_channel("ONLY", mean=100.0), None)
        assert len(reasons) == 1
        assert reasons[0].code == "only_eligible_channel"

    def test_reason_text_is_plain_language(self) -> None:
        """Every reason has readable text."""
        recommended = make_channel(
            "A",
            mean=500.0,
            sale_price=800.0,
            fees=100.0,
            logistics=50.0,
            handling=30.0,
            repair=10.0,
            holding=10.0,
        )
        runner_up = make_channel(
            "B",
            mean=400.0,
            sale_price=600.0,
            fees=100.0,
            logistics=50.0,
            handling=30.0,
            repair=10.0,
            holding=10.0,
        )
        reasons = build_reasons(recommended, runner_up)
        assert all(reason.text.endswith(".") for reason in reasons)
        assert all(len(reason.text) > 10 for reason in reasons)

    def test_reason_serialises(self) -> None:
        """A reason can be serialised for the API."""
        reason = Reason(
            code="favourable_sale_price",
            label="Expected sale price",
            contribution=12.5,
            favours_recommended=True,
            text="Better price.",
        )
        payload = reason.as_dict()
        assert payload["code"] == "favourable_sale_price"
        assert payload["contribution"] == 12.5


class TestFlipConditions:
    """Flip conditions find the thresholds that change the decision."""

    #: A fixture with a clear open-box winner that a fee increase can beat.
    MEANS = {
        ("A", "RESELL_OPEN_BOX"): 1800.0,
        ("A", "RESELL_REFURB"): 1200.0,
        ("A", "RECYCLE"): 60.0,
        ("A", "DONATE"): 0.0,
        ("B", "RESELL_OPEN_BOX"): 1400.0,
        ("B", "RESELL_REFURB"): 950.0,
        ("B", "RECYCLE"): 50.0,
        ("B", "DONATE"): 0.0,
        ("C", "RESELL_OPEN_BOX"): 900.0,
        ("C", "RESELL_REFURB"): 600.0,
        ("C", "RECYCLE"): 40.0,
        ("C", "DONATE"): 0.0,
        ("D", "RESELL_OPEN_BOX"): 500.0,
        ("D", "RESELL_REFURB"): 350.0,
        ("D", "RECYCLE"): 30.0,
        ("D", "DONATE"): 0.0,
    }

    def _input(self, cost_book: CostBook, sku_id: UUID) -> EvaluationInput:
        """Build the evaluation input for the flip tests."""
        signals = InspectionSignals(
            battery_health_pct=95.0,
            cosmetic_grade="A",
            functional_tests={"display": True, "keyboard": True},
            accessories={"charger": True},
            activation_lock="none",
        )
        return EvaluationInput(sku_id=sku_id, signals=signals, cost_book=cost_book, as_of=AS_OF)

    async def _recommender(self, candidate: EvaluationInput) -> Recommendation:
        """Return the recommendation for a candidate input."""
        result = await evaluate_channels(
            candidate,
            FixedPriceSource(self.MEANS, stddev=40.0, observations=16),
            samples=600,
            seed=3,
        )
        ranked = rank_channels(result.channels, "balanced")
        channel = ranked[0][0]
        gated, fallback, _ = apply_confidence_gate(
            result.channels,
            result.joint_draws,
            result.joint_index(channel),
            channel,
            threshold=0.70,
        )
        return Recommendation(channel=channel, gated_channel=gated, fallback_used=fallback)

    @pytest.mark.asyncio
    async def test_flip_condition_found_for_a_cost_input(
        self, cost_book: CostBook, sku_id: UUID
    ) -> None:
        """A cost input that flips the recommendation is reported."""
        evaluation_input = self._input(cost_book, sku_id)
        conditions = await build_flip_conditions(
            evaluation_input, self._recommender, "RESELL_OPEN_BOX"
        )
        assert conditions
        for condition in conditions:
            assert condition.input_name
            assert condition.new_channel
            assert condition.description.endswith(".")
            assert condition.input_kind in {"numeric", "categorical"}

    @pytest.mark.asyncio
    async def test_each_flip_condition_really_flips_the_decision(
        self, cost_book: CostBook, sku_id: UUID
    ) -> None:
        """Applying the reported threshold changes the recommendation."""
        evaluation_input = self._input(cost_book, sku_id)
        baseline = await self._recommender(evaluation_input)

        conditions = await build_flip_conditions(
            evaluation_input, self._recommender, "RESELL_OPEN_BOX"
        )
        assert conditions

        verified = 0
        for condition in conditions:
            if condition.input_kind != "numeric":
                continue
            perturbed = apply_flip_condition(evaluation_input, condition)
            result = await self._recommender(perturbed)
            assert result.channel != baseline.channel, (
                f"{condition.input_name} threshold did not change the recommendation"
            )
            verified += 1

        assert verified > 0, "at least one numeric flip condition must be reproducible"

    @pytest.mark.asyncio
    async def test_cosmetic_grade_flip_is_well_formed(
        self, cost_book: CostBook, sku_id: UUID
    ) -> None:
        """Any cosmetic grade flip that is discovered is well formed."""
        evaluation_input = self._input(cost_book, sku_id)
        conditions = await build_flip_conditions(
            evaluation_input, self._recommender, "RESELL_OPEN_BOX"
        )
        for condition in conditions:
            if condition.input_name != "cosmetic_grade":
                continue
            assert condition.input_kind == "categorical"
            assert condition.threshold_value in {"A", "B", "C", "D"}
            assert condition.threshold_value != "A"
            perturbed = apply_flip_condition(evaluation_input, condition)
            assert perturbed.signals.cosmetic_grade == condition.threshold_value

    def test_flip_condition_serialises(self) -> None:
        """A flip condition can be serialised for the API."""
        condition = FlipCondition(
            input_name="battery_health_pct",
            input_kind="numeric",
            current_value=95.0,
            threshold_value=72.5,
            new_channel="RESELL_REFURB",
            direction="below",
            description="If battery health were below 72.5% the recommendation would change.",
            target_channel="RESELL_OPEN_BOX",
        )
        payload = condition.as_dict()
        assert payload["input_name"] == "battery_health_pct"
        assert payload["new_channel"] == "RESELL_REFURB"
        assert payload["direction"] == "below"
        assert payload["target_channel"] == "RESELL_OPEN_BOX"
