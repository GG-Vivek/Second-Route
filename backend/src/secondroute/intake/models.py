"""
Intake models for Phase 1.

Models for unit intake and tracking.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from secondroute.core.db import Base


class ReturnReasonCode(enum.StrEnum):
    """Return reason codes."""

    BUYER_REMORSE = "buyer_remorse"
    WRONG_ITEM = "wrong_item"
    DAMAGED_IN_SHIPPING = "damaged_in_shipping"
    DEFECTIVE = "defective"
    NOT_AS_DESCRIBED = "not_as_described"
    CHANGED_MIND = "changed_mind"
    BETTER_PRICE_FOUND = "better_price_found"
    NO_LONGER_NEEDED = "no_longer_needed"
    OTHER = "other"


class OrderChannel(enum.StrEnum):
    """Order channel where the unit was originally sold."""

    ONLINE = "online"
    RETAIL = "retail"
    B2B = "b2b"
    MARKETPLACE = "marketplace"
    OTHER = "other"


class UnitStatus(enum.StrEnum):
    """Unit status throughout the intake and disposition process."""

    RECEIVED = "received"
    INSPECTED = "inspected"
    DECIDED = "decided"
    DISPATCHED = "dispatched"
    SOLD = "sold"
    RECYCLED = "recycled"
    DONATED = "donated"


class Unit(Base):
    """Returned unit model."""

    __tablename__ = "units"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # FK added in Phase 5
    sku_id = Column(
        UUID(as_uuid=True), ForeignKey("skus.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    serial = Column(String(100), nullable=True, index=True)
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    return_reason_code: "Column[ReturnReasonCode]" = Column(  # type: ignore[assignment]
        Enum(ReturnReasonCode, name="return_reason_code_enum"), nullable=False
    )
    order_channel: "Column[OrderChannel]" = Column(
        Enum(OrderChannel, name="order_channel_enum"), nullable=False
    )  # type: ignore[assignment]
    status: "Column[UnitStatus]" = Column(
        Enum(UnitStatus, name="unit_status_enum"),
        nullable=False,
        default=UnitStatus.RECEIVED,
        index=True,
    )  # type: ignore[assignment]

    # Relationships
    sku = relationship("SKU", backref="units")
    inspections = relationship(
        "Inspection",
        back_populates="unit",
        cascade="all, delete-orphan",
        order_by="Inspection.created_at",
    )
    photos = relationship("Photo", back_populates="unit", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_units_org_status", "org_id", "status"),
        Index("ix_units_received_at", "received_at"),
    )

    def __repr__(self) -> str:
        return f"<Unit(id={self.id}, sku_id={self.sku_id}, serial={self.serial}, status={self.status})>"


class Inspection(Base):
    """Inspection record model."""

    __tablename__ = "inspections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id = Column(
        UUID(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inspector_id = Column(UUID(as_uuid=True), nullable=True)  # FK added in Phase 5
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    battery_health_pct = Column(
        String(10), nullable=False
    )  # Stored as string to preserve precision
    battery_cycles = Column(String(20), nullable=True)
    cosmetic_grade: Mapped[str] = mapped_column(String(20), nullable=False)
    functional_tests_json = Column(JSON, nullable=False, default=dict)
    activation_lock = Column(
        String(20), nullable=False, default="unknown"
    )  # "none", "present", "unknown"
    accessories_json = Column(JSON, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    offline_created = Column(Boolean, nullable=False, default=False)

    # Relationships
    unit = relationship("Unit", back_populates="inspections")
    photos = relationship("Photo", back_populates="inspection", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Inspection(id={self.id}, unit_id={self.unit_id}, grade={self.cosmetic_grade})>"


class Photo(Base):
    """Photo model for unit inspections."""

    __tablename__ = "photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id = Column(
        UUID(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inspection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_path = Column(String(500), nullable=False)
    exif_stripped = Column(String(10), nullable=False, default="true")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    unit = relationship("Unit", back_populates="photos")
    inspection = relationship("Inspection", back_populates="photos")

    def __repr__(self) -> str:
        return f"<Photo(id={self.id}, unit_id={self.unit_id}, path={self.storage_path})>"
