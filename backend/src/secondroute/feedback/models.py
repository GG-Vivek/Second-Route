"""
Audit log models for Phase 1.

Models for immutable audit logging of all mutations.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
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


class Override(Base):
    """A human override of a decision recommendation (Phase 4 - F4.1).

    Append-only: an override is never updated or deleted through the API.
    The ``user_id`` is null until Phase 5 authentication lands; the actor is
    recorded as "anonymous" in the audit log until then.
    """

    __tablename__ = "overrides"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )  # "anonymous" until Phase 5 auth
    chosen_channel: Mapped[str] = mapped_column(String(40), nullable=False)
    reason_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    decision = relationship("Decision", backref="overrides")

    __table_args__ = (Index("ix_overrides_decision_created", "decision_id", "created_at"),)

    def __repr__(self) -> str:
        return (
            f"<Override(id={self.id}, decision_id={self.decision_id}, "
            f"channel={self.chosen_channel})>"
        )


class Outcome(Base):
    """Actual outcome of a dispositioned unit (Phase 4 - F4.2).

    Append-only: an outcome is never updated or deleted through the API.
    Linked to the decision that was active at disposition time.
    """

    __tablename__ = "outcomes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel_taken: Mapped[str] = mapped_column(String(40), nullable=False)
    sale_price: Mapped[float] = mapped_column(Float, nullable=False)
    fees_actual: Mapped[float] = mapped_column(Float, nullable=False)
    repair_cost_actual: Mapped[float] = mapped_column(Float, nullable=False)
    logistics_actual: Mapped[float] = mapped_column(Float, nullable=False)
    days_to_disposition: Mapped[int] = mapped_column(Integer, nullable=False)
    final_status: Mapped[str] = mapped_column(String(30), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    unit = relationship("Unit", backref="outcomes")
    decision = relationship("Decision", backref="outcomes")

    __table_args__ = (
        Index("ix_outcomes_unit_recorded", "unit_id", "recorded_at"),
        Index("ix_outcomes_decision_recorded", "decision_id", "recorded_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Outcome(id={self.id}, unit_id={self.unit_id}, "
            f"channel={self.channel_taken}, net={self.net:.2f})>"
        )

    @property
    def net(self) -> float:
        """Calculate realized net value."""
        return self.sale_price - self.fees_actual - self.repair_cost_actual - self.logistics_actual
