"""
Pydantic schemas for the feedback module (Phase 1).
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

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
