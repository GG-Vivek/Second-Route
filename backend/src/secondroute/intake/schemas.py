"""
Pydantic schemas for the intake module (Phase 1).
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from secondroute.intake.models import ReturnReasonCode, OrderChannel, UnitStatus


class UnitBase(BaseModel):
    """Base unit fields."""

    sku_id: UUID = Field(..., description="SKU ID")
    serial: Optional[str] = Field(None, max_length=100, description="Serial number (optional)")
    return_reason_code: ReturnReasonCode = Field(..., description="Reason for return")
    order_channel: OrderChannel = Field(..., description="Original sales channel")


class UnitCreate(UnitBase):
    """Schema for creating a unit."""

    pass


class UnitRead(UnitBase):
    """Schema for reading a unit."""

    id: UUID
    org_id: Optional[UUID] = None
    received_at: datetime
    status: UnitStatus

    model_config = ConfigDict(from_attributes=True)


class UnitStatusUpdate(BaseModel):
    """Schema for updating unit status."""

    status: UnitStatus = Field(..., description="New status")


class InspectionBase(BaseModel):
    """Base inspection fields."""

    battery_health_pct: str = Field(
        ..., pattern=r"^\d+(\.\d+)?$", description="Battery health percentage as string"
    )
    battery_cycles: Optional[str] = Field(None, description="Battery cycle count as string")
    cosmetic_grade: str = Field(
        ..., min_length=1, max_length=20, description="Cosmetic grade (A/B/C/D)"
    )
    functional_tests_json: dict[str, Any] = Field(
        default_factory=dict, description="Functional test results"
    )
    activation_lock: str = Field(
        default="unknown", pattern=r"^(none|present|unknown)$", description="Activation lock status"
    )
    accessories_json: dict[str, Any] = Field(
        default_factory=dict, description="Accessories checklist"
    )
    notes: Optional[str] = Field(None, description="Inspector notes")
    offline_created: bool = Field(
        default=False, description="Whether inspection was created offline"
    )

    @field_validator("battery_health_pct")
    @classmethod
    def validate_battery_health(cls, v: str) -> str:
        """Validate battery health is between 0 and 100."""
        try:
            value = float(v)
            if not 0 <= value <= 100:
                raise ValueError("Battery health must be between 0 and 100") from None
        except ValueError as e:
            if "Battery health" in str(e):
                raise
            raise ValueError("Battery health must be a valid number") from None
        return v


class InspectionCreate(InspectionBase):
    """Schema for creating an inspection."""

    pass


class InspectionRead(InspectionBase):
    """Schema for reading an inspection."""

    id: UUID
    unit_id: UUID
    inspector_id: Optional[UUID] = None
    created_at: datetime
    offline_created: bool

    @field_validator("functional_tests_json", "accessories_json", mode="before")
    @classmethod
    def parse_json_fields(cls, v: Any) -> Any:
        """Parse JSON string fields to dict if needed."""
        import json

        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v

    model_config = ConfigDict(from_attributes=True)


class PhotoBase(BaseModel):
    """Base photo fields."""

    storage_path: str = Field(
        ..., min_length=1, max_length=500, description="Storage path for the photo"
    )
    exif_stripped: bool = Field(default=True, description="Whether EXIF data was stripped")


class PhotoCreate(PhotoBase):
    """Schema for creating a photo record."""

    inspection_id: UUID = Field(..., description="Inspection ID this photo belongs to")


class PhotoRead(PhotoBase):
    """Schema for reading a photo."""

    id: UUID
    unit_id: UUID
    inspection_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnitDetailRead(UnitRead):
    """Schema for unit detail with inspections and photos."""

    inspections: list[InspectionRead] = []
    photos: list[PhotoRead] = []
