"""
Confidence and the SAFE_DEFAULT gate (Phase 2 - F2.7).

Confidence answers one question: *how likely is it that the recommended
channel is the right call?*

For every Monte Carlo draw the engine compares each channel's net value
against the best net in that draw. A channel counts as "within the margin"
when it is no more than 5 % away from the best net. The confidence of the
recommended channel is the probability that it is the **only** channel inside
that margin - if a rival channel is just as good in a given draw, the draw
does not count as a confident recommendation.

When the confidence falls below the configured threshold the engine stops
recommending a channel and returns ``SAFE_DEFAULT`` instead: the channel with
the highest p10 net, which is the most conservative floor available.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray

from secondroute.decision.evaluator import ChannelEvaluation

__all__ = [
    "SAFE_DEFAULT",
    "ConfidenceResult",
    "apply_confidence_gate",
    "compute_confidence",
    "highest_p10_channel",
]

#: Sentinel channel returned when confidence is too low.
SAFE_DEFAULT: Final[str] = "SAFE_DEFAULT"

#: Margin used to decide whether a channel is "close enough" to the best net.
DEFAULT_MARGIN: Final[float] = 0.05


@dataclass(frozen=True, slots=True)
class ConfidenceResult:
    """The outcome of the confidence computation.

    Attributes:
        confidence: Probability the recommended channel is the right call.
        margin: Margin used.
        threshold: Threshold the confidence was compared against.
        recommended_channel: Channel the engine wanted to recommend.
        fallback_channel: Conservative channel used when the gate fails.
        within_margin_share: Share of draws the recommended channel was inside
            the margin (ignoring whether a rival was too).
    """

    confidence: float
    margin: float
    threshold: float
    recommended_channel: str
    fallback_channel: str | None = None
    within_margin_share: float = 0.0

    @property
    def passed(self) -> bool:
        """Whether the confidence clears the threshold."""
        return self.confidence >= self.threshold


def compute_confidence(
    joint_draws: NDArray[np.float64],
    recommended_index: int,
    *,
    margin: float = DEFAULT_MARGIN,
) -> tuple[float, float]:
    """Compute the confidence of a recommended channel.

    Args:
        joint_draws: ``(n_channels, n_samples)`` matrix of net draws.
        recommended_index: Row index of the recommended channel.
        margin: Fraction of the best net treated as "close enough".

    Returns:
        A ``(confidence, within_margin_share)`` tuple. Confidence is the
        probability that the recommended channel is the only one inside the
        margin; ``within_margin_share`` ignores the uniqueness requirement.
    """
    if joint_draws.size == 0:
        return 0.0, 0.0
    if not 0 <= recommended_index < joint_draws.shape[0]:
        raise IndexError("recommended_index out of range")

    best = joint_draws.max(axis=0)
    threshold = best - margin * np.abs(best)
    within = joint_draws >= threshold
    within_counts = within.sum(axis=0)

    recommended_within = within[recommended_index]
    unique = within_counts == 1
    confidence = float(np.mean(recommended_within & unique))
    within_share = float(np.mean(recommended_within))
    return confidence, within_share


def highest_p10_channel(channels: tuple[ChannelEvaluation, ...]) -> str | None:
    """Return the eligible channel with the highest p10 net.

    This is the SAFE_DEFAULT fallback: the most conservative floor we can
    offer.

    Args:
        channels: Evaluated channels.

    Returns:
        The channel name, or ``None`` when no channel is eligible.
    """
    eligible = [channel for channel in channels if channel.eligible]
    if not eligible:
        return None
    return max(eligible, key=lambda channel: channel.p10).channel


def apply_confidence_gate(
    channels: tuple[ChannelEvaluation, ...],
    joint_draws: NDArray[np.float64],
    recommended_index: int,
    recommended_channel: str,
    *,
    threshold: float,
    margin: float = DEFAULT_MARGIN,
) -> tuple[str, bool, ConfidenceResult]:
    """Apply the confidence gate.

    When the confidence clears the threshold the recommended channel is
    returned unchanged. When it does not, the gate returns ``SAFE_DEFAULT``
    and the conservative floor (the eligible channel with the highest p10) is
    recorded separately.

    Args:
        channels: Evaluated channels.
        joint_draws: Joint Monte Carlo draws.
        recommended_index: Row index of the recommended channel inside
            ``joint_draws``.
        recommended_channel: Name of the recommended channel.
        threshold: Minimum confidence required to recommend a channel.
        margin: Fraction of the best net treated as "close enough".

    Returns:
        A ``(channel, fallback_used, result)`` tuple.
    """
    confidence, within_share = compute_confidence(joint_draws, recommended_index, margin=margin)
    fallback_channel = highest_p10_channel(channels)
    result = ConfidenceResult(
        confidence=confidence,
        margin=margin,
        threshold=threshold,
        recommended_channel=recommended_channel,
        fallback_channel=fallback_channel,
        within_margin_share=within_share,
    )

    if confidence >= threshold:
        return recommended_channel, False, result

    return SAFE_DEFAULT, True, result
