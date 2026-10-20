"""
Pydantic schemas for the feedback module (Phase 1).
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from secondroute.feedback.models import AuditAction


class AuditLogRead(BaseModel):
    """Schema for reading an audit log entry."""

    id: UUID
    org_id: Optional[UUID] = None
    actor: str
    action: AuditAction
    entity: str
    entity_id: str
    payload_json: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OverrideCreate(BaseModel):
    """Request body for overriding a decision.

    The reason is mandatory: an override without a reason is not actionable
    and cannot feed the regret or calibration analysis.
    """

    chosen_channel: str = Field(
        ...,
        min_length=1,
        max_length=40,
        description="The channel the operator actually used.",
    )
    reason_text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Why the recommendation was overridden. Required.",
    )

    @field_validator("reason_text")
    @classmethod
    def validate_reason_not_blank(cls, v: str) -> str:
        """Reject a reason that is only whitespace."""
        if not v.strip():
            raise ValueError("A reason is required to override a decision")
        return v.strip()

    @field_validator("chosen_channel")
    @classmethod
    def validate_channel_not_blank(cls, v: str) -> str:
        """Reject a blank channel."""
        if not v.strip():
            raise ValueError("A channel is required to override a decision")
        return v.strip()


class OverrideRead(BaseModel):
    """Schema for reading an override."""

    id: UUID
    decision_id: UUID
    user_id: Optional[UUID] = None
    chosen_channel: str
    reason_text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OverrideListRead(BaseModel):
    """A page of overrides."""

    items: list[OverrideRead] = Field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0


class OutcomeCreate(BaseModel):
    """Request body for recording the outcome of a dispositioned unit.

    The realized numbers are what actually happened, not what the engine
    predicted. They feed the regret and calibration analysis.
    """

    channel_taken: str = Field(
        ...,
        min_length=1,
        max_length=40,
        description="The channel the unit actually went to.",
    )
    sale_price: float = Field(..., ge=0, description="Realized sale price.")
    fees_actual: float = Field(..., ge=0, description="Realized platform fees.")
    repair_cost_actual: float = Field(..., ge=0, description="Realized repair cost.")
    logistics_actual: float = Field(..., ge=0, description="Realized logistics cost.")
    days_to_disposition: int = Field(..., ge=0, description="Days from intake to disposition.")
    final_status: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Final status of the unit (e.g. 'sold', 'recycled').",
    )
    decision_id: Optional[UUID] = Field(
        default=None,
        description=(
            "The decision this outcome belongs to. Defaults to the unit's most "
            "recent decision. A unit with no decision cannot have an outcome."
        ),
    )

    @field_validator("channel_taken")
    @classmethod
    def validate_channel_not_blank(cls, v: str) -> str:
        """Reject a blank channel."""
        if not v.strip():
            raise ValueError("A channel is required to record an outcome")
        return v.strip()

    @field_validator("final_status")
    @classmethod
    def validate_status_not_blank(cls, v: str) -> str:
        """Reject a blank final status."""
        if not v.strip():
            raise ValueError("A final status is required to record an outcome")
        return v.strip()


class OutcomeRead(BaseModel):
    """Schema for reading an outcome."""

    id: UUID
    unit_id: UUID
    decision_id: UUID
    channel_taken: str
    sale_price: float
    fees_actual: float
    repair_cost_actual: float
    logistics_actual: float
    days_to_disposition: int
    final_status: str
    recorded_at: datetime
    net: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class OutcomeListRead(BaseModel):
    """A page of outcomes."""

    items: list[OutcomeRead] = Field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0
