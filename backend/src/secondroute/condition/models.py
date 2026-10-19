"""
Condition estimate models (Phase 2 - F2.3).

Every grade distribution the engine computes is stored so a decision can be
replayed and so the outcome data can be joined against the condition that
produced it.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from secondroute.core.db import Base

# Registers the units table so the foreign key below resolves.
from secondroute.intake.models import Unit  # noqa: F401


class ConditionEstimate(Base):
    """One stored grade distribution for a unit.

    Attributes:
        unit_id: Unit the estimate belongs to.
        grade_dist_json: JSON object mapping grade to probability.
        model_version: Version of the rules that produced the estimate.
        score: The condition score behind the distribution.
    """

    __tablename__ = "condition_estimates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    grade_dist_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    model_version: Mapped[str] = mapped_column(String(60), nullable=False, default="grade-rules-v1")
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    # Relationships
    unit = relationship("Unit", backref="condition_estimates")

    __table_args__ = (Index("ix_condition_estimates_unit_created", "unit_id", "created_at"),)

    def __repr__(self) -> str:
        return f"<ConditionEstimate(unit_id={self.unit_id}, model_version={self.model_version})>"
