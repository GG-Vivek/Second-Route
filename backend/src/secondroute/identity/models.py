"""
SKU catalog models for Phase 1.

Models for SKU catalog and serial prefix lookup.
"""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    Date,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from secondroute.core.db import Base


class SKU(Base):
    """SKU catalog model.

    The columns are declared with ``Mapped`` so that the attribute types
    are known: with the older ``Column`` style, a type checker sees
    ``Column[str]`` where the attribute is really a ``str``.
    """

    __tablename__ = "skus"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    year: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g., "2023", "2024"
    storage_gb: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "512", "1TB"
    ram_gb: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "8", "16"
    color: Mapped[str] = mapped_column(String(50), nullable=False)
    region: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g., "US", "EU", "JP"
    specs_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    as_of: Mapped[date] = mapped_column(Date, nullable=False)

    # Relationships
    serial_prefixes = relationship(
        "SerialPrefix", back_populates="sku", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "family",
            "model_name",
            "year",
            "storage_gb",
            "ram_gb",
            "color",
            "region",
            name="uq_sku_variant",
        ),
        Index("ix_sku_family_model", "family", "model_name"),
    )

    def __repr__(self) -> str:
        return f"<SKU(family={self.family}, model={self.model_name}, year={self.year}, storage={self.storage_gb}, ram={self.ram_gb}, color={self.color}, region={self.region})>"


class SerialPrefix(Base):
    """Serial number prefix to SKU mapping."""

    __tablename__ = "serial_prefixes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prefix = Column(String(50), nullable=False, unique=True, index=True)
    sku_id = Column(UUID(as_uuid=True), ForeignKey("skus.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(200), nullable=False)
    as_of = Column(Date, nullable=False)

    # Relationships
    sku = relationship("SKU", back_populates="serial_prefixes")

    def __repr__(self) -> str:
        return f"<SerialPrefix(prefix={self.prefix}, sku_id={self.sku_id})>"
