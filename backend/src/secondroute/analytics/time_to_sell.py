"""
Time-to-sell model for Phase 4 (F4.4).

Kaplan-Meier survival curves of days-to-disposition, computed from the
recorded outcomes, grouped by the channel the unit actually went to and the
cosmetic grade of its inspection.

When a cell has fewer observations than the configured minimum, the curve
falls back to the prior seeded in Phase 3 (``cost_tables`` rows of kind
``expected_days_to_sell``), and the response says so explicitly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional, Sequence
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)

#: Outcome statuses that count as the event of interest ("the unit sold").
SOLD_STATUSES = frozenset({"sold", "sold_online", "sold_offline"})

#: Default minimum number of observations before a cell is trusted.
DEFAULT_MIN_SAMPLE = 10


@dataclass(frozen=True)
class Observation:
    """One unit's disposition outcome.

    Attributes:
        duration_days: Days from intake to disposition.
        event: True when the unit was sold (the event of interest). False
            when the observation is censored, for example a unit that was
            recycled or donated before it sold.
        channel: The channel the unit actually went to.
        grade: The cosmetic grade of the inspection.
    """

    duration_days: int
    event: bool
    channel: str
    grade: str


@dataclass(frozen=True)
class SurvivalCurve:
    """A Kaplan-Meier survival curve.

    Attributes:
        times: The distinct times at which the curve steps down.
        survival: The survival probability after each time in ``times``.
        at_risk: The number of units still at risk just before each time.
        events: The number of events at each time.
        censored: The number of censored observations at each time.
        sample_size: The number of observations the curve was built from.
    """

    times: list[int] = field(default_factory=list)
    survival: list[float] = field(default_factory=list)
    at_risk: list[int] = field(default_factory=list)
    events: list[int] = field(default_factory=list)
    censored: list[int] = field(default_factory=list)
    sample_size: int = 0

    @property
    def is_empty(self) -> bool:
        """Whether the curve has no steps at all."""
        return not self.times


@dataclass(frozen=True)
class TimeToSellCell:
    """The time-to-sell estimate for one channel and grade.

    Attributes:
        channel: The channel.
        grade: The cosmetic grade.
        sample_size: How many outcomes back this cell.
        used_fallback: True when the sample was too small and the prior was
            used instead of a curve.
        curve: The Kaplan-Meier curve. Empty when the prior was used.
        median_days: The median time to sell, in days.
        p25_days: The 25th percentile of the time to sell.
        p75_days: The 75th percentile of the time to sell.
        expected_days: The fallback prior, in days. None when the curve was
            used.
        source: Where the numbers came from - ``outcomes`` for a curve,
            ``cost_tables`` for the prior.
        as_of: The date the numbers are current as of.
    """

    channel: str
    grade: str
    sample_size: int
    used_fallback: bool
    curve: SurvivalCurve
    median_days: Optional[int]
    p25_days: Optional[int]
    p75_days: Optional[int]
    expected_days: Optional[float]
    source: str
    as_of: Optional[date]


def kaplan_meier(observations: Sequence[Observation]) -> SurvivalCurve:
    """Build the Kaplan-Meier survival curve of the time to sell.

    The event of interest is "the unit sold". Everything else is censored:
    a unit that was recycled after 5 days was never going to sell, so it
    leaves the risk set without being an event.

    At every distinct duration ``t``:

    * ``n`` is the number of units still at risk just before ``t``
    * ``d`` is the number of units sold at ``t``
    * the survival probability is multiplied by ``(n - d) / n``
    * the risk set then loses ``d + c`` units, where ``c`` is the number
      censored at ``t``

    Args:
        observations: The observations to summarise.

    Returns:
        The survival curve. Empty when there are no observations.
    """
    if not observations:
        return SurvivalCurve()

    ordered = sorted(observations, key=lambda obs: obs.duration_days)
    distinct_times = sorted({obs.duration_days for obs in ordered})

    times: list[int] = []
    survival: list[float] = []
    at_risk: list[int] = []
    events: list[int] = []
    censored: list[int] = []

    current_survival = 1.0
    still_at_risk = len(ordered)

    for time in distinct_times:
        at_this_time = [obs for obs in ordered if obs.duration_days == time]
        deaths = sum(1 for obs in at_this_time if obs.event)
        censors = len(at_this_time) - deaths

        if still_at_risk > 0:
            current_survival *= (still_at_risk - deaths) / still_at_risk

        times.append(time)
        survival.append(round(current_survival, 6))
        at_risk.append(still_at_risk)
        events.append(deaths)
        censored.append(censors)

        still_at_risk -= deaths + censors

    return SurvivalCurve(
        times=times,
        survival=survival,
        at_risk=at_risk,
        events=events,
        censored=censored,
        sample_size=len(ordered),
    )


def survival_percentile(curve: SurvivalCurve, percentile: float) -> Optional[int]:
    """Return the first time the survival curve drops to ``percentile``.

    Args:
        curve: The curve to read.
        percentile: The survival probability to look for, between 0 and 1.

    Returns:
        The time in days, or None when the curve never drops that far.
    """
    if not 0.0 <= percentile <= 1.0:
        raise ValueError("percentile must be between 0 and 1")

    for time, survival in zip(curve.times, curve.survival, strict=False):
        if survival <= percentile:
            return time
    return None


def survival_median(curve: SurvivalCurve) -> Optional[int]:
    """Return the median time to sell, in days.

    Args:
        curve: The curve to read.

    Returns:
        The median in days, or None when the curve never drops to 0.5.
    """
    return survival_percentile(curve, 0.5)


def is_sold(final_status: str) -> bool:
    """Whether an outcome status counts as the unit having sold.

    Args:
        final_status: The recorded final status.

    Returns:
        True when the unit sold.
    """
    return final_status.strip().lower() in SOLD_STATUSES


class TimeToSellService:
    """Builds the time-to-sell curves from the recorded outcomes."""

    async def curves(
        self,
        session: Any,
        *,
        channel: Optional[str] = None,
        grade: Optional[str] = None,
        min_sample: int = DEFAULT_MIN_SAMPLE,
    ) -> list[TimeToSellCell]:
        """Build one time-to-sell cell per channel and grade.

        Args:
            session: Database session.
            channel: Restrict to a single channel.
            grade: Restrict to a single grade.
            min_sample: The smallest sample a cell needs before its curve is
                trusted. Below it, the prior is used.

        Returns:
            One cell per channel and grade that has at least one outcome.
        """
        observations = await self._load_observations(session, channel=channel, grade=grade)
        priors = await self._load_priors(session)

        cells: list[TimeToSellCell] = []
        grouped: dict[tuple[str, str], list[Observation]] = {}
        for observation in observations:
            grouped.setdefault((observation.channel, observation.grade), []).append(observation)

        for (cell_channel, cell_grade), cell_observations in sorted(grouped.items()):
            curve = kaplan_meier(cell_observations)
            prior_days, prior_as_of = priors.get((cell_channel, cell_grade), (None, None))

            if len(cell_observations) < min_sample:
                cells.append(
                    TimeToSellCell(
                        channel=cell_channel,
                        grade=cell_grade,
                        sample_size=len(cell_observations),
                        used_fallback=True,
                        curve=SurvivalCurve(),
                        median_days=None,
                        p25_days=None,
                        p75_days=None,
                        expected_days=prior_days,
                        source="cost_tables",
                        as_of=prior_as_of,
                    )
                )
                continue

            cells.append(
                TimeToSellCell(
                    channel=cell_channel,
                    grade=cell_grade,
                    sample_size=len(cell_observations),
                    used_fallback=False,
                    curve=curve,
                    median_days=survival_median(curve),
                    p25_days=survival_percentile(curve, 0.25),
                    p75_days=survival_percentile(curve, 0.75),
                    expected_days=None,
                    source="outcomes",
                    as_of=None,
                )
            )

        return cells

    async def _load_observations(
        self,
        session: Any,
        *,
        channel: Optional[str],
        grade: Optional[str],
    ) -> list[Observation]:
        """Load the outcomes, joined with the grade of the inspection."""
        from sqlalchemy import Select, cast, select
        from sqlalchemy import String

        from secondroute.feedback.models import Outcome
        from secondroute.intake.models import Inspection

        query: Select[str, int, str, str] = (
            select(
                Outcome.channel_taken,
                Outcome.days_to_disposition,
                Outcome.final_status,
                cast(Inspection.cosmetic_grade, String),
            )
            .join(Inspection, Inspection.unit_id == Outcome.unit_id)
            .order_by(Outcome.recorded_at)
        )
        if channel:
            query = query.where(Outcome.channel_taken == channel)
        if grade:
            query = query.where(Inspection.cosmetic_grade == grade)

        result = await session.execute(query)
        rows = result.all()

        observations: list[Observation] = []
        for row in rows:
            if row.cosmetic_grade is None:
                continue
            observations.append(
                Observation(
                    duration_days=int(row.days_to_disposition),
                    event=is_sold(row.final_status),
                    channel=row.channel_taken,
                    grade=row.cosmetic_grade,
                )
            )
        return observations

    async def _load_priors(
        self,
        session: Any,
    ) -> dict[tuple[str, str], tuple[Optional[float], Optional[date]]]:
        """Load the Phase 3 priors of expected days to sell.

        Returns:
            A mapping of ``(channel, grade)`` to the prior in days and the
            date the prior is current as of.
        """
        from sqlalchemy import select

        from secondroute.costs.models import CostKind, CostTable

        result = await session.execute(
            select(CostTable.key, CostTable.value, CostTable.as_of).where(
                CostTable.kind == CostKind.EXPECTED_DAYS_TO_SELL
            )
        )

        priors: dict[tuple[str, str], tuple[Optional[float], Optional[date]]] = {}
        for key, value, as_of in result.all():
            channel, _, grade = key.partition(":")
            if not grade:
                continue
            priors[(channel, grade)] = (float(value), as_of)
        return priors


def cell_to_dict(cell: TimeToSellCell) -> dict[str, Any]:
    """Turn a time-to-sell cell into a JSON-ready dict.

    Args:
        cell: The cell to render.

    Returns:
        The dict for the API response.
    """
    return {
        "channel": cell.channel,
        "grade": cell.grade,
        "sample_size": cell.sample_size,
        "used_fallback": cell.used_fallback,
        "median_days": cell.median_days,
        "p25_days": cell.p25_days,
        "p75_days": cell.p75_days,
        "expected_days": cell.expected_days,
        "source": cell.source,
        "as_of": cell.as_of,
        "curve": {
            "times": cell.curve.times,
            "survival": cell.curve.survival,
            "at_risk": cell.curve.at_risk,
            "events": cell.curve.events,
            "censored": cell.curve.censored,
        },
    }
