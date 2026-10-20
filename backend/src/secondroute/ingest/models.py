"""
Phase 3 data models.

The tables that market and component intelligence writes into:

* :class:`ImportFile` - the record of a partner sales import (F3.2)
* :class:`ComponentPrice` - the price of a recoverable component (F3.5)
* :class:`TeardownYield` - how much of a component survives a teardown (F3.6)
* :class:`DemandSignal` - a demand observation for a SKU family (F3.7)
* :class:`LaunchEvent` - a known product launch (F3.8)
* :class:`DecayParam` - the fitted price decay for a family and grade (F3.8)
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
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from secondroute.core.db import Base

# Registers the organizations table so the foreign keys below resolve.
from secondroute.identity.organizations import Organization  # noqa: F401


class SourceHealth(Base):
    """The health of one data source.

    The engine reads this to decide whether a source is fresh enough to
    trust. A stale source drags the confidence of any decision that leans on
    it down.

    Attributes:
        source: The source tag (e.g. ``partner_a``).
        last_success_at: When the source last answered.
        last_error_at: When the source last failed.
        error_count: How many errors the source has had.
        message: The last error message.
    """

    __tablename__ = "source_health"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (UniqueConstraint("source", name="uq_source_health"),)

    def __repr__(self) -> str:
        return (
            f"<SourceHealth(source={self.source}, errors={self.error_count}, "
            f"last_success={self.last_success_at})>"
        )


class ImportFile(Base):
    """The record of one partner sales import.

    The file hash is what makes the import idempotent: re-importing the same
    file changes nothing.

    Attributes:
        file_hash: SHA-256 of the uploaded bytes.
        filename: The original filename.
        source: Where the data came from (the partner's name).
        status: ``completed`` or ``rejected``.
        rows_imported: How many rows were written.
        rows_rejected: How many rows were rejected.
        imported_at: When the import ran.
    """

    __tablename__ = "import_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="completed")
    rows_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    import_kind: Mapped[str] = mapped_column(String(40), nullable=False, default="sales")
    imported_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    report_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    __table_args__ = (
        UniqueConstraint("org_id", "import_kind", "file_hash", name="uq_import_file_hash"),
        Index("ix_import_files_source", "source"),
    )

    def __repr__(self) -> str:
        return (
            f"<ImportFile(file_hash={self.file_hash[:12]}..., source={self.source}, "
            f"imported={self.rows_imported}, rejected={self.rows_rejected})>"
        )


class ComponentPrice(Base):
    """The price of one recoverable component.

    Attributes:
        component_type: What the component is (e.g. ``display``, ``battery``).
        price_per_unit: What one unit is worth.
        unit: The unit the price is quoted in.
        source: Where the price came from.
        as_of: When the price was current.
        confidence_weight: How much the price can be trusted, ``0``-``1``.
    """

    __tablename__ = "component_prices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    component_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    price_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="USD")
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    as_of: Mapped[date] = mapped_column(Date, nullable=False, default=date.today, index=True)
    confidence_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("org_id", "component_type", "source", "as_of", name="uq_component_price"),
        Index("ix_component_prices_type", "component_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<ComponentPrice(component_type={self.component_type}, "
            f"price={self.price_per_unit}, source={self.source})>"
        )


class TeardownYield(Base):
    """How much of a component survives a teardown.

    Attributes:
        component_type: The component.
        sku_family: The family it was taken from. Empty means "any family".
        yield_ratio: The share of the component that can be recovered.
        source: Where the ratio came from.
        as_of: When the ratio was current.
    """

    __tablename__ = "teardown_yields"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    component_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    sku_family: Mapped[str] = mapped_column(String(100), nullable=False, default="", index=True)
    yield_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    labor_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    as_of: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "component_type", "sku_family", "source", "as_of", name="uq_teardown_yield"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<TeardownYield(component_type={self.component_type}, "
            f"family={self.sku_family}, yield={self.yield_ratio})>"
        )


class DemandSignal(Base):
    """A demand observation for a SKU family.

    Attributes:
        sku_family: The family the demand is for.
        period_start: First day of the period.
        period_end: Last day of the period.
        views: The count over the period.
        source: Where the count came from.
        query_params: The query that produced it, stored so the number can be
            reproduced.
    """

    __tablename__ = "demand_signals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku_family: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    views: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    query_params: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "sku_family", "period_start", "period_end", "source", name="uq_demand_signal"
        ),
        Index("ix_demand_signals_family_period", "sku_family", "period_start"),
    )

    def __repr__(self) -> str:
        return (
            f"<DemandSignal(family={self.sku_family}, "
            f"period={self.period_start}..{self.period_end}, views={self.views})>"
        )


class LaunchEvent(Base):
    """A known product launch.

    Attributes:
        sku_family: The family the launch affects.
        event_date: When the launch is expected.
        event_type: What kind of launch it is.
        source_url: Where the announcement is.
    """

    __tablename__ = "launch_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku_family: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("sku_family", "event_date", "event_type", name="uq_launch_event"),
    )

    def __repr__(self) -> str:
        return (
            f"<LaunchEvent(family={self.sku_family}, date={self.event_date}, "
            f"type={self.event_type})>"
        )


class DecayParam(Base):
    """The fitted price decay for a family and grade.

    Attributes:
        sku_family: The family.
        grade: The grade.
        rate_per_day: How much the price decays per day, as a fraction.
        fitted_at: When the rate was fitted.
        model_version: The model that fitted it.
    """

    __tablename__ = "decay_params"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku_family: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    grade: Mapped[str] = mapped_column(String(4), nullable=False, index=True)
    rate_per_day: Mapped[float] = mapped_column(Float, nullable=False)
    fitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    model_version: Mapped[str] = mapped_column(String(60), nullable=False, default="decay-v1")

    __table_args__ = (UniqueConstraint("sku_family", "grade", name="uq_decay_param"),)

    def __repr__(self) -> str:
        return (
            f"<DecayParam(family={self.sku_family}, grade={self.grade}, rate={self.rate_per_day})>"
        )
