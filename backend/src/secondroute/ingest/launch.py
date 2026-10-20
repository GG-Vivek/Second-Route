"""
Launch calendar and the HOLD channel (Phase 3 - F3.8).

A unit can be worth more later than it is worth now. When a new model is
about to launch, the outgoing model's resale price usually falls - so holding
is a bad idea. But when a price is rising and nothing is about to launch,
holding a unit for a few weeks can be worth more than selling it today.

So HOLD is only offered when both of these hold:

1. The expected change over the hold window is **positive at p50** - the
   median outcome of holding is better than selling now.
2. The probability of a launch inside the window is **below** the threshold.

The decay rate per family and grade is fitted from the price observations
over time, so the "expected change" comes from the data rather than from a
guess.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone, UTC
from typing import Any, Final, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.logging import get_logger
from secondroute.ingest.models import DecayParam, LaunchEvent

logger = get_logger(__name__)

__all__ = [
    "DEFAULT_HOLD_WINDOW_DAYS",
    "DEFAULT_LAUNCH_PROBABILITY_THRESHOLD",
    "HoldDecision",
    "fit_decay_params",
    "hold_decision",
    "launch_probability",
    "list_launch_events",
    "upsert_launch_event",
]

#: How long a unit is held for when the HOLD channel is offered.
DEFAULT_HOLD_WINDOW_DAYS: Final[int] = 21

#: The probability of a launch inside the window below which holding is
#: considered safe.
DEFAULT_LAUNCH_PROBABILITY_THRESHOLD: Final[float] = 0.20

#: The model version of the fitted decay parameters.
DECAY_MODEL_VERSION: Final[str] = "decay-v1"


@dataclass(frozen=True, slots=True)
class HoldDecision:
    """Whether a unit should be held, and why.

    Attributes:
        offered: Whether HOLD is on the table.
        reason: Why it is, or why it is not.
        expected_change_p50: The median expected price change over the window.
        launch_probability: The probability of a launch inside the window.
        window_days: The length of the hold window.
        rate_per_day: The fitted decay rate.
    """

    offered: bool
    reason: str
    expected_change_p50: float
    launch_probability: float
    window_days: int
    rate_per_day: float

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of the decision."""
        return {
            "offered": self.offered,
            "reason": self.reason,
            "expected_change_p50": round(self.expected_change_p50, 6),
            "launch_probability": round(self.launch_probability, 4),
            "window_days": self.window_days,
            "rate_per_day": round(self.rate_per_day, 8),
        }


async def upsert_launch_event(
    session: AsyncSession,
    *,
    sku_family: str,
    event_date: date,
    event_type: str,
    source_url: str,
    notes: str | None = None,
) -> LaunchEvent:
    """Create or update a launch event.

    Args:
        session: Database session.
        sku_family: The family the launch affects.
        event_date: When the launch is expected.
        event_type: What kind of launch it is.
        source_url: Where the announcement is.
        notes: Anything else worth recording.

    Returns:
        The stored row.
    """
    result = await session.execute(
        select(LaunchEvent).where(
            LaunchEvent.sku_family == sku_family,
            LaunchEvent.event_date == event_date,
            LaunchEvent.event_type == event_type,
        )
    )
    row = result.scalars().first()
    if row is None:
        row = LaunchEvent(
            sku_family=sku_family,
            event_date=event_date,
            event_type=event_type,
            source_url=source_url,
            notes=notes,
        )
        session.add(row)
    else:
        row.source_url = source_url
        row.notes = notes
    await session.flush()
    return row


async def list_launch_events(
    session: AsyncSession, *, sku_family: str | None = None
) -> list[LaunchEvent]:
    """List the launch events.

    Args:
        session: Database session.
        sku_family: Restrict to one family.

    Returns:
        The launch events, soonest first.
    """
    query = select(LaunchEvent)
    if sku_family:
        query = query.where(LaunchEvent.sku_family == sku_family)
    result = await session.execute(query.order_by(LaunchEvent.event_date))
    return list(result.scalars().all())


def launch_probability(
    launches: Sequence[LaunchEvent],
    *,
    today: date | None = None,
    window_days: int = DEFAULT_HOLD_WINDOW_DAYS,
) -> float:
    """The probability of a launch inside the hold window.

    A known launch inside the window means a launch is certain, so the
    probability is 1. A launch that has already passed does not count.

    Args:
        launches: The known launch events.
        today: The reference date. Defaults to today.
        window_days: The length of the window.

    Returns:
        The probability, between 0 and 1.
    """
    today = today or datetime.now(UTC).date()
    window_end = today + timedelta(days=window_days)

    for launch in launches:
        if launch.event_date < today:
            continue
        if launch.event_date <= window_end:
            return 1.0

    return 0.0


def expected_price_change(rate_per_day: float, window_days: int) -> float:
    """The expected price change over the window.

    The rate is the log-slope of the price, so a **positive** rate means the
    price is rising. The change is expressed as a fraction of the current
    price.

    Args:
        rate_per_day: The fitted price rate per day.
        window_days: The length of the window.

    Returns:
        The expected fractional change. Positive means holding is better.
    """
    if rate_per_day == 0:
        return 0.0
    return math.exp(rate_per_day * window_days) - 1.0


def hold_decision(
    *,
    rate_per_day: float,
    launches: Sequence[LaunchEvent],
    today: date | None = None,
    window_days: int = DEFAULT_HOLD_WINDOW_DAYS,
    launch_probability_threshold: float = DEFAULT_LAUNCH_PROBABILITY_THRESHOLD,
) -> HoldDecision:
    """Decide whether a unit should be held.

    Args:
        rate_per_day: The fitted price rate for the family and grade. A
            positive rate means the price is rising.
        launches: The known launch events for the family.
        today: The reference date. Defaults to today.
        window_days: The length of the hold window.
        launch_probability_threshold: The probability above which holding is
            not offered.

    Returns:
        The decision.
    """
    today = today or datetime.now(UTC).date()
    probability = launch_probability(launches, today=today, window_days=window_days)
    change = expected_price_change(rate_per_day, window_days)

    if probability >= launch_probability_threshold:
        return HoldDecision(
            offered=False,
            reason=(
                "A launch is expected inside the hold window "
                f"(probability {probability:.0%}), so the price is likely to fall."
            ),
            expected_change_p50=change,
            launch_probability=probability,
            window_days=window_days,
            rate_per_day=rate_per_day,
        )

    if change <= 0:
        return HoldDecision(
            offered=False,
            reason=(
                "The expected price change over the hold window is not positive, "
                "so holding is worse than selling now."
            ),
            expected_change_p50=change,
            launch_probability=probability,
            window_days=window_days,
            rate_per_day=rate_per_day,
        )

    return HoldDecision(
        offered=True,
        reason=(
            f"The expected price change over {window_days} days is positive "
            f"({change:+.1%}) and no launch is expected in the window."
        ),
        expected_change_p50=change,
        launch_probability=probability,
        window_days=window_days,
        rate_per_day=rate_per_day,
    )


async def fit_decay_params(
    session: AsyncSession,
    *,
    model_version: str = DECAY_MODEL_VERSION,
    minimum_observations: int = 10,
) -> int:
    """Fit the price decay for every family and grade.

    The rate is the slope of the log price against time, per family and grade.
    A positive slope means the price is rising.

    Args:
        session: Database session.
        model_version: The model version to stamp on the fitted parameters.
        minimum_observations: How many observations a cell needs before it is
            fitted at all.

    Returns:
        How many parameters were fitted.
    """
    from secondroute.identity.models import SKU
    from secondroute.pricing.models import PriceObservation

    rows = (
        (await session.execute(select(PriceObservation).order_by(PriceObservation.observed_at)))
        .scalars()
        .all()
    )
    if not rows:
        return 0

    sku_ids = {row.sku_id for row in rows}
    skus = (await session.execute(select(SKU).where(SKU.id.in_(sku_ids)))).scalars().all()
    family_by_sku = {sku.id: sku.family for sku in skus}

    grouped: dict[tuple[str, str], list[tuple[datetime, float]]] = {}
    for row in rows:
        family = family_by_sku.get(row.sku_id)
        if family is None:
            continue
        grouped.setdefault((family, row.grade), []).append((row.observed_at, row.price))

    fitted = 0
    for (family, grade), points in grouped.items():
        if len(points) < minimum_observations:
            continue

        points.sort()
        origin = points[0][0]
        xs = [(observed - origin).total_seconds() / 86400.0 for observed, _ in points]
        ys = [math.log(price) for _, price in points if price > 0]
        if len(ys) < len(xs):
            continue

        rate = _least_squares_slope(xs, ys)
        if rate is None:
            continue

        result = await session.execute(
            select(DecayParam).where(DecayParam.sku_family == family, DecayParam.grade == grade)
        )
        row = result.scalars().first()
        if row is None:
            row = DecayParam(
                sku_family=family,
                grade=grade,
                rate_per_day=rate,
                model_version=model_version,
            )
            session.add(row)
        else:
            row.rate_per_day = rate
            row.model_version = model_version
            row.fitted_at = datetime.utcnow()
        fitted += 1

    await session.flush()
    logger.info("decay_params_fitted", parameters=fitted)
    return fitted


def _least_squares_slope(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """The slope of a least-squares fit, or ``None`` when it is undefined."""
    count = len(xs)
    if count < 2:
        return None

    mean_x = sum(xs) / count
    mean_y = sum(ys) / count
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return None
    return numerator / denominator


async def get_decay_param(
    session: AsyncSession, *, sku_family: str, grade: str
) -> DecayParam | None:
    """Return the fitted decay for a family and grade.

    Args:
        session: Database session.
        sku_family: The family.
        grade: The grade.

    Returns:
        The decay parameter, or ``None`` when it has not been fitted.
    """
    result = await session.execute(
        select(DecayParam).where(DecayParam.sku_family == sku_family, DecayParam.grade == grade)
    )
    return result.scalars().first()
