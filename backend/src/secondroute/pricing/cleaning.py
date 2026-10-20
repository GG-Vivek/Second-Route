"""
Price cleaning (Phase 3 - F3.3).

Three things happen to a set of price observations before they are turned into
a distribution:

1. **Outlier removal.** A single mispriced listing (a data-entry error, a
   "free" auction, a price for a different model) must not drag the p50 or
   the p90. The filter is based on the median absolute deviation (MAD), which
   - unlike a standard deviation - is not itself moved by the outlier.
2. **Grade normalisation.** Every source names its grades differently. eBay
   says "Very Good", a partner CSV says "B+", a refurb shop says "Refurbished".
   They all have to become our canonical ``A``/``B``/``C``/``D``.
3. **Recency weighting.** A price from 60 days ago says less about the market
   than a price from this morning. Observations are weighted by an
   exponential decay with a configurable half-life (30 days by default), so a
   60-day-old observation counts a quarter as much as a fresh one.

Nothing here touches the decision engine. Cleaning happens in the adapter
layer, before the distribution is built.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Final

__all__ = [
    "DEFAULT_HALF_LIFE_DAYS",
    "DEFAULT_MAD_THRESHOLD",
    "CleanedObservations",
    "PriceObservationRow",
    "apply_recency_weights",
    "clean_observations",
    "normalize_grade",
    "recency_weight",
    "remove_outliers",
]

#: Half-life of the recency decay, in days.
DEFAULT_HALF_LIFE_DAYS: Final[int] = 30

#: How many robust standard deviations away a value has to be to count as an
#: outlier. 3.5 is the usual choice for MAD-based filtering.
DEFAULT_MAD_THRESHOLD: Final[float] = 3.5

#: Scale factor that makes the MAD comparable to a standard deviation for
#: normally distributed data.
MAD_SCALE: Final[float] = 1.4826

#: Canonical grades, best to worst.
CANONICAL_GRADES: Final[tuple[str, ...]] = ("A", "B", "C", "D")

#: Grade labels seen in the wild, mapped to our canonical grades.
GRADE_ALIASES: Final[dict[str, str]] = {
    # eBay condition ids
    "1000": "A",
    "1500": "A",
    "2000": "B",
    "2500": "A",
    "2750": "B",
    "3000": "C",
    "4000": "B",
    "5000": "C",
    "6000": "D",
    "7000": "D",
    # eBay condition labels
    "new": "A",
    "new other": "A",
    "new with defects": "B",
    "manufacturer refurbished": "A",
    "seller refurbished": "B",
    "used": "C",
    "very good": "B",
    "good": "C",
    "acceptable": "D",
    "for parts or not working": "D",
    # generic
    "excellent": "A",
    "mint": "A",
    "like new": "A",
    "open box": "B",
    "open-box": "B",
    "refurbished": "B",
    "refurb": "B",
    "fair": "C",
    "good condition": "C",
    "used - good": "C",
    "used - acceptable": "D",
    "poor": "D",
    "for parts": "D",
    "broken": "D",
    "damaged": "D",
    # letter grades with modifiers
    "a+": "A",
    "a-": "A",
    "b+": "B",
    "b-": "B",
    "c+": "C",
    "c-": "C",
    "d+": "D",
    "d-": "D",
}


@dataclass(frozen=True, slots=True)
class PriceObservationRow:
    """One observation as the cleaning step sees it.

    Attributes:
        value: The observed price.
        observed_at: When the price was observed.
        grade: The grade as the source named it.
        weight: The source's own weight for the observation.
    """

    value: float
    observed_at: datetime
    grade: str
    weight: float = 1.0


@dataclass(frozen=True, slots=True)
class CleanedObservations:
    """The result of cleaning a set of observations.

    Attributes:
        values: The surviving prices.
        weights: The weight of each surviving price, after recency decay.
        removed: How many observations were dropped as outliers.
        total: How many observations went in.
        grades: The normalised grade of each surviving observation.
    """

    values: tuple[float, ...]
    weights: tuple[float, ...]
    removed: int
    total: int
    grades: tuple[str, ...] = ()

    @property
    def count(self) -> int:
        """How many observations survived."""
        return len(self.values)

    @property
    def is_empty(self) -> bool:
        """Whether nothing survived."""
        return not self.values


def normalize_grade(raw: str | None) -> str | None:
    """Map a source's grade label onto our canonical grade.

    Args:
        raw: The grade as the source named it. Case and whitespace are
            ignored.

    Returns:
        ``"A"``, ``"B"``, ``"C"`` or ``"D"``, or ``None`` when the label is
        not recognised. An unrecognised grade is not silently forced into a
        bucket - the caller decides what to do with it.
    """
    if raw is None:
        return None

    key = str(raw).strip().lower()
    if not key:
        return None

    if key in GRADE_ALIASES:
        return GRADE_ALIASES[key]

    # A bare letter, e.g. "A", "b" or "grade c".
    stripped = key.replace("grade", "").strip()
    upper = stripped.upper()
    if upper in CANONICAL_GRADES:
        return upper

    # A letter with a modifier: take the letter.
    if len(stripped) >= 2 and stripped[0].upper() in CANONICAL_GRADES:
        return stripped[0].upper()

    return None


def recency_weight(age: timedelta | float, half_life_days: int = DEFAULT_HALF_LIFE_DAYS) -> float:
    """Return the exponential decay weight for an observation's age.

    The weight is ``0.5 ** (age / half_life)``, so an observation exactly one
    half-life old counts half as much as a fresh one, and one exactly two
    half-lives old counts a quarter.

    Args:
        age: How old the observation is, as a timedelta or a number of days.
        half_life_days: The half-life in days.

    Returns:
        The weight, between 0 and 1.

    Raises:
        ValueError: If the half-life is not positive.
    """
    if half_life_days <= 0:
        raise ValueError("half_life_days must be positive")

    if isinstance(age, timedelta):
        days = age.total_seconds() / 86400.0
    else:
        days = float(age)

    if days <= 0:
        return 1.0

    return float(0.5 ** (days / half_life_days))


def _median(values: Sequence[float]) -> float:
    """Return the median of a sequence."""
    if not values:
        raise ValueError("cannot take the median of an empty sequence")
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def remove_outliers(
    values: Sequence[float],
    *,
    threshold: float = DEFAULT_MAD_THRESHOLD,
) -> tuple[tuple[float, ...], int]:
    """Remove outliers using the median absolute deviation.

    The MAD is used rather than the standard deviation because the standard
    deviation is itself inflated by the very outliers we are looking for: one
    bad value can push a value far enough that it survives the filter.

    Args:
        values: The observations.
        threshold: How many robust standard deviations away a value has to be
            to count as an outlier.

    Returns:
        A ``(surviving_values, removed_count)`` tuple.

    Raises:
        ValueError: If the threshold is not positive.
    """
    if threshold <= 0:
        raise ValueError("threshold must be positive")

    if len(values) < 3:
        # Not enough points to say anything about outliers.
        return tuple(values), 0

    median = _median(values)
    deviations = [abs(value - median) for value in values]
    mad = _median(deviations)

    if mad == 0:
        # Most values are identical. Fall back to the mean absolute deviation
        # so a single odd value can still be spotted.
        mad = sum(deviations) / len(deviations)

    if mad == 0:
        return tuple(values), 0

    scaled = mad * MAD_SCALE
    kept = tuple(value for value in values if abs(value - median) / scaled <= threshold)
    return kept, len(values) - len(kept)


def apply_recency_weights(
    rows: Sequence[PriceObservationRow],
    *,
    now: datetime,
    half_life_days: int = DEFAULT_HALF_LIFE_DAYS,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Weight observations by how recent they are.

    Args:
        rows: The observations.
        now: The reference time.
        half_life_days: The half-life of the decay.

    Returns:
        A ``(values, weights)`` tuple.

    Raises:
        ValueError: If the half-life is not positive.
    """
    values: list[float] = []
    weights: list[float] = []

    for row in rows:
        age = now - row.observed_at
        values.append(row.value)
        weights.append(row.weight * recency_weight(age, half_life_days))

    return tuple(values), tuple(weights)


def clean_observations(
    rows: Sequence[PriceObservationRow],
    *,
    now: datetime,
    half_life_days: int = DEFAULT_HALF_LIFE_DAYS,
    mad_threshold: float = DEFAULT_MAD_THRESHOLD,
    normalize: bool = True,
) -> CleanedObservations:
    """Clean a set of price observations.

    Outliers are removed first, then the survivors are weighted by recency.

    Args:
        rows: The observations.
        now: The reference time for the recency decay.
        half_life_days: The half-life of the decay.
        mad_threshold: The outlier threshold.
        normalize: Whether to normalise the grades.

    Returns:
        The cleaned observations.

    Raises:
        ValueError: If the half-life or the threshold is not positive.
    """
    if half_life_days <= 0:
        raise ValueError("half_life_days must be positive")
    if mad_threshold <= 0:
        raise ValueError("mad_threshold must be positive")

    total = len(rows)
    if not rows:
        return CleanedObservations(values=(), weights=(), removed=0, total=0, grades=())

    kept_rows: list[PriceObservationRow] = []
    # Outlier removal works on the values, but the kept values have to be
    # mapped back onto their rows so the weights stay attached.
    kept_values, removed = remove_outliers([row.value for row in rows], threshold=mad_threshold)
    kept_set = set(kept_values)
    remaining = list(kept_values)
    for row in rows:
        if row.value in kept_set and remaining.count(row.value) > 0:
            remaining.remove(row.value)
            kept_rows.append(row)

    values, weights = apply_recency_weights(kept_rows, now=now, half_life_days=half_life_days)

    grades: tuple[str, ...] = ()
    if normalize:
        normalised: list[str] = []
        for row in kept_rows:
            grade = normalize_grade(row.grade) or "C"
            normalised.append(grade)
        grades = tuple(normalised)

    return CleanedObservations(
        values=values,
        weights=weights,
        removed=removed,
        total=total,
        grades=grades,
    )


def group_by_cell(
    rows: Iterable[PriceObservationRow],
) -> dict[tuple[str, str], list[PriceObservationRow]]:
    """Group observations by ``(grade, channel)``.

    Args:
        rows: The observations.

    Returns:
        A mapping of cell to its observations.
    """
    grouped: dict[tuple[str, str], list[PriceObservationRow]] = {}
    for row in rows:
        key = (normalize_grade(row.grade) or "C", "")
        grouped.setdefault(key, []).append(row)
    return grouped


def effective_sample_size(weights: Sequence[float]) -> float:
    """Return the effective sample size of a weighted set.

    The effective sample size is ``(sum of weights) ** 2 / sum of weights
    squared``. It is the number of equally-weighted observations that would
    carry the same amount of information.

    Args:
        weights: The weights.

    Returns:
        The effective sample size.
    """
    if not weights:
        return 0.0
    total = sum(weights)
    squared = sum(weight * weight for weight in weights)
    if squared <= 0:
        return 0.0
    return (total * total) / squared


def log_cleaning_summary(summary: dict[str, Any]) -> None:
    """Log a cleaning summary in a stable shape.

    Args:
        summary: The summary to log.
    """
    from secondroute.core.logging import get_logger

    get_logger(__name__).info("price_cleaning", **summary)
