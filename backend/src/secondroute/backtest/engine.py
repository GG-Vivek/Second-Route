"""
The historical backtest (Phase 5 - F5.6).

Replays past decisions and compares the engine's channel against the
partner's baseline policy, using only the information each decision had at
the time it was made.

What "no look-ahead" means here, concretely:

- Every decision is checked before it is replayed. If any price, cost or
  snapshot the decision used is dated after the decision was made, the run
  is refused. A backtest that cannot prove it had no look-ahead is not
  reported at all.
- The nets being compared are the ones the engine computed at decision
  time, recorded on the decision itself. Nothing is recomputed from
  today's data, so the comparison cannot pick up anything the decision did
  not already know.

The comparison is a paired one: both policies are scored on the same unit,
and the unit's difference is the observation. A paired bootstrap over those
differences gives the interval around the mean difference.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.backtest.baseline import (
    BaselinePolicy,
    FixedChannelBaseline,
    MostCommonChannelBaseline,
)
from secondroute.backtest.bootstrap import (
    BootstrapError,
    ConfidenceInterval,
    bootstrap_mean_ci,
)
from secondroute.backtest.lookahead import (
    LookAheadError,
    LookAheadReport,
    check_decision_with_relations,
    combine_reports,
)

__all__ = [
    "BacktestResult",
    "BacktestRunError",
    "SkippedDecision",
    "run_backtest",
]


class BacktestRunError(RuntimeError):
    """Raised when a backtest cannot be run."""


@dataclass(frozen=True, slots=True)
class SkippedDecision:
    """A decision that was left out of the comparison, and why.

    Attributes:
        decision_id: The decision that was skipped.
        reason: Why it was skipped.
    """

    decision_id: str
    reason: str

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-serialisable view of the skip."""
        return {"decision_id": self.decision_id, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """The outcome of a backtest.

    Attributes:
        baseline_name: Identifies the baseline policy that was compared.
        baseline_description: What the baseline does.
        baseline_channel: The channel the baseline chose, when it has one.
        decision_count: How many decisions took part in the comparison.
        skipped: The decisions that were left out, and why.
        mean_engine_net: Mean modelled net of the engine's channel.
        mean_baseline_net: Mean modelled net of the baseline's channel.
        mean_difference: The paired mean difference in net, per unit.
        interval: The bootstrap interval around ``mean_difference``.
        confidence: The confidence level of the interval.
        method: How the interval was produced.
        win_rate: Share of units where the engine's channel modelled a
            higher net than the baseline's.
        channel_breakdown: Per-channel counts of engine and baseline picks.
        lookahead: The look-ahead check that was run over the decisions.
        window_start: Earliest decision time in scope.
        window_end: Latest decision time in scope.
        warnings: Things a reader needs to know about the result.
    """

    baseline_name: str
    baseline_description: str
    baseline_channel: str | None
    decision_count: int
    skipped: tuple[SkippedDecision, ...] = ()
    mean_engine_net: float | None = None
    mean_baseline_net: float | None = None
    mean_difference: float | None = None
    interval: ConfidenceInterval | None = None
    confidence: float = 0.95
    method: str = "paired-bootstrap-percentile"
    win_rate: float | None = None
    channel_breakdown: dict[str, dict[str, int]] = field(default_factory=dict)
    lookahead: LookAheadReport | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of the result."""
        return {
            "baseline_name": self.baseline_name,
            "baseline_description": self.baseline_description,
            "baseline_channel": self.baseline_channel,
            "decision_count": self.decision_count,
            "skipped": [skip.as_dict() for skip in self.skipped],
            "mean_engine_net": _round(self.mean_engine_net),
            "mean_baseline_net": _round(self.mean_baseline_net),
            "mean_difference": _round(self.mean_difference),
            "interval": self.interval.as_dict() if self.interval else None,
            "confidence": self.confidence,
            "method": self.method,
            "win_rate": _round(self.win_rate),
            "channel_breakdown": self.channel_breakdown,
            "lookahead": self.lookahead.as_dict() if self.lookahead else None,
            "window_start": self.window_start.isoformat() if self.window_start else None,
            "window_end": self.window_end.isoformat() if self.window_end else None,
            "warnings": list(self.warnings),
        }


def _round(value: float | None) -> float | None:
    """Round a value for reporting, leaving ``None`` alone."""
    return None if value is None else round(value, 4)


def _candidate_nets(decision: Any) -> tuple[dict[str, float], set[str]]:
    """Return the modelled net per eligible channel, and the blocked ones.

    The candidates are the evaluations the engine computed when it made the
    decision. Reading them back is what keeps the backtest free of
    look-ahead: no price or cost is looked up again.

    A channel that was not eligible for the unit has no meaningful net - the
    engine records a placeholder zero for it - so it is reported separately
    rather than compared.

    Returns:
        The net per eligible channel, and the set of blocked channels.
    """
    candidates = getattr(decision, "candidates", None)
    if candidates is None:
        raw = getattr(decision, "candidates_json", "[]")
        import json

        try:
            candidates = json.loads(raw)
        except (TypeError, ValueError):
            candidates = []

    nets: dict[str, float] = {}
    blocked: set[str] = set()
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        channel = candidate.get("channel")
        if not channel:
            continue
        channel = str(channel)
        if not candidate.get("eligible", True):
            blocked.add(channel)
            continue
        net = candidate.get("mean")
        if net is None:
            breakdown = candidate.get("breakdown")
            if isinstance(breakdown, dict):
                net = breakdown.get("net")
        if net is None:
            continue
        try:
            nets[channel] = float(net)
        except (TypeError, ValueError):
            continue
    return nets, blocked


async def _load_decisions(
    session: AsyncSession,
    *,
    org_id: Any,
    window_start: datetime | None,
    window_end: datetime | None,
    unit_ids: Sequence[Any] | None,
) -> list[Any]:
    """Load the decisions in scope, oldest first."""
    from secondroute.decision.models import Decision

    statement = select(Decision).where(Decision.org_id == org_id)
    if window_start is not None:
        statement = statement.where(Decision.created_at >= window_start)
    if window_end is not None:
        statement = statement.where(Decision.created_at <= window_end)
    if unit_ids:
        statement = statement.where(Decision.unit_id.in_(list(unit_ids)))
    statement = statement.order_by(Decision.created_at.asc())

    result = await session.execute(statement)
    return list(result.scalars().all())


async def _partner_channel_counts(
    session: AsyncSession, decisions: Sequence[Any]
) -> dict[str, int]:
    """Count the channels the partner actually took on these decisions.

    The partner's habit is read from the recorded outcomes rather than
    assumed, so the baseline describes what the partner really did.
    """
    from secondroute.feedback.models import Outcome

    decision_ids = [decision.id for decision in decisions]
    if not decision_ids:
        return {}

    result = await session.execute(
        select(Outcome.channel_taken, Outcome.decision_id).where(
            Outcome.decision_id.in_(decision_ids)
        )
    )
    counts: dict[str, int] = {}
    for channel, _decision_id in result.all():
        if channel:
            counts[str(channel)] = counts.get(str(channel), 0) + 1
    return counts


def _resolve_baseline(
    baseline: BaselinePolicy,
    partner_counts: dict[str, int],
) -> BaselinePolicy:
    """Fill in a baseline that needs the partner's behaviour to answer.

    The most-common-channel baseline reads the channel the partner used
    most often; until the runner has seen the outcomes it has no answer.
    """
    if isinstance(baseline, MostCommonChannelBaseline) and not baseline.counts:
        return MostCommonChannelBaseline(counts=dict(partner_counts))
    return baseline


@dataclass(slots=True)
class _Comparison:
    """The outcome of comparing the two policies over a set of decisions."""

    engine_nets: list[float] = field(default_factory=list)
    baseline_nets: list[float] = field(default_factory=list)
    differences: list[float] = field(default_factory=list)
    skipped: list[SkippedDecision] = field(default_factory=list)
    channel_breakdown: dict[str, dict[str, int]] = field(default_factory=dict)
    baseline_channel: str | None = None


def _compare_decisions(decisions: Sequence[Any], policy: BaselinePolicy) -> _Comparison:
    """Compare the engine's channel against the baseline on each decision.

    A decision that cannot be compared is skipped with a reason, rather
    than being dropped silently or counted as a zero difference.
    """
    comparison = _Comparison()

    for decision in decisions:
        decision_id = str(decision.id)
        nets, blocked = _candidate_nets(decision)
        if not nets:
            comparison.skipped.append(
                SkippedDecision(
                    decision_id=decision_id,
                    reason="The decision recorded no eligible channel evaluations.",
                )
            )
            continue

        engine_channel = decision.recommended_channel
        engine_net = nets.get(engine_channel)
        if engine_net is None:
            comparison.skipped.append(
                SkippedDecision(
                    decision_id=decision_id,
                    reason=(f"The recommended channel {engine_channel} has no recorded net value."),
                )
            )
            continue

        baseline_channel = policy.channel_for(decision)
        if baseline_channel is None:
            comparison.skipped.append(
                SkippedDecision(
                    decision_id=decision_id,
                    reason="The baseline policy has no answer for this decision.",
                )
            )
            continue

        baseline_net = nets.get(baseline_channel)
        if baseline_net is None:
            reason = (
                f"The baseline channel {baseline_channel} was not eligible for this unit, "
                f"so it could not have been used."
                if baseline_channel in blocked
                else (
                    f"The baseline channel {baseline_channel} was not evaluated for this "
                    f"decision, so it cannot be compared."
                )
            )
            comparison.skipped.append(SkippedDecision(decision_id=decision_id, reason=reason))
            continue

        comparison.engine_nets.append(engine_net)
        comparison.baseline_nets.append(baseline_net)
        comparison.differences.append(engine_net - baseline_net)
        comparison.baseline_channel = baseline_channel

        breakdown = comparison.channel_breakdown.setdefault(
            engine_channel, {"engine": 0, "baseline": 0}
        )
        breakdown["engine"] += 1
        baseline_breakdown = comparison.channel_breakdown.setdefault(
            baseline_channel, {"engine": 0, "baseline": 0}
        )
        baseline_breakdown["baseline"] += 1

    return comparison


async def run_backtest(
    session: AsyncSession,
    *,
    org_id: Any,
    baseline: BaselinePolicy | None = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    unit_ids: Sequence[Any] | None = None,
    confidence: float = 0.95,
    samples: int = 10_000,
    seed: int = 0,
    require_provenance: bool = True,
) -> BacktestResult:
    """Replay past decisions and compare the engine against a baseline.

    Args:
        session: Database session.
        org_id: The organisation whose decisions are replayed.
        baseline: The policy to compare against. Defaults to a fixed channel
            baseline on the engine's own recommendation, which measures only
            how much the confidence gate and the ranking move the answer.
        window_start: Earliest decision time to include.
        window_end: Latest decision time to include.
        unit_ids: Restrict the replay to these units.
        confidence: Confidence level of the interval.
        samples: Number of bootstrap resamples.
        seed: RNG seed for the bootstrap.
        require_provenance: Whether a decision that records no as-of date is
            treated as a finding.

    Returns:
        The result of the comparison.

    Raises:
        LookAheadError: If any decision in scope used data dated after it
            was made. The backtest is refused rather than reported.
        BacktestRunError: If the arguments are not usable.
    """
    if org_id is None:
        raise BacktestRunError("A backtest needs an organisation to replay")

    policy = baseline or FixedChannelBaseline(channel="LIQUIDATE")
    decisions = await _load_decisions(
        session,
        org_id=org_id,
        window_start=window_start,
        window_end=window_end,
        unit_ids=unit_ids,
    )

    if not decisions:
        return BacktestResult(
            baseline_name=policy.name,
            baseline_description=policy.description,
            baseline_channel=None,
            decision_count=0,
            confidence=confidence,
            warnings=(
                "No decisions fall in the requested window, so there is nothing to compare.",
            ),
        )

    policy = _resolve_baseline(policy, await _partner_channel_counts(session, decisions))

    # Check every decision for look-ahead before comparing anything. A
    # backtest that cannot prove it had no look-ahead is not reported.
    reports = []
    for decision in decisions:
        reports.append(
            await check_decision_with_relations(
                session, decision, require_provenance=require_provenance
            )
        )
    lookahead = combine_reports(reports)
    if lookahead.has_leak:
        raise LookAheadError(lookahead)

    comparison = _compare_decisions(decisions, policy)
    skipped = comparison.skipped
    engine_nets = comparison.engine_nets
    baseline_nets = comparison.baseline_nets
    differences = comparison.differences

    warnings: list[str] = []
    interval: ConfidenceInterval | None = None
    mean_difference: float | None = None
    win_rate: float | None = None

    if differences:
        mean_difference = sum(differences) / len(differences)
        win_rate = sum(1 for value in differences if value > 0) / len(differences)
        try:
            interval = bootstrap_mean_ci(
                differences, confidence=confidence, samples=samples, seed=seed
            )
        except BootstrapError as error:
            warnings.append(f"No interval could be computed: {error}")
    else:
        warnings.append(
            "No decision could be compared, so the engine and the baseline have no "
            "difference to report."
        )

    if skipped:
        warnings.append(
            f"{len(skipped)} decision(s) were left out of the comparison; see 'skipped'."
        )

    return BacktestResult(
        baseline_name=policy.name,
        baseline_description=policy.description,
        baseline_channel=comparison.baseline_channel,
        decision_count=len(differences),
        skipped=tuple(skipped),
        mean_engine_net=sum(engine_nets) / len(engine_nets) if engine_nets else None,
        mean_baseline_net=sum(baseline_nets) / len(baseline_nets) if baseline_nets else None,
        mean_difference=mean_difference,
        interval=interval,
        confidence=confidence,
        method="paired-bootstrap-percentile",
        win_rate=win_rate,
        channel_breakdown=comparison.channel_breakdown,
        lookahead=lookahead,
        window_start=decisions[0].created_at,
        window_end=decisions[-1].created_at,
        warnings=tuple(warnings),
    )
