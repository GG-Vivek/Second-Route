"""
Risk profiles and the certainty equivalent (Phase 2 - F2.6).

Three profiles rank the channels:

* ``conservative`` - strongly risk averse, prefers the lower-variance channel.
* ``balanced`` - the default.
* ``aggressive`` - prefers the higher expected value even when it is noisy.

Ranking uses the certainty equivalent ``mean - lambda * stddev``. The
``lambda`` values live in application configuration so a retailer can be
tuned without a code change (F5.3 exposes them through the API).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from secondroute.core.config import settings
from secondroute.decision.evaluator import ChannelEvaluation

__all__ = [
    "RISK_PROFILES",
    "RiskProfile",
    "certainty_equivalent",
    "lambda_for",
    "rank_channels",
]

#: The profiles the engine understands.
RISK_PROFILES: Final[tuple[str, ...]] = ("conservative", "balanced", "aggressive")


@dataclass(frozen=True, slots=True)
class RiskProfile:
    """A risk profile: a name and its risk-aversion parameter.

    Attributes:
        name: Profile name.
        lam: Risk-aversion parameter (``lambda``).
    """

    name: str
    lam: float

    @property
    def description(self) -> str:
        """Return a short human-readable description."""
        if self.name == "conservative":
            return "Prefers the most predictable value, even at a lower expected return."
        if self.name == "aggressive":
            return "Prefers the highest expected value, accepting more variability."
        return "Balances expected value against variability."


def lambda_for(profile: str) -> float:
    """Return the risk-aversion parameter for a profile.

    Args:
        profile: Profile name.

    Returns:
        The ``lambda`` value. Unknown profiles fall back to ``balanced``.

    Raises:
        ValueError: If the profile name is empty.
    """
    if not profile:
        raise ValueError("profile must not be empty")
    lambdas = settings.RISK_PROFILE_LAMBDA
    if profile in lambdas:
        return float(lambdas[profile])
    return float(lambdas.get("balanced", 1.0))


def certainty_equivalent(mean: float, stddev: float, profile: str = "balanced") -> float:
    """Return the certainty equivalent of a distribution under a profile.

    Args:
        mean: Expected value.
        stddev: Standard deviation.
        profile: Risk profile name.

    Returns:
        ``mean - lambda * stddev``.
    """
    return mean - lambda_for(profile) * stddev


def rank_channels(
    channels: tuple[ChannelEvaluation, ...], profile: str = "balanced"
) -> list[tuple[str, float]]:
    """Rank eligible channels by certainty equivalent, best first.

    Args:
        channels: Evaluated channels.
        profile: Risk profile name.

    Returns:
        A list of ``(channel, certainty_equivalent)`` pairs, best first.
        Ineligible channels are excluded.
    """
    lam = lambda_for(profile)
    ranked = [
        (channel.channel, channel.mean - lam * channel.stddev)
        for channel in channels
        if channel.eligible
    ]
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked
