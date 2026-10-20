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
from secondroute.pricing.protocols import (
    PriceDistribution,
    PriceSource,
    PriceSourceNotFoundError,
)

logger = get_logger(__name__)

__all__ = ["CompositePriceSource", "FallbackPriceSource"]


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

    @property
    def stale_sources(self) -> frozenset[str]:
        """The stale sources of every member of the composite."""
        stale: set[str] = set()
        for source in (*self.sources.values(), self.default):
            member_stale = getattr(source, "stale_sources", None)
            if member_stale:
                stale.update(str(name) for name in member_stale)
        return frozenset(stale)

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


class FallbackPriceSource:
    """Tries each source in turn and uses the first one that answers.

    This is how the system prefers real market data but still works before
    any has been collected: the database source goes first, the synthetic one
    second. The card says which one answered.

    Attributes:
        source_tag: A tag describing the chain.
    """

    def __init__(self, *sources: PriceSource) -> None:
        """Build the chain.

        Args:
            sources: The sources, in the order they are tried.
        """
        self.sources = list(sources)

    @property
    def source_tag(self) -> str:
        """A tag describing the chain."""
        return "fallback:" + ",".join(
            sorted(getattr(source, "source_tag", type(source).__name__) for source in self.sources)
        )

    @property
    def stale_sources(self) -> frozenset[str]:
        """The stale sources of every member of the chain."""
        stale: set[str] = set()
        for source in self.sources:
            member_stale = getattr(source, "stale_sources", None)
            if member_stale:
                stale.update(str(name) for name in member_stale)
        return frozenset(stale)

    async def get_distribution(
        self,
        sku_id: UUID,
        grade: str,
        channel: str,
        as_of: datetime,
    ) -> PriceDistribution:
        """Return the first distribution any source can answer.

        Args:
            sku_id: The SKU the price applies to.
            grade: The condition grade.
            channel: The disposition channel.
            as_of: The reference time.

        Returns:
            The distribution from the first source that answers.

        Raises:
            PriceSourceNotFoundError: If no source can answer.
        """
        for source in self.sources:
            try:
                return await source.get_distribution(sku_id, grade, channel, as_of)
            except PriceSourceNotFoundError:
                continue
        raise PriceSourceNotFoundError(
            f"no price source could answer for sku={sku_id} grade={grade} channel={channel}"
        )
