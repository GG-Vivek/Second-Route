"""
Cost table models (Phase 2 - F2.4).

Every cost the decision engine subtracts from a sale price lives here: fees,
logistics, handling, repair defaults and holding costs. Each row carries a
``source`` and an ``as_of`` date so a number can always be traced back to
where it came from (PLAN.md principle 6).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from secondroute.core.db import Base

# Registers the organizations table so the foreign key below resolves.
from secondroute.identity.organizations import Organization  # noqa: F401


class CostKind:
    """The kinds of cost the decision engine understands.

    The string values are the stable keys stored in ``cost_tables.kind``.
    """

    CHANNEL_FEE_PCT = "channel_fee_pct"
    FIXED_FEE = "fixed_fee"
    LOGISTICS_COST = "logistics_cost"
    HANDLING_COST = "handling_cost"
    REPAIR_COST = "repair_cost"
    HOLDING_COST_PER_DAY = "holding_cost_per_day"
    EXPECTED_DAYS_TO_SELL = "expected_days_to_sell"
    RESALE_RECOVERY_PCT = "resale_recovery_pct"

    ALL = (
        CHANNEL_FEE_PCT,
        FIXED_FEE,
        LOGISTICS_COST,
        HANDLING_COST,
        REPAIR_COST,
        HOLDING_COST_PER_DAY,
        EXPECTED_DAYS_TO_SELL,
        RESALE_RECOVERY_PCT,
    )


class CostTable(Base):
    """One cost value.

    Attributes:
        kind: What the cost is (see :class:`CostKind`).
        key: What it applies to - usually a channel, or ``channel:grade``.
        value: The numeric value.
        source: Where the number came from. Required, never empty.
        as_of: Date the number was current.
    """

    __tablename__ = "cost_tables"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    as_of: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("org_id", "kind", "key", name="uq_cost_table_scope"),
        Index("ix_cost_tables_kind_key", "kind", "key"),
    )

    def __repr__(self) -> str:
        return f"<CostTable(kind={self.kind}, key={self.key}, value={self.value})>"
