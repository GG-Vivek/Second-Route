"""
Price observation models (Phase 2 - F2.2).

A single table holds every price observation the system knows about, regardless
of whether it came from the synthetic generator (Phase 2) or a real market
adapter (Phase 3). The ``is_synthetic`` flag keeps synthetic rows out of real
reports.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from secondroute.core.db import Base

# Registers the organizations and skus tables so the foreign keys below resolve.
from secondroute.identity.models import SKU  # noqa: F401
from secondroute.identity.organizations import Organization  # noqa: F401


class PriceObservation(Base):
    """One observed sale price for a (SKU, grade, channel) cell.

    Attributes:
        sku_id: SKU the observation applies to.
        grade: Condition grade (``A``/``B``/``C``/``D``).
        channel: Disposition channel.
        price: Observed price in ``currency``.
        currency: ISO currency code.
        source: Where the observation came from (e.g. ``synthetic``).
        observed_at: When the price was observed.
        weight: Relative weight used when building a distribution.
        is_synthetic: True for rows produced by the synthetic generator.
    """

    __tablename__ = "price_observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skus.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    grade: Mapped[str] = mapped_column(String(4), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    as_of: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships
    sku = relationship("SKU", backref="price_observations")

    __table_args__ = (
        UniqueConstraint(
            "sku_id",
            "grade",
            "channel",
            "price",
            "source",
            "observed_at",
            name="uq_price_observation_cell",
        ),
        Index("ix_price_observations_cell", "sku_id", "grade", "channel"),
        Index("ix_price_observations_source_time", "source", "observed_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<PriceObservation(sku_id={self.sku_id}, grade={self.grade}, "
            f"channel={self.channel}, price={self.price}, source={self.source})>"
        )
