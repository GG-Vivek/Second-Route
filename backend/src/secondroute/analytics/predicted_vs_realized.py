"""
Predicted vs realized view for Phase 4 (F4.3).

Per unit: predicted net (p10, p50, p90) against realized net, with the
residual and whether the realized value fell inside the range.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, UTC
from typing import Any, Optional
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ChannelPrediction:
    """The predicted net range for one channel on a decision.

    Attributes:
        channel: The channel.
        p10: 10th percentile of predicted net.
        p50: Median of predicted net.
        p90: 90th percentile of predicted net.
        mean: Expected net.
    """

    channel: str
    p10: float
    p50: float
    p90: float
    mean: float = 0.0


@dataclass
class PredictedVsRealized:
    """Comparison of a prediction against what actually happened.

    Attributes:
        unit_id: The unit.
        decision_id: The decision that made the prediction.
        outcome_id: The recorded outcome.
        channel: The channel that was actually used.
        recommended_channel: The channel the engine recommended.
        used_recommended: Whether the outcome used the recommended channel.
        predicted: The predicted net range for the channel that was used.
        realized_net: The realized net.
        residual: realized_net - predicted.p50.
        absolute_residual: |residual|.
        in_range: Whether the realized net fell inside [p10, p90].
        within_p10_p90: Alias of in_range, kept for readability at call sites.
        below_p10: Whether the realized net came in below the p10.
        above_p90: Whether the realized net came in above the p90.
        recorded_at: When the outcome was recorded.
    """

    unit_id: UUID
    decision_id: UUID
    outcome_id: UUID
    channel: str
    recommended_channel: str
    used_recommended: bool
    predicted: ChannelPrediction
    realized_net: float
    residual: float
    absolute_residual: float
    in_range: bool
    within_p10_p90: bool
    below_p10: bool
    above_p90: bool
    recorded_at: datetime


def _prediction_from_candidate(candidate: dict[str, Any]) -> ChannelPrediction:
    """Build a ChannelPrediction from a stored candidate dict."""
    return ChannelPrediction(
        channel=str(candidate.get("channel", "")),
        p10=float(candidate.get("p10", 0.0)),
        p50=float(candidate.get("p50", 0.0)),
        p90=float(candidate.get("p90", 0.0)),
        mean=float(candidate.get("mean", 0.0)),
    )


class PredictedVsRealizedService:
    """Compares what the engine predicted against what actually happened.

    The residual is ``realized_net - predicted_p50``. A positive residual
    means the outcome beat the prediction. The in-range flag says whether the
    realized net landed inside the predicted [p10, p90] band.
    """

    async def compare_unit(
        self,
        session: Any,
        unit_id: UUID,
    ) -> list[PredictedVsRealized]:
        """Compare predictions against outcomes for one unit.

        Args:
            session: Database session.
            unit_id: The unit.

        Returns:
            One comparison per recorded outcome, newest first. Empty when the
            unit has no outcomes.
        """
        from sqlalchemy import desc, select

        from secondroute.decision.models import Decision
        from secondroute.feedback.models import Outcome

        result = await session.execute(
            select(Outcome).where(Outcome.unit_id == unit_id).order_by(desc(Outcome.recorded_at))
        )
        outcomes = result.scalars().all()

        comparisons: list[PredictedVsRealized] = []
        for outcome in outcomes:
            decision = await session.get(Decision, outcome.decision_id)
            if decision is None:
                continue
            comparison = self._compare(decision, outcome)
            if comparison is not None:
                comparisons.append(comparison)

        return comparisons

    async def compare_all(
        self,
        session: Any,
        limit: int = 100,
    ) -> list[PredictedVsRealized]:
        """Compare predictions against outcomes across every unit.

        Args:
            session: Database session.
            limit: Maximum number of outcomes to compare.

        Returns:
            One comparison per recorded outcome, newest first.
        """
        from sqlalchemy import desc, select

        from secondroute.decision.models import Decision
        from secondroute.feedback.models import Outcome

        result = await session.execute(
            select(Outcome, Decision)
            .join(Decision, Outcome.decision_id == Decision.id)
            .order_by(desc(Outcome.recorded_at))
            .limit(limit)
        )
        rows = result.all()

        comparisons: list[PredictedVsRealized] = []
        for outcome, decision in rows:
            comparison = self._compare(decision, outcome)
            if comparison is not None:
                comparisons.append(comparison)

        return comparisons

    def _compare(self, decision: Any, outcome: Any) -> PredictedVsRealized | None:
        """Compare one decision against one outcome.

        Returns:
            The comparison, or None when the decision has no usable
            prediction for the channel that was actually used.
        """
        candidates = decision.candidates or []
        if not candidates:
            return None

        # The prediction we compare against is the one for the channel that
        # was actually used. If the outcome used a channel the decision
        # never evaluated, there is nothing to compare.
        candidate = next(
            (c for c in candidates if c.get("channel") == outcome.channel_taken),
            None,
        )
        if candidate is None:
            return None

        prediction = _prediction_from_candidate(candidate)
        realized = float(outcome.net)
        residual = realized - prediction.p50

        below_p10 = realized < prediction.p10
        above_p90 = realized > prediction.p90
        in_range = prediction.p10 <= realized <= prediction.p90

        return PredictedVsRealized(
            unit_id=outcome.unit_id,
            decision_id=decision.id,
            outcome_id=outcome.id,
            channel=outcome.channel_taken,
            recommended_channel=decision.recommended_channel,
            used_recommended=outcome.channel_taken == decision.recommended_channel,
            predicted=prediction,
            realized_net=realized,
            residual=residual,
            absolute_residual=abs(residual),
            in_range=in_range,
            within_p10_p90=in_range,
            below_p10=below_p10,
            above_p90=above_p90,
            recorded_at=outcome.recorded_at,
        )

    def summarize(
        self,
        comparisons: list[PredictedVsRealized],
    ) -> dict[str, Any]:
        """Summarize a set of comparisons.

        Args:
            comparisons: The comparisons to summarize.

        Returns:
            Aggregate statistics: counts, in-range rate, mean and mean
            absolute residual.
        """
        total = len(comparisons)
        if total == 0:
            return {
                "total": 0,
                "in_range_count": 0,
                "in_range_rate": 0.0,
                "below_p10_count": 0,
                "above_p90_count": 0,
                "used_recommended_count": 0,
                "mean_residual": 0.0,
                "mean_absolute_residual": 0.0,
            }

        in_range = sum(1 for c in comparisons if c.in_range)
        below = sum(1 for c in comparisons if c.below_p10)
        above = sum(1 for c in comparisons if c.above_p90)
        used_recommended = sum(1 for c in comparisons if c.used_recommended)
        mean_residual = sum(c.residual for c in comparisons) / total
        mean_abs = sum(c.absolute_residual for c in comparisons) / total

        return {
            "total": total,
            "in_range_count": in_range,
            "in_range_rate": in_range / total,
            "below_p10_count": below,
            "above_p90_count": above,
            "used_recommended_count": used_recommended,
            "mean_residual": mean_residual,
            "mean_absolute_residual": mean_abs,
        }
