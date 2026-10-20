"""
Price source interface and distribution types (Phase 2 - F2.2).

The decision engine never talks to a market data provider directly. It talks
to the :class:`PriceSource` protocol. Synthetic (Phase 2) and real (Phase 3)
adapters implement the same protocol, so swapping data sources changes no
decision code.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

import numpy as np
from numpy.typing import NDArray

__all__ = [
    "PriceDistribution",
    "PriceSource",
    "PriceSourceError",
    "PriceSourceNotFoundError",
]


class PriceSourceError(RuntimeError):
    """Raised when a price source cannot produce a usable distribution."""


class PriceSourceNotFoundError(PriceSourceError):
    """Raised when no price observation exists for the requested cell."""


@dataclass(frozen=True, slots=True)
class PriceDistribution:
    """A weighted empirical distribution over sale prices.

    Prices are represented empirically (the observations we actually have)
    rather than by fitting a parametric family. This keeps the engine honest:
    a cell backed by three observations produces a coarse distribution, which
    in turn lowers confidence and can trigger ``SAFE_DEFAULT`` (F2.7).

    Attributes:
        values: Observed prices, one per observation.
        weights: Relative weight of each observation (recency-adjusted).
        source: Where the observations came from (e.g. ``synthetic``).
        as_of: Timestamp the distribution is valid as of.
        currency: ISO currency code of ``values``.
    """

    values: tuple[float, ...]
    weights: tuple[float, ...]
    source: str
    as_of: datetime
    currency: str = "USD"
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.values) != len(self.weights):
            raise ValueError("values and weights must have the same length")
        if not self.values:
            raise ValueError("a price distribution needs at least one observation")
        if any(w < 0 for w in self.weights):
            raise ValueError("weights must be non-negative")
        if sum(self.weights) <= 0:
            raise ValueError("weights must sum to a positive value")

    # ------------------------------------------------------------------
    # Derived statistics
    # ------------------------------------------------------------------

    @property
    def sample_count(self) -> int:
        """Number of underlying observations."""
        return len(self.values)

    @property
    def mean(self) -> float:
        """Weighted mean price."""
        weights = np.asarray(self.weights, dtype=np.float64)
        values = np.asarray(self.values, dtype=np.float64)
        return float(np.dot(values, weights) / weights.sum())

    @property
    def stddev(self) -> float:
        """Weighted population standard deviation of the price."""
        weights = np.asarray(self.weights, dtype=np.float64)
        values = np.asarray(self.values, dtype=np.float64)
        mean = self.mean
        variance = float(np.dot(weights, (values - mean) ** 2) / weights.sum())
        return float(np.sqrt(max(variance, 0.0)))

    @property
    def minimum(self) -> float:
        """Smallest observed price."""
        return float(min(self.values))

    @property
    def maximum(self) -> float:
        """Largest observed price."""
        return float(max(self.values))

    def quantile(self, q: float) -> float:
        """Return the weighted ``q`` quantile (``q`` in ``[0, 1]``)."""
        if not 0.0 <= q <= 1.0:
            raise ValueError("q must be between 0 and 1")
        values = np.asarray(self.values, dtype=np.float64)
        weights = np.asarray(self.weights, dtype=np.float64)
        order = np.argsort(values)
        sorted_values = values[order]
        sorted_weights = weights[order]
        cumulative = np.cumsum(sorted_weights) / sorted_weights.sum()
        # np.interp requires increasing x; guard against zero-weight plateaus.
        safe_cumulative = np.maximum.accumulate(cumulative)
        safe_cumulative[-1] = 1.0
        return float(np.interp(q, safe_cumulative, sorted_values))

    def sample(self, rng: np.random.Generator, size: int) -> NDArray[np.float64]:
        """Draw ``size`` prices from the distribution (weighted resampling).

        Args:
            rng: Seeded NumPy generator.
            size: Number of draws.

        Returns:
            An array of ``size`` sampled prices.
        """
        if size <= 0:
            raise ValueError("size must be positive")
        values = np.asarray(self.values, dtype=np.float64)
        weights = np.asarray(self.weights, dtype=np.float64)
        probabilities = weights / weights.sum()
        cumulative = np.cumsum(probabilities)
        cumulative[-1] = 1.0
        draws = rng.random(size)
        indices = np.searchsorted(cumulative, draws, side="right")
        return values[np.clip(indices, 0, len(values) - 1)]

    @classmethod
    def from_parameters(
        cls,
        *,
        mean: float,
        stddev: float,
        source: str,
        as_of: datetime,
        currency: str = "USD",
        observations: int = 64,
        lognormal: bool = True,
        minimum: float = 0.0,
    ) -> PriceDistribution:
        """Build a distribution from a mean and standard deviation.

        Used when a cell has no stored observations but the caller still has a
        defensible parametric view (for example a partner quote or a test
        fixture).

        Args:
            mean: Expected price.
            stddev: Price dispersion.
            source: Source tag.
            as_of: Validity timestamp.
            currency: ISO currency code.
            observations: How many synthetic support points to generate.
            lognormal: Use a log-normal shape (positive, right-skewed) instead
                of a normal shape.
            minimum: Hard floor applied to the generated support points.

        Returns:
            A :class:`PriceDistribution` backed by generated support points.
        """
        if observations <= 0:
            raise ValueError("observations must be positive")
        if not math.isfinite(mean):
            raise ValueError("mean must be a finite number")
        if not math.isfinite(stddev):
            raise ValueError("stddev must be a finite number")
        if mean < 0:
            raise ValueError("mean must be non-negative")
        if stddev < 0:
            raise ValueError("stddev must be non-negative")

        # Deterministic support points (no RNG) so the result is reproducible.
        quantiles = [(i + 0.5) / observations for i in range(observations)]
        if lognormal and mean > 0:
            sigma = stddev / mean
            values = [
                max(minimum, mean * float(np.exp(sigma * normal_quantile(q) - (sigma**2) / 2)))
                for q in quantiles
            ]
        else:
            spread = stddev if stddev > 0 else 0.0
            values = [max(minimum, mean + spread * normal_quantile(q)) for q in quantiles]

        return cls(
            values=tuple(round(v, 4) for v in values),
            weights=tuple(1.0 for _ in values),
            source=source,
            as_of=as_of,
            currency=currency,
        )


@runtime_checkable
class PriceSource(Protocol):
    """Protocol every price adapter implements.

    Implementations may be backed by synthetic data (Phase 2), the eBay Browse
    API or partner CSV imports (Phase 3). The decision engine only ever sees
    this protocol, so the engine code does not change when the data source
    does.
    """

    @property
    def source_tag(self) -> str:
        """The tag the observations from this source carry."""
        ...

    async def get_distribution(
        self,
        sku_id: UUID,
        grade: str,
        channel: str,
        as_of: datetime,
    ) -> PriceDistribution:
        """Return the sale-price distribution for one (sku, grade, channel) cell.

        Args:
            sku_id: SKU the price applies to.
            grade: Condition grade (``A``/``B``/``C``/``D``).
            channel: Disposition channel the price belongs to.
            as_of: Only observations at or before this timestamp are used.

        Returns:
            The distribution for the requested cell.

        Raises:
            PriceSourceNotFoundError: If the cell has no usable observations.
            PriceSourceError: If the source cannot answer.
        """
        ...


def norm_ppf(q: float) -> float:
    """Return the standard-normal quantile for ``q``.

    Uses Peter Acklam's rational approximation, refined with one Halley step.
    Accurate to roughly 1e-9 over the whole open interval, and safe at the
    extremes (no domain errors, no NaNs).

    Args:
        q: Probability in ``(0, 1)``.

    Returns:
        The standard-normal quantile.

    Raises:
        ValueError: If ``q`` is outside ``(0, 1)``.
    """
    if not 0.0 < q < 1.0:
        raise ValueError("q must be strictly between 0 and 1")

    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    )
    p_low = 0.02425
    p_high = 1.0 - p_low

    if q < p_low:
        u = math.sqrt(-2.0 * math.log(q))
        x = (((((c[0] * u + c[1]) * u + c[2]) * u + c[3]) * u + c[4]) * u + c[5]) / (
            (((d[0] * u + d[1]) * u + d[2]) * u + d[3]) * u + 1.0
        )
    elif q > p_high:
        u = math.sqrt(-2.0 * math.log(1.0 - q))
        x = -(((((c[0] * u + c[1]) * u + c[2]) * u + c[3]) * u + c[4]) * u + c[5]) / (
            (((d[0] * u + d[1]) * u + d[2]) * u + d[3]) * u + 1.0
        )
    else:
        u = q - 0.5
        r = u * u
        x = (
            (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
            * u
            / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
        )

    # One Halley refinement step.
    error = 0.5 * math.erfc(-x / math.sqrt(2.0)) - q
    if error > 0:
        u = error * math.sqrt(2.0 * math.pi) * math.exp(x * x / 2.0)
    else:
        u = -error * math.sqrt(2.0 * math.pi) * math.exp(-x * x / 2.0)
    refined = x - u / (1.0 + x * u / 2.0)
    return float(refined)


def normal_quantile(q: float) -> float:
    """Return the standard-normal quantile for ``q``."""
    return norm_ppf(q)


def weighted_quantiles(
    values: Sequence[float], weights: Sequence[float], quantiles: Sequence[float]
) -> list[float]:
    """Compute weighted quantiles for a sequence of observations.

    Args:
        values: Observation values.
        weights: Observation weights.
        quantiles: Quantiles to compute, each in ``[0, 1]``.

    Returns:
        The computed quantiles, in the order requested.
    """
    distribution = PriceDistribution(
        values=tuple(values),
        weights=tuple(weights),
        source="inline",
        as_of=datetime.min,
    )
    return [distribution.quantile(q) for q in quantiles]
