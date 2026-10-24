"""
Pydantic schemas for the identity module (Phase 1).
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SKUBase(BaseModel):
    """Base SKU fields."""

    family: str = Field(
        ..., min_length=1, max_length=100, description="Product family (e.g., MacBook Pro)"
    )
    model_name: str = Field(
        ..., min_length=1, max_length=200, description="Model name (e.g., M3 Pro)"
    )
    year: str = Field(..., min_length=1, max_length=10, description="Model year (e.g., '2023')")
    # The two figures are left empty for a product that has not got them: a
    # hair dryer has no storage and a washing machine has no memory, and the
    # catalogue says so by leaving the column blank. The column itself is not
    # null, so the blank is the value rather than an absence of one -- and a
    # schema that insisted on a figure here would refuse to describe its own
    # catalogue, which is how a list of units ends up failing to render at all.
    storage_gb: str = Field(
        ..., max_length=50, description="Storage capacity (e.g., '512', '1TB'), or empty"
    )
    ram_gb: str = Field(..., max_length=50, description="RAM capacity (e.g., '8', '16'), or empty")
    color: str = Field(
        ..., min_length=1, max_length=50, description="Color (e.g., 'Space Gray', 'Silver')"
    )
    region: str = Field(
        ..., min_length=1, max_length=10, description="Region code (e.g., 'US', 'EU')"
    )
    specs_json: dict = Field(default_factory=dict, description="Additional specifications as JSON")
    source: str = Field(
        ..., min_length=1, max_length=200, description="Data source (e.g., 'manufacturer_specs')"
    )
    as_of: date = Field(..., description="Date when this data was current")


class SKUCreate(SKUBase):
    """Schema for creating a SKU."""

    pass


class SKURead(SKUBase):
    """Schema for reading a SKU."""

    id: UUID

    model_config = ConfigDict(from_attributes=True)


class SerialPrefixBase(BaseModel):
    """Base serial prefix fields."""

    prefix: str = Field(..., min_length=1, max_length=50, description="Serial number prefix")
    source: str = Field(..., min_length=1, max_length=200, description="Data source")
    as_of: date = Field(..., description="Date when this data was current")


class SerialPrefixCreate(SerialPrefixBase):
    """Schema for creating a serial prefix."""

    sku_id: UUID = Field(..., description="SKU ID this prefix maps to")


class SerialPrefixRead(SerialPrefixBase):
    """Schema for reading a serial prefix."""

    id: UUID
    sku_id: UUID

    model_config = ConfigDict(from_attributes=True)


class SKULookupResponse(BaseModel):
    """Response for SKU lookup by serial prefix."""

    sku: SKURead
    matched_prefix: str


class SKULookupError(BaseModel):
    """Error response for SKU lookup."""

    error: str = "manual_selection_required"
    message: str
    serial: str
