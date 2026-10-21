"""The decision distribution (F8.4).

The engine draws ten thousand net samples per channel. This module turns
those draws into a density histogram that an interface can draw, so that
the overlap between two channels can be seen rather than asserted.

The histogram is built from the samples themselves. It is never fitted
from a mean and a standard deviation: the engine samples from log-normal
price and cost factors, so a normal approximation would be visibly wrong
in the tails and would be, strictly speaking, a number with no source.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np
from numpy.typing import NDArray

__all__ = [
    "DEFAULT_BIN_COUNT",
    "ChannelDistribution",
    "DecisionDistribution",
    "DensityBin",
    "build_distribution",
]

#: How many bins the histogram has by default.
DEFAULT_BIN_COUNT = 96

#: The fraction of the span left empty at each end of the shared axis.
#: A little air keeps the shape of the distribution readable.
AXIS_PADDING = 0.04

#: The smallest axis span, so that a distribution with no spread still
#: produces a usable axis rather than a division by zero.
MIN_AXIS_SPAN = 1.0


@dataclass(frozen=True, slots=True)
class DensityBin:
    """One bar of the histogram.

    Attributes:
        x: The middle of the bar, in the same units as the net value.
        density: The probability density at that point. The bars of one
            channel sum, with their width, to one.
    """

    x: float
    density: float


@dataclass(frozen=True, slots=True)
class ChannelDistribution:
    """The distribution of the net value for one channel.

    Attributes:
        channel: The channel name.
        eligible: Whether the channel could be used at all.
        exclusion_reason: Why it could not be used, when it could not.
        mean: Expected net.
        stddev: Standard deviation of the net.
        p10: Tenth percentile of the net.
        p50: Median of the net.
        p90: Ninetieth percentile of the net.
        probability_best: Probability this channel has the best net.
        bins: The density histogram, empty for an ineligible channel.
    """

    channel: str
    eligible: bool
    exclusion_reason: str | None
    mean: float
    stddev: float
    p10: float
    p50: float
    p90: float
    probability_best: float
    bins: tuple[DensityBin, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-ready form of this distribution."""
        return {
            "channel": self.channel,
            "eligible": self.eligible,
            "exclusion_reason": self.exclusion_reason,
            "mean": self.mean,
            "stddev": self.stddev,
            "p10": self.p10,
            "p50": self.p50,
            "p90": self.p90,
            "probability_best": self.probability_best,
            "bins": [{"x": b.x, "density": b.density} for b in self.bins],
        }


@dataclass(frozen=True, slots=True)
class DecisionDistribution:
    """The distributions of every channel, on one shared axis.

    Attributes:
        channels: One entry per evaluated channel, in evaluation order.
        axis_min: The left end of the shared axis.
        axis_max: The right end of the shared axis.
        bin_count: How many bars each channel has.
    """

    channels: tuple[ChannelDistribution, ...]
    axis_min: float
    axis_max: float
    bin_count: int

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-ready form of this distribution."""
        return {
            "axis": {"min": self.axis_min, "max": self.axis_max},
            "bin_count": self.bin_count,
            "channels": [c.to_dict() for c in self.channels],
        }


def _axis_bounds(
    draws: Sequence[NDArray[np.float64]],
    padding: float,
) -> tuple[float, float]:
    """Return the shared axis that every channel is drawn against."""
    values = np.concatenate([d for d in draws if d.size]) if draws else np.zeros(0)

    if values.size == 0:
        return 0.0, 1.0

    low = float(values.min())
    high = float(values.max())
    span = high - low

    if span < MIN_AXIS_SPAN:
        middle = (high + low) / 2
        half = MIN_AXIS_SPAN / 2
        return middle - half, middle + half

    pad = span * padding
    return low - pad, high + pad


def build_distribution(
    *,
    draws_by_channel: Mapping[str, NDArray[np.float64]],
    channels: Sequence[Mapping[str, Any]],
    probability_best: Mapping[str, float],
    bin_count: int = DEFAULT_BIN_COUNT,
    padding: float = AXIS_PADDING,
) -> DecisionDistribution:
    """Build the shared-axis density histogram of every channel.

    Args:
        draws_by_channel: The net samples of each eligible channel.
        channels: The evaluated channels, in evaluation order. Each entry
            carries the channel name and its eligibility.
        probability_best: The probability each channel has the best net.
        bin_count: How many bars each channel has.
        padding: The fraction of the span left empty at each end of the
            axis.

    Returns:
        The distribution of every channel, on one shared axis.

    Raises:
        ValueError: When the bin count is not positive.
    """
    if bin_count <= 0:
        raise ValueError("bin_count must be positive")

    eligible_draws = [draws_by_channel[c] for c in draws_by_channel if draws_by_channel[c].size]
    axis_min, axis_max = _axis_bounds(eligible_draws, padding)
    edges = np.linspace(axis_min, axis_max, bin_count + 1)
    centres = (edges[:-1] + edges[1:]) / 2

    results: list[ChannelDistribution] = []
    for channel in channels:
        name = str(channel["channel"])
        eligible = bool(channel.get("eligible", False))
        draws = draws_by_channel.get(name)

        if not eligible or draws is None or draws.size == 0:
            results.append(
                ChannelDistribution(
                    channel=name,
                    eligible=False,
                    exclusion_reason=channel.get("exclusion_reason"),
                    mean=float(channel.get("mean", 0.0)),
                    stddev=float(channel.get("stddev", 0.0)),
                    p10=float(channel.get("p10", 0.0)),
                    p50=float(channel.get("p50", 0.0)),
                    p90=float(channel.get("p90", 0.0)),
                    probability_best=float(probability_best.get(name, 0.0)),
                    bins=(),
                )
            )
            continue

        density, _ = np.histogram(draws, bins=edges, density=True)
        results.append(
            ChannelDistribution(
                channel=name,
                eligible=True,
                exclusion_reason=None,
                mean=float(channel.get("mean", 0.0)),
                stddev=float(channel.get("stddev", 0.0)),
                p10=float(channel.get("p10", 0.0)),
                p50=float(channel.get("p50", 0.0)),
                p90=float(channel.get("p90", 0.0)),
                probability_best=float(probability_best.get(name, 0.0)),
                bins=tuple(
                    DensityBin(x=float(centre), density=float(value))
                    for centre, value in zip(centres, density, strict=True)
                ),
            )
        )

    return DecisionDistribution(
        channels=tuple(results),
        axis_min=axis_min,
        axis_max=axis_max,
        bin_count=bin_count,
    )
