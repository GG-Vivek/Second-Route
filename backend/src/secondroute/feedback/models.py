"""
Audit log models for Phase 1.

Models for immutable audit logging of all mutations.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from secondroute.core.db import Base


class AuditAction(enum.StrEnum):
    """Audit action types."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class AuditLog(Base):
    """Audit log model - append only, never updated or deleted."""

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # "anonymous" until Phase 5 auth
    action: Mapped[AuditAction] = mapped_column(
        String(20), nullable=False, index=True
    )  # "create" | "update" | "delete"
    entity: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # e.g., "units", "inspections"
    entity_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # UUID as string
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)  # Full payload before/after
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_audit_log_entity_entity_id", "entity", "entity_id"),
        Index("ix_audit_log_actor_created", "actor", "created_at"),
        Index("ix_audit_log_org_created", "org_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, entity={self.entity}, "
            f"entity_id={self.entity_id}, action={self.action})>"
        )
