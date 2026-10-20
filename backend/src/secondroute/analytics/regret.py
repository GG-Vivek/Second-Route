"""
Regret calculation for Phase 4 (F4.5).

Regret is the value left on the table by a disposition choice: the best
realized net among the channels that were tried, minus the realized net of
the channel that was actually chosen.

When only one channel was tried there is nothing to compare against, so
the best alternative is taken from the decision's own predictions. That
figure is an *estimate* and is stored under its own flag, so it can never
be silently added to an observed regret.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Sequence
from uuid import UUID

import structlog

from secondroute.analytics.models import RegretKind, RegretMeasurement

logger = structlog.get_logger(__name__)

#: How an observed regret is produced.
OBSERVED_METHOD = "observed-best-realized-net"

#: How an estimated regret is produced.
ESTIMATED_METHOD = "estimated-best-predicted-net"


@dataclass
class RegretEstimate:
    """The regret of one outcome, before it is stored.

    Attributes:
        unit_id: The unit.
        outcome_id: The outcome of the chosen channel.
        decision_id: The decision that produced the choice.
        channel_taken: The channel that was chosen.
        best_channel: The channel that was the best, observed or expected.
        realized_net: The realized net of the chosen channel.
        best_net: The best realized net, or the predicted net of the best
            alternative.
        regret: ``best_net - realized_net``, never negative.
        regret_kind: ``observed`` or ``estimated``.
        method: How the figure was produced.
    """

    unit_id: UUID
    outcome_id: UUID
    decision_id: UUID
    channel_taken: str
    best_channel: str
    realized_net: float
    best_net: float
    regret: float
    regret_kind: str
    method: str

    def as_measurement(
        self,
        *,
        org_id: Optional[UUID] = None,
        is_synthetic: bool = False,
    ) -> RegretMeasurement:
        """Turn the estimate into a storable row.

        Args:
            org_id: The organisation the row belongs to.
            is_synthetic: True when the underlying prices were synthetic.

        Returns:
            The row to append.
        """
        return RegretMeasurement(
            org_id=org_id,
            unit_id=self.unit_id,
            outcome_id=self.outcome_id,
            decision_id=self.decision_id,
            channel_taken=self.channel_taken,
            best_channel=self.best_channel,
            realized_net=self.realized_net,
            best_net=self.best_net,
            regret=self.regret,
            regret_kind=self.regret_kind,
            method=self.method,
            is_synthetic=is_synthetic,
        )


@dataclass
class RegretSummary:
    """The aggregated regret, split by kind.

    Attributes:
        observed_count: How many observed regrets there are.
        observed_total: The summed observed regret.
        observed_mean: The mean observed regret.
        estimated_count: How many estimated regrets there are.
        estimated_total: The summed estimated regret.
        estimated_mean: The mean estimated regret.
    """

    observed_count: int = 0
    observed_total: float = 0.0
    observed_mean: float = 0.0
    estimated_count: int = 0
    estimated_total: float = 0.0
    estimated_mean: float = 0.0

    @property
    def is_mixed(self) -> bool:
        """Whether the summary mixes observed and estimated figures."""
        return self.observed_count > 0 and self.estimated_count > 0

    def to_dict(self) -> dict[str, Any]:
        """Render the summary for the API response.

        Returns:
            The summary, with the observed and the estimated figures kept
            apart and a clearly labelled combined total.
        """
        combined = self.observed_total + self.estimated_total
        return {
            "observed": {
                "count": self.observed_count,
                "total_regret": self.observed_total,
                "mean_regret": self.observed_mean,
            },
            "estimated": {
                "count": self.estimated_count,
                "total_regret": self.estimated_total,
                "mean_regret": self.estimated_mean,
            },
            # The combined figure is never presented on its own: it says
            # what it is made of.
            "combined": {
                "total_regret": combined,
                "is_mixed": self.is_mixed,
                "label": self._label(),
            },
        }

    def _label(self) -> str:
        """Describe what the combined figure is made of.

        Returns:
            The label of the combined total.
        """
        if self.is_mixed:
            return "observed + estimated"
        if self.observed_count:
            return "observed"
        if self.estimated_count:
            return "estimated"
        return "none"


class RegretService:
    """Computes and stores the regret of the recorded outcomes."""

    async def measure_unit(
        self,
        session: Any,
        unit_id: UUID,
    ) -> list[RegretEstimate]:
        """Compute the regret of every outcome recorded for a unit.

        A unit with two or more outcomes has an observed regret: the best
        realized net among the channels that were tried. A unit with a
        single outcome has an estimated regret, taken from the decision's
        own predictions.

        Args:
            session: Database session.
            unit_id: The unit.

        Returns:
            One estimate per outcome of the unit.
        """
        from sqlalchemy import select

        from secondroute.decision.models import Decision
        from secondroute.feedback.models import Outcome

        result = await session.execute(
            select(Outcome).where(Outcome.unit_id == unit_id).order_by(Outcome.recorded_at)
        )
        outcomes = result.scalars().all()

        if not outcomes:
            return []

        decisions: dict[UUID, Any] = {}
        for outcome in outcomes:
            if outcome.decision_id not in decisions:
                decision = await session.get(Decision, outcome.decision_id)
                if decision is not None:
                    decisions[outcome.decision_id] = decision

        return self._estimate(outcomes, decisions)

    async def measure_all(
        self,
        session: Any,
        limit: int = 100,
    ) -> list[RegretEstimate]:
        """Compute the regret of every recorded outcome.

        Args:
            session: Database session.
            limit: Maximum number of outcomes to consider.

        Returns:
            One estimate per outcome, newest first.
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

        # The outcomes of a unit are compared against each other, so they
        # have to be grouped by unit before they are estimated.
        grouped: dict[UUID, list[Any]] = {}
        decisions: dict[UUID, Any] = {}
        for outcome, decision in rows:
            grouped.setdefault(outcome.unit_id, []).append(outcome)
            decisions[decision.id] = decision

        estimates: list[RegretEstimate] = []
        for unit_outcomes in grouped.values():
            estimates.extend(self._estimate(unit_outcomes, decisions))
        return estimates

    def _estimate(
        self,
        outcomes: Any,
        decisions: dict[UUID, Any],
    ) -> list[RegretEstimate]:
        """Estimate the regret of a set of outcomes of the same unit.

        Args:
            outcomes: The outcomes to estimate.
            decisions: The decisions the outcomes belong to, keyed by id.

        Returns:
            One estimate per outcome.
        """
        estimates: list[RegretEstimate] = []
        for outcome in outcomes:
            decision = decisions.get(outcome.decision_id)
            if decision is None:
                continue
            estimates.append(self._estimate_one(outcome, decision, outcomes))
        return estimates

    def _estimate_one(
        self,
        outcome: Any,
        decision: Any,
        siblings: Any,
    ) -> RegretEstimate:
        """Estimate the regret of one outcome against its alternatives.

        Args:
            outcome: The outcome of the chosen channel.
            decision: The decision that produced the choice.
            siblings: The other outcomes of the same unit, when there are
                any.

        Returns:
            The estimate.
        """
        realized = float(outcome.net)
        channel_taken = outcome.channel_taken

        # Observed: the best realized net among the channels that were
        # actually tried.
        best_realized: Optional[float] = None
        best_observed_channel: Optional[str] = None
        for sibling in siblings:
            sibling_net = float(sibling.net)
            if best_realized is None or sibling_net > best_realized:
                best_realized = sibling_net
                best_observed_channel = sibling.channel_taken

        if len(list(siblings)) > 1 and best_realized is not None:
            return RegretEstimate(
                unit_id=outcome.unit_id,
                outcome_id=outcome.id,
                decision_id=decision.id,
                channel_taken=channel_taken,
                best_channel=best_observed_channel or channel_taken,
                realized_net=realized,
                best_net=best_realized,
                regret=max(0.0, best_realized - realized),
                regret_kind=RegretKind.OBSERVED,
                method=OBSERVED_METHOD,
            )

        # Estimated: only one channel was tried, so the best alternative
        # comes from the decision's own predictions.
        predicted_best: Optional[float] = None
        predicted_channel: Optional[str] = None
        for candidate in decision.candidates or []:
            if not candidate.get("eligible"):
                continue
            if candidate.get("channel") == channel_taken:
                continue
            candidate_p50 = float(candidate.get("p50", 0.0))
            if predicted_best is None or candidate_p50 > predicted_best:
                predicted_best = candidate_p50
                predicted_channel = str(candidate.get("channel", ""))

        if predicted_best is None:
            # Nothing to compare against: no candidate, or every candidate
            # was the channel that was taken. There is no regret to report.
            return RegretEstimate(
                unit_id=outcome.unit_id,
                outcome_id=outcome.id,
                decision_id=decision.id,
                channel_taken=channel_taken,
                best_channel=channel_taken,
                realized_net=realized,
                best_net=realized,
                regret=0.0,
                regret_kind=RegretKind.ESTIMATED,
                method=ESTIMATED_METHOD,
            )

        return RegretEstimate(
            unit_id=outcome.unit_id,
            outcome_id=outcome.id,
            decision_id=decision.id,
            channel_taken=channel_taken,
            best_channel=predicted_channel or channel_taken,
            realized_net=realized,
            best_net=predicted_best,
            regret=max(0.0, predicted_best - realized),
            regret_kind=RegretKind.ESTIMATED,
            method=ESTIMATED_METHOD,
        )

    def summarize(self, estimates: Sequence[RegretEstimate]) -> RegretSummary:
        """Summarize a set of regret estimates.

        Args:
            estimates: The estimates to summarize.

        Returns:
            The summary, with observed and estimated kept apart.
        """
        return self._summarize_figures(
            (estimate.regret, estimate.regret_kind) for estimate in estimates
        )

    def summarize_measurements(
        self,
        measurements: Sequence[RegretMeasurement],
    ) -> RegretSummary:
        """Summarize a set of stored regret measurements.

        Args:
            measurements: The measurements to summarize.

        Returns:
            The summary, with observed and estimated kept apart.
        """
        return self._summarize_figures(
            (measurement.regret, measurement.regret_kind) for measurement in measurements
        )

    def _summarize_figures(
        self,
        figures: Iterable[tuple[float, str]],
    ) -> RegretSummary:
        """Summarize regret figures given as ``(regret, kind)`` pairs.

        Args:
            figures: The figures to summarize.

        Returns:
            The summary, with observed and estimated kept apart.
        """
        summary = RegretSummary()
        for regret, regret_kind in figures:
            if regret_kind == RegretKind.OBSERVED:
                summary.observed_count += 1
                summary.observed_total += regret
            else:
                summary.estimated_count += 1
                summary.estimated_total += regret

        if summary.observed_count:
            summary.observed_mean = summary.observed_total / summary.observed_count
        if summary.estimated_count:
            summary.estimated_mean = summary.estimated_total / summary.estimated_count

        return summary
