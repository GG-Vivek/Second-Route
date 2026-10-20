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
