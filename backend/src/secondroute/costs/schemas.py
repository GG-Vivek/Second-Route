"""
Pydantic schemas for the cost administration API (Phase 2 - F2.4).
"""

from __future__ import annotations

import math
from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CostBase(BaseModel):
    """Fields shared by cost write schemas."""

    kind: str = Field(..., min_length=1, max_length=40, description="Cost kind")
    key: str = Field(..., min_length=1, max_length=120, description="Channel or channel:grade")
    value: float = Field(..., description="Numeric value of the cost")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    source: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Where the value came from. Required - never empty.",
    )
    as_of: date = Field(..., description="Date the value was current")

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Reject a blank or whitespace-only source."""
        if not v.strip():
            raise ValueError("source must not be empty")
        return v


class CostCreate(CostBase):
    """Schema for creating a cost row."""

    org_id: Optional[UUID] = None

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: float) -> float:
        """Reject non-finite values."""
        if not math.isfinite(v):
            raise ValueError("value must be a finite number")
        return v


class CostUpdate(BaseModel):
    """Schema for updating a cost row.

    Every field is optional, but at least one must be supplied. The
    ``source`` field can never be blank - a cost without a provenance is
    rejected.
    """

    value: Optional[float] = None
    source: Optional[str] = Field(default=None, max_length=200)
    as_of: Optional[date] = None
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: Optional[str]) -> Optional[str]:
        """Reject a blank source."""
        if v is not None and not v.strip():
            raise ValueError("source must not be empty")
        return v

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: Optional[float]) -> Optional[float]:
        """Reject non-finite values."""
        if v is None:
            return v
        if not math.isfinite(v):
            raise ValueError("value must be a finite number")
        return v


class CostRead(CostBase):
    """Schema for reading a cost row."""

    id: UUID
    org_id: Optional[UUID] = None
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class CostListRead(BaseModel):
    """A list of cost rows."""

    items: list[CostRead]
    total: int
