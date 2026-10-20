"""
Calibration for Phase 4 (F4.6).

The reliability curve compares the confidence the engine reported with how
often the recommended channel actually turned out to be the best one, and
the expected calibration error (ECE) summarises the gap.

Recalibration is a versioned step. Fitting it produces a new version with
its own mapping; the version in force is recorded on every decision, so a
decision can always be read against the calibration it was made under.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Sequence, cast
from uuid import UUID

import structlog

from secondroute.analytics.models import CalibrationVersion
from secondroute.core.db import Base  # noqa: F401  (registers the table)

logger = structlog.get_logger(__name__)

#: The number of bins of the reliability curve.
DEFAULT_BINS = 10


@dataclass(frozen=True)
class CalibrationPoint:
    """One observation of the engine's confidence and what really happened.

    Attributes:
        predicted: The confidence the engine reported, between 0 and 1.
        observed: Whether the recommended channel turned out to be the best
            of the channels that were tried.
    """

    predicted: float
    observed: bool


@dataclass(frozen=True)
class CalibrationBin:
    """One bin of the reliability curve.

    Attributes:
        lower: The lower edge of the bin.
        upper: The upper edge of the bin.
        count: How many observations fell into the bin.
        mean_predicted: The mean predicted confidence in the bin.
        observed_frequency: The fraction of observations that were correct.
    """

    lower: float
    upper: float
    count: int
    mean_predicted: float
    observed_frequency: float

    @property
    def gap(self) -> float:
        """The signed gap between the prediction and the observation."""
        return self.observed_frequency - self.mean_predicted


@dataclass(frozen=True)
class IsotonicMapping:
    """A fitted isotonic recalibration.

    Attributes:
        points: The ``(predicted, calibrated)`` knots of the mapping.
    """

    points: tuple[tuple[float, float], ...] = ()

    def apply(self, predicted: float) -> float:
        """Map a predicted confidence to its calibrated value.

        The mapping is piecewise linear between the knots and flat outside
        them.

        Args:
            predicted: The predicted confidence.

        Returns:
            The calibrated confidence.
        """
        if not self.points:
            return predicted
        if predicted <= self.points[0][0]:
            return self.points[0][1]
        if predicted >= self.points[-1][0]:
            return self.points[-1][1]

        for (low_x, low_y), (high_x, high_y) in zip(self.points, self.points[1:], strict=False):
            if low_x <= predicted <= high_x:
                if high_x == low_x:
                    return low_y
                ratio = (predicted - low_x) / (high_x - low_x)
                return low_y + ratio * (high_y - low_y)
        return predicted

    def to_json(self) -> str:
        """Render the mapping for storage.

        Returns:
            The mapping as a JSON string.
        """
        return json.dumps([list(point) for point in self.points])

    @classmethod
    def from_json(cls, raw: str) -> IsotonicMapping:
        """Read a stored mapping.

        Args:
            raw: The JSON string.

        Returns:
            The mapping.
        """
        if not raw:
            return cls()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return cls()
        points = tuple((float(x), float(y)) for x, y in parsed)
        return cls(points=points)


def reliability_curve(
    observations: Sequence[CalibrationPoint],
    bins: int = DEFAULT_BINS,
) -> list[CalibrationBin]:
    """Build the reliability curve of the given observations.

    The observations are binned by predicted confidence into ``bins`` equal
    width bins over ``[0, 1]``.

    Args:
        observations: The observations.
        bins: How many bins to use.

    Returns:
        One bin per non-empty bucket of the curve.
    """
    if bins < 1:
        raise ValueError("bins must be at least one")

    buckets: list[list[CalibrationPoint]] = [[] for _ in range(bins)]
    for observation in observations:
        predicted = min(max(observation.predicted, 0.0), 1.0)
        index = min(int(predicted * bins), bins - 1)
        buckets[index].append(observation)

    curve: list[CalibrationBin] = []
    for index, bucket in enumerate(buckets):
        if not bucket:
            continue
        lower = index / bins
        upper = (index + 1) / bins
        mean_predicted = sum(point.predicted for point in bucket) / len(bucket)
        observed = sum(1 for point in bucket if point.observed) / len(bucket)
        curve.append(
            CalibrationBin(
                lower=round(lower, 6),
                upper=round(upper, 6),
                count=len(bucket),
                mean_predicted=round(mean_predicted, 6),
                observed_frequency=round(observed, 6),
            )
        )
    return curve


def expected_calibration_error(bins: Sequence[CalibrationBin]) -> float:
    """Compute the expected calibration error of a reliability curve.

    The ECE is the sample-weighted mean absolute gap between the predicted
    confidence and the observed frequency, over the non-empty bins.

    Args:
        bins: The bins of the reliability curve.

    Returns:
        The ECE, between 0 and 1. Zero when there is nothing to measure.
    """
    total = sum(bin_.count for bin_ in bins)
    if total == 0:
        return 0.0
    error = sum(bin_.count * abs(bin_.gap) for bin_ in bins) / total
    return round(error, 6)


def fit_isotonic(observations: Sequence[CalibrationPoint]) -> IsotonicMapping:
    """Fit an isotonic recalibration of the predicted confidence.

    The pool adjacent violators algorithm is used: the observations are
    sorted by their predicted confidence and the blocks are merged until the
    fitted values are non-decreasing.

    Args:
        observations: The observations to fit.

    Returns:
        The fitted mapping.
    """
    if not observations:
        return IsotonicMapping()

    ordered = sorted(observations, key=lambda point: point.predicted)

    # Each block holds the predicted sum, the observed sum, the count and
    # the range of predicted values it covers.
    blocks: list[list[float]] = []
    for point in ordered:
        blocks.append([point.predicted, 1.0 if point.observed else 0.0, 1.0, point.predicted])
        while len(blocks) >= 2 and blocks[-2][1] / blocks[-2][2] > blocks[-1][1] / blocks[-1][2]:
            left = blocks.pop()
            right = blocks.pop()
            blocks.append(
                [
                    left[0] + right[0],
                    left[1] + right[1],
                    left[2] + right[2],
                    right[3],
                ]
            )

    knots: list[tuple[float, float]] = []
    for predicted_sum, observed_sum, count, _upper in blocks:
        knots.append((predicted_sum / count, observed_sum / count))

    # The mapping has to be non-decreasing in the predicted confidence.
    for index in range(1, len(knots)):
        previous_x, previous_y = knots[index - 1]
        current_x, current_y = knots[index]
        if current_y < previous_y:
            knots[index] = (current_x, previous_y)

    return IsotonicMapping(points=tuple(knots))


@dataclass
class CalibrationReport:
    """The calibration of the engine.

    Attributes:
        bins: The reliability curve.
        ece: The expected calibration error.
        sample_size: How many observations the curve is built from.
        bins_count: How many bins the curve uses.
        active_version: The recalibration version in force, if any.
        observations: The raw observations, so a caller can refit.
    """

    bins: list[CalibrationBin] = field(default_factory=list)
    ece: float = 0.0
    sample_size: int = 0
    bins_count: int = DEFAULT_BINS
    active_version: Optional[str] = None
    observations: list[CalibrationPoint] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Render the report for the API response.

        Returns:
            The report.
        """
        return {
            "bins": [
                {
                    "lower": bin_.lower,
                    "upper": bin_.upper,
                    "count": bin_.count,
                    "mean_predicted": bin_.mean_predicted,
                    "observed_frequency": bin_.observed_frequency,
                    "gap": round(bin_.gap, 6),
                }
                for bin_ in self.bins
            ],
            "ece": self.ece,
            "sample_size": self.sample_size,
            "bin_count": self.bins_count,
            "active_version": self.active_version,
        }


class CalibrationService:
    """Builds the calibration report and the recalibration versions."""

    async def report(
        self,
        session: Any,
        *,
        bins: int = DEFAULT_BINS,
    ) -> CalibrationReport:
        """Build the calibration report from the recorded dispositions.

        A decision counts as correct when the channel it recommended was
        the one that realized the best net. A decision without an outcome
        has nothing to compare against and is left out.

        Args:
            session: Database session.
            bins: How many bins the reliability curve uses.

        Returns:
            The report.
        """
        observations = await self._load_observations(session)
        curve = reliability_curve(observations, bins=bins)
        active = await self._active_version(session)

        return CalibrationReport(
            bins=curve,
            ece=expected_calibration_error(curve),
            sample_size=len(observations),
            bins_count=bins,
            active_version=active.version if active is not None else None,
            observations=observations,
        )

    async def recalibrate(
        self,
        session: Any,
        *,
        bins: int = DEFAULT_BINS,
        version: Optional[str] = None,
    ) -> CalibrationVersion:
        """Fit a new recalibration version and put it in force.

        The version is stored before it is activated, and the previous
        version stays in the table, so the calibration a decision was made
        under can always be looked up.

        Args:
            session: Database session.
            bins: How many bins the reliability curve uses.
            version: The version name. One is derived from the time when
                it is left out.

        Returns:
            The stored version.
        """
        observations = await self._load_observations(session)
        curve = reliability_curve(observations, bins=bins)
        ece_before = expected_calibration_error(curve)

        mapping = fit_isotonic(observations)

        # The ECE of the recalibrated curve.
        recalibrated_points = [
            CalibrationPoint(predicted=mapping.apply(point.predicted), observed=point.observed)
            for point in observations
        ]
        recalibrated_curve = reliability_curve(recalibrated_points, bins=bins)
        ece_after = expected_calibration_error(recalibrated_curve)

        name = (
            version
            or f"calibration-v{len(observations)}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        )

        record = CalibrationVersion(
            version=name,
            org_id=None,
            mapping_json=mapping.to_json(),
            sample_size=len(observations),
            ece_before=ece_before,
            ece_after=ece_after,
            bins=bins,
            is_active=True,
        )
        session.add(record)

        # Only one version is in force at a time.
        for other in await self._all_versions(session):
            if other.is_active and other.version != name:
                other.is_active = False

        await session.commit()
        await session.refresh(record)
        logger.info(
            "calibration.recalibrated", version=name, ece_before=ece_before, ece_after=ece_after
        )
        return record

    async def _all_versions(self, session: Any) -> list[CalibrationVersion]:
        """Load every stored recalibration version."""
        from sqlalchemy import select

        result = await session.execute(select(CalibrationVersion))
        return list(result.scalars().all())

    async def _active_version(self, session: Any) -> Optional[CalibrationVersion]:
        """Load the recalibration version in force, if there is one."""
        from sqlalchemy import select

        result = await session.execute(
            select(CalibrationVersion).where(CalibrationVersion.is_active.is_(True))
        )
        return cast("Optional[CalibrationVersion]", result.scalars().first())

    async def _load_observations(self, session: Any) -> list[CalibrationPoint]:
        """Load the decisions and work out how often they were right.

        Args:
            session: Database session.

        Returns:
            The observations.
        """
        from sqlalchemy import select

        from secondroute.decision.models import Decision
        from secondroute.feedback.models import Outcome

        result = await session.execute(
            select(Decision, Outcome)
            .join(Outcome, Outcome.decision_id == Decision.id)
            .order_by(Decision.created_at)
        )
        rows = result.all()

        # The outcomes of a unit are compared against each other, so the
        # best realized net has to be found per unit.
        best_net_by_unit: dict[UUID, float] = {}
        for _decision, outcome in rows:
            realized = float(outcome.net)
            current = best_net_by_unit.get(outcome.unit_id)
            if current is None or realized > current:
                best_net_by_unit[outcome.unit_id] = realized

        observations: list[CalibrationPoint] = []
        for decision, outcome in rows:
            best_net = best_net_by_unit.get(outcome.unit_id)
            if best_net is None:
                continue
            # The recommendation was right when the channel it recommended
            # realized the best net of the channels that were tried.
            observed = float(outcome.net) >= best_net
            observations.append(
                CalibrationPoint(
                    predicted=float(decision.confidence),
                    observed=observed,
                )
            )
        return observations


def new_version_id() -> str:
    """Return a fresh identifier for a calibration version."""
    return uuid.uuid4().hex
