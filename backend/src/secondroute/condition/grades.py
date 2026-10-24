"""
Grade rules (Phase 2 - F2.3).

Maps the fields of an inspection record onto a probability distribution over
the grades ``A``, ``B``, ``C`` and ``D``.

The rules are explicit and deterministic - no model, no LLM. A latent *condition
score* is built from the inspection signals, and the score is mapped onto the
four grades with a softmax. Because the score is monotone increasing in
battery health, and the softmax is monotone increasing in the score, the
probability of grade ``A`` can never increase when battery health gets worse.
That property is asserted by the test suite.

This module also owns the channel *eligibility* rules, which are policy rather
than condition (an activation-locked unit cannot be resold regardless of how
good it looks).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Final, Literal

__all__ = [
    "GRADES",
    "Grade",
    "GradeDistribution",
    "InspectionSignals",
    "channel_eligibility",
    "grade_distribution",
]

Grade = Literal["A", "B", "C", "D"]

#: Canonical grade order, best to worst.
GRADES: Final[tuple[Grade, ...]] = ("A", "B", "C", "D")

#: Position of each grade on the 1-4 condition scale.
GRADE_VALUE: Final[dict[str, float]] = {
    "A": 4.0,
    "B": 3.0,
    "C": 2.0,
    "D": 1.0,
}

#: Lowest and highest condition score the signals can produce.
SCORE_MIN: Final[float] = -0.38
SCORE_MAX: Final[float] = 0.90

#: How sharply the grade distribution is concentrated around the expected
#: grade level. Higher means a more confident grade call.
TEMPERATURE: Final[float] = 2.5

#: Share of the probability mass spread evenly over all grades. This keeps a
#: floor under every grade so a very good unit is never *impossible* in a
#: lower grade.
UNIFORM_FLOOR: Final[float] = 0.02

#: Cosmetic grade contribution, normalised to ``[0, 1]``.
COSMETIC_SCORE: Final[dict[str, float]] = {
    "A": 1.00,
    "B": 0.62,
    "C": 0.25,
    "D": 0.00,
}

#: Weights of each inspection signal in the condition score.
WEIGHT_COSMETIC: Final[float] = 0.68
WEIGHT_BATTERY: Final[float] = 0.22
WEIGHT_FUNCTIONAL_FAILURES: Final[float] = 0.38

#: Battery health at or below this maps to a score of zero.
BATTERY_FLOOR_PCT: Final[float] = 50.0
#: Battery health at or above this maps to a score of one.
BATTERY_CEILING_PCT: Final[float] = 100.0

#: The battery term for a device with no battery: the middle of the scale.
NO_BATTERY_SCORE: Final[float] = 0.5

#: Activation-lock states that block every resale channel.
BLOCKING_ACTIVATION_LOCKS: Final[frozenset[str]] = frozenset({"present"})

#: Minimum expected grade level for the open-box channel.
MIN_OPEN_BOX_LEVEL: Final[float] = 2.4

#: The channels a unit can be routed to. ``PARTS_HARVEST`` arrived in
#: Phase 3 (F3.6) and is always eligible - there is always something to
#: harvest, and the parts valuation decides whether it is worth doing.
ELIGIBLE_CHANNELS: Final[tuple[str, ...]] = (
    "RESELL_OPEN_BOX",
    "RESELL_REFURB",
    "PARTS_HARVEST",
    "RECYCLE",
    "DONATE",
    "HOLD",
)

#: The channels that sell the unit rather than its parts.
RESALE_CHANNELS: Final[frozenset[str]] = frozenset({"RESELL_OPEN_BOX", "RESELL_REFURB"})


@dataclass(frozen=True, slots=True)
class InspectionSignals:
    """The inspection fields the grade rules read.

    Attributes:
        battery_health_pct: Battery health percentage (``0``-``100``).
        battery_cycles: Battery cycle count, when known.
        cosmetic_grade: Inspector's cosmetic grade (``A``-``D``).
        functional_tests: Mapping of test name to pass/fail.
        accessories: Mapping of accessory name to present/missing.
        activation_lock: Activation-lock state (``none``/``present``/``unknown``).
    """

    battery_health_pct: float | None
    cosmetic_grade: str
    functional_tests: Mapping[str, bool] = field(default_factory=dict)
    accessories: Mapping[str, bool] = field(default_factory=dict)
    activation_lock: str = "unknown"
    battery_cycles: int | None = None

    @classmethod
    def from_inspection(cls, inspection: object) -> InspectionSignals:
        """Build signals from an ORM inspection row or a plain mapping.

        Args:
            inspection: An inspection record (ORM row or mapping).

        Returns:
            The extracted signals.
        """
        if isinstance(inspection, Mapping):
            data: Mapping[str, object] = inspection
        else:
            data = {
                "battery_health_pct": getattr(inspection, "battery_health_pct", None),
                "battery_cycles": getattr(inspection, "battery_cycles", None),
                "cosmetic_grade": getattr(inspection, "cosmetic_grade", "C"),
                "functional_tests": getattr(inspection, "functional_tests", {}) or {},
                "accessories": getattr(inspection, "accessories", {}) or {},
                "activation_lock": getattr(inspection, "activation_lock", "unknown"),
            }

        raw_battery = data.get("battery_health_pct")
        battery: float | None
        if raw_battery in (None, ""):
            battery = None
        else:
            try:
                battery = float(raw_battery)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                battery = None

        raw_cycles = data.get("battery_cycles")
        try:
            cycles = int(str(raw_cycles)) if raw_cycles not in (None, "") else None
        except (TypeError, ValueError):
            cycles = None

        return cls(
            battery_health_pct=battery,
            battery_cycles=cycles,
            cosmetic_grade=str(data.get("cosmetic_grade", "C")),
            functional_tests=_coerce_bool_map(data.get("functional_tests")),
            accessories=_coerce_bool_map(data.get("accessories")),
            activation_lock=str(data.get("activation_lock", "unknown")),
        )


@dataclass(frozen=True, slots=True)
class GradeDistribution:
    """Probability distribution over the four grades.

    Attributes:
        probabilities: Probability per grade.
        score: The condition score the distribution was derived from.
        expected_level: Expected position on the 1-4 grade scale.
        model_version: Version of the rules that produced it.
    """

    probabilities: dict[str, float]
    score: float
    expected_level: float = 2.0
    model_version: str = "grade-rules-v1"

    def __post_init__(self) -> None:
        missing = [g for g in GRADES if g not in self.probabilities]
        if missing:
            raise ValueError(f"grade distribution is missing grades: {missing}")
        total = sum(self.probabilities.values())
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"grade probabilities must sum to 1, got {total}")

    @property
    def most_likely(self) -> str:
        """Return the grade with the highest probability."""
        return max(GRADES, key=lambda g: self.probabilities[g])

    @property
    def expected_grade_score(self) -> float:
        """Return the expected position on the 1-4 grade scale."""
        return self.expected_level

    def as_dict(self) -> dict[str, float]:
        """Return the probabilities as a plain dictionary."""
        return {grade: self.probabilities[grade] for grade in GRADES}


def _coerce_bool_map(value: object) -> dict[str, bool]:
    """Coerce a stored JSON blob into a ``{name: bool}`` mapping."""
    if isinstance(value, Mapping):
        return {str(k): bool(v) for k, v in value.items()}
    if isinstance(value, str) and value:
        import json

        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, Mapping):
            return {str(k): bool(v) for k, v in parsed.items()}
    return {}


def condition_score(signals: InspectionSignals) -> float:
    """Return the latent condition score for a set of inspection signals.

    The score is in roughly ``[-1, 1]`` and is monotone increasing in battery
    health, which is what makes the grade distribution monotone in the same
    direction.

    Args:
        signals: The inspection signals.

    Returns:
        The condition score.
    """
    cosmetic = COSMETIC_SCORE.get(signals.cosmetic_grade, COSMETIC_SCORE["C"])

    span = BATTERY_CEILING_PCT - BATTERY_FLOOR_PCT
    if signals.battery_health_pct is None:
        # A device with no battery is neither good nor bad on that account.
        # It sits at the middle, so the grade is decided by what it does have.
        battery = NO_BATTERY_SCORE
    else:
        battery = (signals.battery_health_pct - BATTERY_FLOOR_PCT) / span
        battery = min(max(battery, 0.0), 1.0)

    tests = signals.functional_tests
    if tests:
        failures = sum(1 for passed in tests.values() if not passed)
        failure_rate = failures / len(tests)
    else:
        failure_rate = 0.0

    return (
        WEIGHT_COSMETIC * cosmetic
        + WEIGHT_BATTERY * battery
        - WEIGHT_FUNCTIONAL_FAILURES * failure_rate
    )


def expected_grade_level(score: float) -> float:
    """Map a condition score onto the expected position on the 1-4 grade scale.

    The mapping is linear and clamped, so the expected level is monotone in
    the condition score.

    Args:
        score: The condition score.

    Returns:
        The expected grade level, between ``1`` (grade D) and ``4`` (grade A).
    """
    span = SCORE_MAX - SCORE_MIN
    normalized = (score - SCORE_MIN) / span if span else 0.0
    normalized = min(max(normalized, 0.0), 1.0)
    return 1.0 + 3.0 * normalized


def grade_distribution(signals: InspectionSignals) -> GradeDistribution:
    """Map inspection signals onto a probability distribution over grades.

    The condition score is mapped onto an expected grade level, and the four
    grades are given a discretised-Gaussian spread around that level. Because
    the expected level is monotone increasing in battery health, and the
    probability of grade ``A`` is monotone increasing in the expected level,
    worse battery health can never increase the probability of grade ``A``.

    Args:
        signals: The inspection signals.

    Returns:
        The grade distribution. Probabilities sum to exactly one.
    """
    score = condition_score(signals)
    level = expected_grade_level(score)

    logits = {grade: -TEMPERATURE * (GRADE_VALUE[grade] - level) ** 2 for grade in GRADES}
    max_logit = max(logits.values())
    exponentials = {grade: math.exp(logits[grade] - max_logit) for grade in GRADES}
    total = sum(exponentials.values())

    uniform = UNIFORM_FLOOR / len(GRADES)
    probabilities: dict[str, float] = {
        grade: (1.0 - UNIFORM_FLOOR) * (exponentials[grade] / total) + uniform for grade in GRADES
    }
    # Guard against float drift so the sum is exactly 1.0.
    rounding = 1.0 - sum(probabilities.values())
    probabilities[GRADES[0]] += rounding

    return GradeDistribution(
        probabilities=probabilities,
        score=score,
        expected_level=level,
    )


def channel_eligibility(
    signals: InspectionSignals,
    grade_distribution_: GradeDistribution,
) -> dict[str, tuple[bool, str | None]]:
    """Return per-channel eligibility and the reason when a channel is blocked.

    Args:
        signals: The inspection signals.
        grade_distribution_: The grade distribution for the unit.

    Returns:
        A mapping of channel name to ``(eligible, reason)``.
    """
    expected_level = grade_distribution_.expected_level
    activation_locked = signals.activation_lock in BLOCKING_ACTIVATION_LOCKS

    eligibility: dict[str, tuple[bool, str | None]] = {}

    for channel in ELIGIBLE_CHANNELS:
        eligible = True
        reason: str | None = None

        if activation_locked and channel in RESALE_CHANNELS:
            eligible = False
            reason = "Activation lock present - resale channels are blocked."

        if eligible and channel == "RESELL_OPEN_BOX" and expected_level < MIN_OPEN_BOX_LEVEL:
            eligible = False
            reason = (
                "Expected condition is below the open-box standard "
                f"(expected grade level {expected_level:.2f}, "
                f"minimum {MIN_OPEN_BOX_LEVEL:.2f})."
            )

        eligibility[channel] = (eligible, reason)

    return eligibility
