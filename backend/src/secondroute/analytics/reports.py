"""
The reports behind the analytics page (Phase 4 - F4.7).

Three reports: the north star (the net recovered per return above the
baseline), the regret over time and the override rate by reason.

Synthetic and real data are never merged. Every report is returned once
for the synthetic data and once for the real data, and the caller has to
choose which one to show.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)

#: The channel the baseline is measured against: the salvage default.
BASELINE_CHANNEL = "RECYCLE"

#: The two kinds of data a report is split into.
DATA_KINDS = ("synthetic", "real")


@dataclass
class NorthStarSection:
    """The north star of one kind of data.

    Attributes:
        returns_count: How many returns there were.
        net_recovered_total: The summed realized net of the chosen
            channels.
        baseline_total: The summed baseline the choices beat.
        net_recovered_per_return: The mean realized net per return.
        baseline_per_return: The mean baseline per return.
        above_baseline_per_return: The mean gap per return.
        observed_baseline_count: How many returns had the baseline channel
            actually tried, so the baseline is a fact.
        estimated_baseline_count: How many returns had the baseline taken
            from the model, so the baseline is an estimate.
    """

    returns_count: int = 0
    net_recovered_total: float = 0.0
    baseline_total: float = 0.0
    net_recovered_per_return: float = 0.0
    baseline_per_return: float = 0.0
    above_baseline_per_return: float = 0.0
    observed_baseline_count: int = 0
    estimated_baseline_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Render the section for the API response.

        Returns:
            The section.
        """
        return {
            "returns_count": self.returns_count,
            "net_recovered_total": round(self.net_recovered_total, 2),
            "baseline_total": round(self.baseline_total, 2),
            "net_recovered_per_return": round(self.net_recovered_per_return, 2),
            "baseline_per_return": round(self.baseline_per_return, 2),
            "above_baseline_per_return": round(self.above_baseline_per_return, 2),
            "observed_baseline_count": self.observed_baseline_count,
            "estimated_baseline_count": self.estimated_baseline_count,
        }


@dataclass
class RegretBucket:
    """The regret of one period.

    Attributes:
        period: The period, as ``YYYY-MM``.
        count: How many measurements the period holds.
        mean_regret: The mean regret of the period.
        observed_count: How many of them were observed.
        estimated_count: How many of them were estimated.
        observed_mean_regret: The mean of the observed ones.
        estimated_mean_regret: The mean of the estimated ones.
    """

    period: str
    count: int = 0
    mean_regret: float = 0.0
    observed_count: int = 0
    estimated_count: int = 0
    observed_mean_regret: float = 0.0
    estimated_mean_regret: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Render the bucket for the API response.

        Returns:
            The bucket.
        """
        return {
            "period": self.period,
            "count": self.count,
            "mean_regret": round(self.mean_regret, 2),
            "observed_count": self.observed_count,
            "estimated_count": self.estimated_count,
            "observed_mean_regret": round(self.observed_mean_regret, 2),
            "estimated_mean_regret": round(self.estimated_mean_regret, 2),
        }


@dataclass
class ReasonCount:
    """How often one override reason was given.

    Attributes:
        reason: The reason, as it was written down.
        count: How many overrides used it.
        share: The share of all the overrides.
    """

    reason: str
    count: int = 0
    share: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Render the count for the API response.

        Returns:
            The count.
        """
        return {"reason": self.reason, "count": self.count, "share": round(self.share, 4)}


@dataclass
class OverrideRateSection:
    """The override rate of one kind of data.

    Attributes:
        decisions_count: How many decisions were made.
        overrides_count: How many of them were overridden.
        override_rate: The share of decisions that were overridden.
        by_reason: The reasons, most used first.
    """

    decisions_count: int = 0
    overrides_count: int = 0
    override_rate: float = 0.0
    by_reason: list[ReasonCount] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Render the section for the API response.

        Returns:
            The section.
        """
        return {
            "decisions_count": self.decisions_count,
            "overrides_count": self.overrides_count,
            "override_rate": round(self.override_rate, 4),
            "by_reason": [reason.to_dict() for reason in self.by_reason],
        }


def decision_is_synthetic(decision: Any) -> bool:
    """Whether a decision was made with synthetic prices.

    Args:
        decision: The decision.

    Returns:
        True when the decision was made with synthetic data.
    """
    freshness = getattr(decision, "data_freshness", None)
    if not isinstance(freshness, dict):
        return False
    return bool(freshness.get("is_synthetic", False))


def _candidate_p50(decision: Any, channel: str) -> Optional[float]:
    """Return the predicted p50 net of a channel, when the decision has it.

    Args:
        decision: The decision.
        channel: The channel to look for.

    Returns:
        The predicted net, or None when the decision has no candidate for
        the channel.
    """
    for candidate in getattr(decision, "candidates", None) or []:
        if candidate.get("channel") == channel:
            return float(candidate.get("p50", 0.0))
    return None


class AnalyticsReportService:
    """Builds the reports of the analytics page."""

    async def north_star(self, session: Any) -> dict[str, NorthStarSection]:
        """Build the north star, split into synthetic and real.

        The recovered value is the realized net of the channel that was
        actually used. The baseline is the salvage default, ``RECYCLE``:
        its realized net when that channel was tried for the unit, and the
        model's prediction for it when it was not. The two are counted
        apart, so the estimate is never mistaken for a measurement.

        Args:
            session: Database session.

        Returns:
            One section per kind of data.
        """
        from sqlalchemy import select

        from secondroute.decision.models import Decision
        from secondroute.feedback.models import Outcome

        result = await session.execute(
            select(Outcome, Decision)
            .join(Decision, Outcome.decision_id == Decision.id)
            .order_by(Outcome.recorded_at)
        )
        rows = result.all()

        # The baseline channel, when it was tried for the unit, is a fact.
        baseline_by_unit: dict[UUID, float] = {}
        for outcome, _decision in rows:
            if outcome.channel_taken != BASELINE_CHANNEL:
                continue
            realized = float(outcome.net)
            current = baseline_by_unit.get(outcome.unit_id)
            if current is None or realized > current:
                baseline_by_unit[outcome.unit_id] = realized

        sections = {kind: NorthStarSection() for kind in DATA_KINDS}
        for outcome, decision in rows:
            kind = "synthetic" if decision_is_synthetic(decision) else "real"
            section = sections[kind]

            recovered = float(outcome.net)
            baseline = baseline_by_unit.get(outcome.unit_id)
            if baseline is None:
                predicted = _candidate_p50(decision, BASELINE_CHANNEL)
                if predicted is None:
                    # There is no baseline to compare against, so the return
                    # does not count towards the above-baseline figure.
                    continue
                baseline = predicted
                section.estimated_baseline_count += 1
            else:
                section.observed_baseline_count += 1

            section.returns_count += 1
            section.net_recovered_total += recovered
            section.baseline_total += baseline

        for section in sections.values():
            if section.returns_count:
                section.net_recovered_per_return = (
                    section.net_recovered_total / section.returns_count
                )
                section.baseline_per_return = section.baseline_total / section.returns_count
                section.above_baseline_per_return = (
                    section.net_recovered_total - section.baseline_total
                ) / section.returns_count

        return sections

    async def regret_over_time(
        self,
        session: Any,
        *,
        bucket: str = "month",
    ) -> dict[str, list[RegretBucket]]:
        """Build the regret over time, split into synthetic and real.

        Args:
            session: Database session.
            bucket: ``month`` or ``week``.

        Returns:
            One list of buckets per kind of data.
        """
        from sqlalchemy import select

        from secondroute.analytics.models import RegretKind, RegretMeasurement
        from secondroute.decision.models import Decision

        result = await session.execute(
            select(RegretMeasurement, Decision)
            .join(Decision, RegretMeasurement.decision_id == Decision.id)
            .order_by(RegretMeasurement.created_at)
        )
        rows = result.all()

        grouped: dict[tuple[str, str], RegretBucket] = {}
        for measurement, decision in rows:
            kind = "synthetic" if decision_is_synthetic(decision) else "real"
            period = _period(measurement.created_at, bucket)
            key = (kind, period)
            bucket_row = grouped.get(key)
            if bucket_row is None:
                bucket_row = RegretBucket(period=period)
                grouped[key] = bucket_row

            bucket_row.count += 1
            bucket_row.mean_regret += measurement.regret
            if measurement.regret_kind == RegretKind.OBSERVED:
                bucket_row.observed_count += 1
                bucket_row.observed_mean_regret += measurement.regret
            else:
                bucket_row.estimated_count += 1
                bucket_row.estimated_mean_regret += measurement.regret

        sections: dict[str, list[RegretBucket]] = {kind: [] for kind in DATA_KINDS}
        for (kind, _period_key), bucket_row in sorted(grouped.items()):
            bucket_row.mean_regret = bucket_row.mean_regret / bucket_row.count
            if bucket_row.observed_count:
                bucket_row.observed_mean_regret /= bucket_row.observed_count
            if bucket_row.estimated_count:
                bucket_row.estimated_mean_regret /= bucket_row.estimated_count
            sections[kind].append(bucket_row)

        return sections

    async def override_rate(self, session: Any) -> dict[str, OverrideRateSection]:
        """Build the override rate by reason, split into synthetic and real.

        Args:
            session: Database session.

        Returns:
            One section per kind of data.
        """
        from sqlalchemy import select

        from secondroute.decision.models import Decision
        from secondroute.feedback.models import Override

        decisions = await session.execute(select(Decision))
        decision_rows = decisions.scalars().all()

        synthetic_decision_ids = {
            decision.id for decision in decision_rows if decision_is_synthetic(decision)
        }
        decision_kind = {
            decision.id: ("synthetic" if decision.id in synthetic_decision_ids else "real")
            for decision in decision_rows
        }

        overrides = await session.execute(select(Override))
        override_rows = overrides.scalars().all()

        sections: dict[str, OverrideRateSection] = {
            kind: OverrideRateSection() for kind in DATA_KINDS
        }
        reasons: dict[str, dict[str, int]] = {kind: {} for kind in DATA_KINDS}

        for decision in decision_rows:
            kind = decision_kind[decision.id]
            sections[kind].decisions_count += 1

        for override in override_rows:
            kind = decision_kind.get(override.decision_id, "real")
            section = sections[kind]
            section.overrides_count += 1
            reason = override.reason_text.strip() or "(no reason given)"
            reasons[kind][reason] = reasons[kind].get(reason, 0) + 1

        for kind, section in sections.items():
            if section.decisions_count:
                section.override_rate = section.overrides_count / section.decisions_count
            total = sum(reasons[kind].values())
            section.by_reason = [
                ReasonCount(
                    reason=reason,
                    count=count,
                    share=(count / total) if total else 0.0,
                )
                for reason, count in sorted(
                    reasons[kind].items(), key=lambda item: (-item[1], item[0])
                )
            ]

        return sections


def _period(moment: datetime, bucket: str) -> str:
    """Return the period a moment falls into.

    Args:
        moment: The moment.
        bucket: ``month`` or ``week``.

    Returns:
        The period, as ``YYYY-MM`` or ``YYYY-Www``.
    """
    if bucket == "week":
        year, week, _ = moment.isocalendar()
        return f"{year}-W{week:02d}"
    return moment.strftime("%Y-%m")


def parse_candidates(raw: str) -> list[dict[str, Any]]:
    """Parse a stored candidates payload.

    Args:
        raw: The JSON string.

    Returns:
        The candidates, or an empty list when the payload is unusable.
    """
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]
