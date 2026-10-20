"""
Baseline policies for the backtest (Phase 5 - F5.6).

The backtest compares the engine against the policy the partner uses
today. Which channel that is depends on the partner and is not yet known
(PLAN.md, Appendix F), so the baseline is a protocol with a configurable
implementation rather than a hard-coded constant. The report always names
the baseline it used, so a reader can tell what the comparison is against.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

__all__ = [
    "BaselinePolicy",
    "FixedChannelBaseline",
    "MostCommonChannelBaseline",
]


@runtime_checkable
class BaselinePolicy(Protocol):
    """A policy the engine is compared against.

    The name and the description are read-only: they identify the policy
    in the report, and a policy does not get to change its own identity
    after it has been described.
    """

    @property
    def name(self) -> str:
        """Identifies the policy in the report."""
        ...

    @property
    def description(self) -> str:
        """A sentence describing what the policy does."""
        ...

    def channel_for(self, decision: Any) -> str | None:
        """Return the channel the baseline would pick for a decision.

        Args:
            decision: The decision being replayed.

        Returns:
            The channel name, or ``None`` when the policy has no answer for
            this decision.
        """
        ...


@dataclass(frozen=True, slots=True)
class FixedChannelBaseline:
    """Always recommends the same channel.

    This is the honest model of a partner with a fixed habit: everything
    goes to the same channel, whatever the unit looks like.

    Attributes:
        channel: The channel the partner always uses.
        name: Identifies the policy in the report.
        description: A sentence describing what the policy does.
    """

    channel: str
    name: str = "fixed-channel"
    description: str = "Always recommends the same channel."

    def channel_for(self, decision: Any) -> str | None:  # noqa: ARG002
        """Return the fixed channel."""
        return self.channel


@dataclass(frozen=True, slots=True)
class MostCommonChannelBaseline:
    """Recommends the channel the partner used most often in the window.

    This is the empirical version of the partner's habit: it reads the
    channel that was actually taken on the units being replayed and
    applies it to all of them. The count is reported so a reader can see
    how much of the partner's behaviour the baseline captured.

    Attributes:
        counts: How many times each channel was taken, keyed by channel.
        name: Identifies the policy in the report.
        description: A sentence describing what the policy does.
    """

    counts: dict[str, int]
    name: str = "most-common-channel"
    description: str = "Recommends the channel the partner used most often."

    def channel_for(self, decision: Any) -> str | None:  # noqa: ARG002
        """Return the most frequently used channel, if there is one."""
        if not self.counts:
            return None
        # Sort by count, then by name, so the choice is deterministic when
        # two channels were taken equally often.
        return sorted(self.counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
