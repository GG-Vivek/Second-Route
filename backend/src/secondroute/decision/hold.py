"""
The HOLD channel (Phase 3 - F3.8).

Holding a unit is a bet on the price going up. The price of the HOLD channel
is therefore the *expected future price*, not today's price.

The price source wraps the market source and scales it by the expected
change over the hold window. The cost of holding is already in the cost
tables (the per-day holding cost times the days to sell).

HOLD is only on the table when the launch calendar says it is safe. The
decision is made in :func:`secondroute.ingest.launch.hold_decision` and
applied by the caller, which is the only place that has the launch events.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence
from uuid import UUID

from secondroute.pricing.protocols import (
    PriceDistribution,
    PriceSource,
    PriceSourceNotFoundError,
)

__all__ = ["HoldPriceSource"]


class HoldPriceSource:
    """A price source for the ``HOLD`` channel.

    Attributes:
        source_tag: The source tag recorded on the observations.
    """

    source_tag = "hold"

    def __init__(
        self,
        base: PriceSource,
        expected_change: float,
        *,
        window_days: int,
        base_channel: str = "RESELL_OPEN_BOX",
    ) -> None:
        """Build the source.

        Args:
            base: The source that gives today's price.
            expected_change: The expected fractional change over the window.
                Positive means the price is expected to rise.
            window_days: The length of the hold window.
            base_channel: The channel the base source is asked about. The
                base source knows about resale channels, not about HOLD.
        """
        self.base = base
        self.expected_change = expected_change
        self.window_days = window_days
        self.base_channel = base_channel

    async def get_distribution(
        self,
        sku_id: UUID,
        grade: str,
        channel: str,
        as_of: datetime,
    ) -> PriceDistribution:
        """Return the expected future price distribution.

        Args:
            sku_id: The SKU the price applies to.
            grade: The condition grade.
            channel: The disposition channel. Only ``HOLD`` is served.
            as_of: The reference time.

        Returns:
            The distribution of the expected future price.

        Raises:
            PriceSourceNotFoundError: If the channel is not the hold channel.
        """
        if channel != "HOLD":
            raise PriceSourceNotFoundError(f"the hold source only serves HOLD, not {channel!r}")

        base = await self.base.get_distribution(sku_id, grade, self.base_channel, as_of)
        multiplier = 1.0 + self.expected_change

        return PriceDistribution(
            values=tuple(value * multiplier for value in base.values),
            weights=base.weights,
            source=f"{self.source_tag}:{base.source}",
            as_of=base.as_of,
            currency=base.currency,
            metadata={
                **base.metadata,
                "expected_change": f"{self.expected_change:.6f}",
                "window_days": str(self.window_days),
            },
        )
