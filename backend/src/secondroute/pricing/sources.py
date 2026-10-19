"""
Price source adapters (Phase 2 - F2.2).

Two implementations of the :class:`~secondroute.pricing.protocols.PriceSource`
protocol ship in Phase 2:

* :class:`DatabasePriceSource` - reads stored ``price_observations`` rows.
* :class:`SyntheticPriceSource` - derives a distribution analytically so the
  Phase 2 demo and tests run without a seeded database.

Phase 3 adds real adapters (eBay Browse API, partner CSV) behind the same
protocol. The decision engine is unaffected by that change.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone, UTC
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.logging import get_logger
from secondroute.pricing.models import PriceObservation
from secondroute.pricing.protocols import PriceDistribution, PriceSourceNotFoundError

logger = get_logger(__name__)

__all__ = [
    "DatabasePriceSource",
    "SyntheticPriceSource",
    "seed_synthetic_price_observations",
    "stable_cell_hash",
]


class DatabasePriceSource:
    """Serves price distributions from the ``price_observations`` table.

    Attributes:
        source_tag: Only rows with this ``source`` are considered.
    """

    source_tag = "synthetic"

    def __init__(self, session: AsyncSession, source_tag: str = "synthetic") -> None:
        self._session = session
        self.source_tag = source_tag

    async def get_distribution(
        self,
        sku_id: UUID,
        grade: str,
        channel: str,
        as_of: datetime,
    ) -> PriceDistribution:
        """Return the observed price distribution for one cell.

        Args:
            sku_id: SKU the price applies to.
            grade: Condition grade.
            channel: Disposition channel.
            as_of: Only observations at or before this timestamp are used.

        Returns:
            The distribution for the requested cell.

        Raises:
            PriceSourceNotFoundError: If no usable observation exists.
        """
        result = await self._session.execute(
            select(PriceObservation)
            .where(
                PriceObservation.sku_id == sku_id,
                PriceObservation.grade == grade,
                PriceObservation.channel == channel,
                PriceObservation.source == self.source_tag,
                PriceObservation.observed_at <= as_of,
            )
            .order_by(PriceObservation.observed_at.desc())
        )
        rows = result.scalars().all()

        if not rows:
            raise PriceSourceNotFoundError(
                f"No {self.source_tag} price observations for sku={sku_id} "
                f"grade={grade} channel={channel} as_of={as_of.isoformat()}"
            )

        values = tuple(float(row.price) for row in rows)
        weights = tuple(max(float(row.weight), 1e-9) for row in rows)
        latest = max(row.observed_at for row in rows)

        return PriceDistribution(
            values=values,
            weights=weights,
            source=self.source_tag,
            as_of=latest,
            currency=rows[0].currency,
            metadata={"sample_count": str(len(rows))},
        )


class SyntheticPriceSource:
    """Price source backed by the synthetic generator.

    Unlike the database-backed source this one needs no stored rows: it
    derives a log-normal price distribution analytically from the grade, the
    family value multiplier and the channel's share of the base value.

    It exists so the Phase 2 demo and tests run without a seeded database.
    Phase 3 replaces it with real adapters behind the same protocol.
    """

    source_tag = "synthetic"

    #: Base resale value per grade, in USD.
    GRADE_BASE_VALUE_USD: dict[str, float] = {
        "A": 1450.0,
        "B": 1150.0,
        "C": 780.0,
        "D": 420.0,
    }

    #: Share of the grade base value a buyer pays per channel.
    CHANNEL_VALUE_SHARE: dict[str, float] = {
        "RESELL_OPEN_BOX": 0.92,
        "RESELL_REFURB": 0.78,
        "RECYCLE": 0.06,
        "DONATE": 0.0,
    }

    #: Coefficient of variation per channel.
    CHANNEL_PRICE_CV: dict[str, float] = {
        "RESELL_OPEN_BOX": 0.12,
        "RESELL_REFURB": 0.18,
        "RECYCLE": 0.22,
        "DONATE": 0.0,
    }

    #: Value multiplier per SKU family.
    FAMILY_VALUE_MULTIPLIER: dict[str, float] = {
        "MacBook Pro": 1.35,
        "MacBook Air": 0.62,
        "ThinkPad X1 Carbon": 0.72,
        "Dell XPS 13": 0.61,
    }

    def __init__(self, sku_family: str = "MacBook Pro", observations: int = 64) -> None:
        self.sku_family = sku_family
        self.observations = observations

    async def get_distribution(
        self,
        sku_id: UUID,
        grade: str,
        channel: str,
        as_of: datetime,
    ) -> PriceDistribution:
        """Return the synthetic price distribution for one cell.

        Args:
            sku_id: Unused by the synthetic source, but part of the protocol.
            grade: Condition grade.
            channel: Disposition channel.
            as_of: Timestamp the distribution is valid as of.

        Returns:
            The distribution for the requested cell.

        Raises:
            PriceSourceNotFoundError: If the grade or channel is unknown.
        """
        del sku_id  # the synthetic source is family-scoped, not SKU-scoped
        base = self.GRADE_BASE_VALUE_USD.get(grade)
        share = self.CHANNEL_VALUE_SHARE.get(channel)
        if base is None:
            raise PriceSourceNotFoundError(f"Unknown grade {grade!r}")
        if share is None:
            raise PriceSourceNotFoundError(f"Unknown channel {channel!r}")

        multiplier = self.FAMILY_VALUE_MULTIPLIER.get(self.sku_family, 1.0)
        mean = base * multiplier * share
        cv = self.CHANNEL_PRICE_CV.get(channel, 0.15)

        return PriceDistribution.from_parameters(
            mean=mean,
            stddev=mean * cv,
            source=self.source_tag,
            as_of=as_of,
            observations=self.observations,
            lognormal=True,
            minimum=0.0,
        )

    def with_family(self, family: str) -> SyntheticPriceSource:
        """Return a copy of this source bound to a different SKU family."""
        return SyntheticPriceSource(sku_family=family, observations=self.observations)


async def seed_synthetic_price_observations(
    session: AsyncSession,
    sku_ids: Sequence[tuple[UUID, str]],
    *,
    seed: int = 42,
    observations_per_cell: int = 40,
    as_of: datetime | None = None,
) -> int:
    """Insert synthetic price observations for the given SKU ids.

    The operation is idempotent: running it twice does not create duplicates.

    Args:
        session: Database session.
        sku_ids: ``(sku_id, family)`` pairs to seed.
        seed: Seed for the synthetic generator.
        observations_per_cell: Observations per (sku, grade, channel) cell.
        as_of: Timestamp applied to every observation.

    Returns:
        The number of rows inserted.
    """
    from synthetic.generator import SyntheticReturnGenerator

    if not sku_ids:
        return 0

    generator = SyntheticReturnGenerator(seed=seed)
    observations = generator.generate_price_observations(
        observations_per_cell=observations_per_cell, as_of=as_of
    )

    existing_result = await session.execute(
        select(PriceObservation.sku_id).where(
            PriceObservation.source == "synthetic",
            PriceObservation.sku_id.in_([sku_id for sku_id, _ in sku_ids]),
        )
    )
    already_seeded = {row.sku_id for row in existing_result.all()}
    if already_seeded:
        logger.info("synthetic_price_observations_already_seeded", rows=len(already_seeded))
        return 0

    inserted = 0
    for sku_id, family in sku_ids:
        for row in observations:
            if row.family != family:
                continue
            session.add(
                PriceObservation(
                    sku_id=sku_id,
                    grade=row.grade,
                    channel=row.channel,
                    price=row.price,
                    currency=row.currency,
                    source="synthetic",
                    observed_at=row.observed_at,
                    weight=row.weight,
                    is_synthetic=True,
                    as_of=row.observed_at.date(),
                )
            )
            inserted += 1

    await session.flush()
    logger.info("synthetic_price_observations_seeded", rows=inserted)
    return inserted


def stable_cell_hash(sku_id: UUID, grade: str, channel: str) -> str:
    """Return a stable hash for a price cell (used for deterministic seeding)."""
    payload = f"{sku_id}:{grade}:{channel}".encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def now_utc() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)
