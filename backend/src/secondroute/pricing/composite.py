"""
Composite price source.

Dispatches to a different price source per disposition channel. This is how
the engine picks up a channel-specific adapter - the parts source for
``PARTS_HARVEST``, the market source for the resale channels - without the
engine knowing that any of it is happening.

The decision code stays exactly as it was in Phase 2: it still takes one
price source and asks it for a distribution.
"""

from __future__ import annotations

from datetime import datetime
from typing import Mapping
from uuid import UUID

from secondroute.core.logging import get_logger
from secondroute.pricing.protocols import PriceDistribution, PriceSource

logger = get_logger(__name__)

__all__ = ["CompositePriceSource"]


class CompositePriceSource:
    """A price source that dispatches per channel.

    Attributes:
        sources: The source for each channel.
        default: The source used for channels with no specific source.
    """

    def __init__(
        self,
        sources: Mapping[str, PriceSource],
        default: PriceSource,
    ) -> None:
        """Build the composite.

        Args:
            sources: The source for each channel.
            default: The source used when a channel has no specific source.
        """
        self.sources = dict(sources)
        self.default = default

    @property
    def source_tag(self) -> str:
        """A tag describing the composite."""
        return "composite:" + ",".join(sorted(self.sources))

    async def get_distribution(
        self,
        sku_id: UUID,
        grade: str,
        channel: str,
        as_of: datetime,
    ) -> PriceDistribution:
        """Return the distribution for one cell, from the right source.

        Args:
            sku_id: The SKU the price applies to.
            grade: The condition grade.
            channel: The disposition channel.
            as_of: The reference time.

        Returns:
            The distribution for the requested cell.
        """
        source = self.sources.get(channel, self.default)
        return await source.get_distribution(sku_id, grade, channel, as_of)
