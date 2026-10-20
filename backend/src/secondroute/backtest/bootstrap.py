"""
Bootstrap confidence intervals for the backtest (Phase 5 - F5.6).

The backtest compares two policies over the same units, so the quantity of
interest is the *paired* difference in net value per unit. A paired
bootstrap resamples the units, not the two policies separately, which keeps
the pairing and gives an interval that accounts for the fact that the two
policies saw the same units.

The resampling is seeded, so the same inputs always produce the same
interval.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from numpy.typing import NDArray

__all__ = [
    "BootstrapError",
    "ConfidenceInterval",
    "bootstrap_mean_ci",
]


class BootstrapError(RuntimeError):
    """Raised when a bootstrap cannot be computed."""


@dataclass(frozen=True, slots=True)
class ConfidenceInterval:
    """A point estimate with a bootstrap interval around it.

    Attributes:
        point_estimate: The observed mean of the sample.
        lower: Lower bound of the interval.
        upper: Upper bound of the interval.
        confidence: The confidence level of the interval.
        method: How the interval was produced.
        samples: Number of bootstrap resamples.
        seed: The seed used, so the interval can be reproduced.
        n: Number of observations the interval was computed from.
    """

    point_estimate: float
    lower: float
    upper: float
    confidence: float
    method: str
    samples: int
    seed: int
    n: int

    @property
    def excludes_zero(self) -> bool:
        """Whether the interval lies entirely on one side of zero."""
        return self.lower > 0.0 or self.upper < 0.0

    def as_dict(self) -> dict[str, float | int | str | bool]:
        """Return a JSON-serialisable view of the interval."""
        return {
            "point_estimate": round(self.point_estimate, 4),
            "lower": round(self.lower, 4),
            "upper": round(self.upper, 4),
            "confidence": self.confidence,
            "method": self.method,
            "samples": self.samples,
            "seed": self.seed,
            "n": self.n,
            "excludes_zero": self.excludes_zero,
        }


def bootstrap_mean_ci(
    values: Sequence[float],
    *,
    confidence: float = 0.95,
    samples: int = 10_000,
    seed: int = 0,
) -> ConfidenceInterval:
    """Return a bootstrap confidence interval for the mean of ``values``.

    Args:
        values: The observations to summarise. For a paired backtest these
            are the per-unit differences between the two policies.
        confidence: The confidence level, in ``(0, 1)``.
        samples: Number of bootstrap resamples. More samples give a smoother
            interval at a proportional cost.
        seed: RNG seed. The same seed always produces the same interval.

    Returns:
        The point estimate and the interval around it.

    Raises:
        BootstrapError: If fewer than two observations are given, or the
            confidence level or sample count is out of range.
    """
    if not 0.0 < confidence < 1.0:
        raise BootstrapError(f"confidence must be strictly between 0 and 1, got {confidence}")
    if samples < 1:
        raise BootstrapError(f"samples must be at least 1, got {samples}")

    data = np.asarray(list(values), dtype=np.float64)
    n = int(data.size)
    if n < 2:
        raise BootstrapError(
            f"A confidence interval needs at least two observations, got {n}. "
            f"Report the point estimate without an interval instead."
        )
    if not np.all(np.isfinite(data)):
        raise BootstrapError("The sample contains a non-finite value")

    rng = np.random.default_rng(seed)
    indices = rng.integers(0, n, size=(samples, n))
    resampled_means = data[indices].mean(axis=1)

    alpha = (1.0 - confidence) / 2.0
    lower = float(np.quantile(resampled_means, alpha))
    upper = float(np.quantile(resampled_means, 1.0 - alpha))

    return ConfidenceInterval(
        point_estimate=float(data.mean()),
        lower=lower,
        upper=upper,
        confidence=confidence,
        method="paired-bootstrap-percentile",
        samples=samples,
        seed=seed,
        n=n,
    )


def bootstrap_mean_ci_array(
    values: NDArray[np.float64],
    *,
    confidence: float = 0.95,
    samples: int = 10_000,
    seed: int = 0,
) -> ConfidenceInterval:
    """Array-typed wrapper around :func:`bootstrap_mean_ci`."""
    return bootstrap_mean_ci(values.tolist(), confidence=confidence, samples=samples, seed=seed)
