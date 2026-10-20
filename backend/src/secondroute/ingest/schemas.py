"""
Schemas for the partner sales import (Phase 3 - F3.2).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ColumnMapping(BaseModel):
    """Maps our canonical fields onto the columns of a partner CSV.

    Attributes:
        sku: The column holding the SKU (an id, or a family/model key).
        grade: The column holding the condition grade.
        channel: The column holding the disposition channel.
        price: The column holding the sale price.
        sold_at: The column holding the sale date.
        quantity: The column holding the quantity sold.
    """

    sku: str = Field(..., min_length=1, description="Column with the SKU identifier")
    grade: str = Field(..., min_length=1, description="Column with the condition grade")
    channel: str = Field(..., min_length=1, description="Column with the channel")
    price: str = Field(..., min_length=1, description="Column with the sale price")
    sold_at: str = Field(..., min_length=1, description="Column with the sale date")
    quantity: Optional[str] = Field(
        default=None, description="Column with the quantity sold (optional)"
    )

    def columns(self) -> list[str]:
        """Return every column the mapping refers to."""
        names = [self.sku, self.grade, self.channel, self.price, self.sold_at]
        if self.quantity:
            names.append(self.quantity)
        return names


class RejectedRow(BaseModel):
    """A row that could not be imported, and why.

    Attributes:
        row_number: The 1-based line number in the file (the header is line 1).
        reason: Why the row was rejected.
        detail: The offending value.
        raw: The raw row, so the operator can see what was in the file.
    """

    row_number: int
    reason: str
    detail: Optional[str] = None
    raw: dict[str, Any] = Field(default_factory=dict)


class ImportPreview(BaseModel):
    """What a file looks like before it is imported.

    Attributes:
        columns: The columns found in the file.
        suggested_mapping: The mapping the auto-detection chose.
        row_count: How many data rows the file has.
        filename: The uploaded filename.
        file_hash: The SHA-256 of the uploaded bytes.
    """

    columns: list[str] = Field(default_factory=list)
    suggested_mapping: Optional[ColumnMapping] = None
    row_count: int = 0
    filename: str = ""
    file_hash: str = ""


class ImportResult(BaseModel):
    """The outcome of a sales import.

    Attributes:
        dry_run: Whether the import was a dry run.
        rows_total: How many data rows the file had.
        rows_imported: How many rows were accepted.
        rows_rejected: How many rows were rejected.
        rejected: The rejected rows, with reasons.
        mapping: The mapping that was used.
        file_hash: The SHA-256 of the imported bytes.
        already_imported: True when the file had been imported before.
        import_id: The id of the import record.
        message: A short human-readable summary.
    """

    dry_run: bool
    rows_total: int
    rows_imported: int
    rows_rejected: int
    rejected: list[RejectedRow] = Field(default_factory=list)
    mapping: Optional[ColumnMapping] = None
    file_hash: str
    already_imported: bool = False
    import_id: Optional[UUID] = None
    message: str = ""


class ImportListRead(BaseModel):
    """A page of import records."""

    items: list[ImportRecordRead]
    total: int


class ComponentPriceRead(BaseModel):
    """A component price, with its freshness and provenance."""

    id: str
    component_type: str
    price_per_unit: float
    unit: str
    source: str
    as_of: date
    confidence_weight: float
    is_stale: bool
    age_days: int

    model_config = ConfigDict(from_attributes=True)


class ComponentPriceCreate(BaseModel):
    """A manually entered component price."""

    component_type: str = Field(..., min_length=1, max_length=60)
    price_per_unit: float = Field(..., ge=0)
    unit: str = Field(default="USD", min_length=1, max_length=20)
    source: str = Field(..., min_length=1, max_length=200)
    as_of: date
    confidence_weight: float = Field(default=1.0, ge=0.0, le=1.0)


class ComponentPriceListRead(BaseModel):
    """A list of component prices."""

    items: list[ComponentPriceRead]
    total: int
    stale_count: int


class ComponentPriceImportRead(BaseModel):
    """The outcome of a component price import."""

    rows_imported: int
    errors: list[str] = Field(default_factory=list)


class ImportRecordRead(BaseModel):
    """One past import."""

    id: UUID
    filename: str
    source: str
    file_hash: str
    status: str
    rows_imported: int
    rows_rejected: int
    import_kind: str
    imported_at: datetime

    model_config = ConfigDict(from_attributes=True)
