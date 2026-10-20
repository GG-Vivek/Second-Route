"""
The explanation model (Phase 5 - F5.7).

An explanation is written once and read many times. The model is slow -
a 14B model on a CPU takes seconds - so the explanation is stored rather
than regenerated every time somebody opens the decision.

The rows are append-only in the sense that a new explanation is a new row:
a decision that was explained again, with a different model or a different
template, keeps the old row.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from secondroute.core.db import Base


class DecisionExplanation(Base):
    """One explanation of a decision.

    Attributes:
        decision_id: The decision that was explained.
        text: The explanation to show.
        source: ``model`` or ``template``.
        reason: Why it is what it is: it passed the validator, it was
            refused for an unseen number, the model was unreachable.
        model: The model that wrote it, when a model did.
        unseen_numbers: The numbers that caused a refusal, as a JSON array.
        is_synthetic: True when the decision was made with synthetic prices.
        created_at: When the explanation was written.
    """

    __tablename__ = "decision_explanations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str | None] = mapped_column(String(60), nullable=True)
    unseen_numbers: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    __table_args__ = (
        Index("ix_decision_explanations_decision_created", "decision_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<DecisionExplanation(id={self.id}, decision_id={self.decision_id}, "
            f"source={self.source})>"
        )
