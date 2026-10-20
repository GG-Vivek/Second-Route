"""
Decision persistence (Phase 2 - F2.9).

A decision is append-only. It stores everything needed to explain the call:
the candidate evaluations, the reasons, the flip conditions, the data
freshness, the exact input snapshot and a hash of that snapshot.

``input_snapshot_hash`` is the reproducibility key: the same snapshot always
produces the same hash and the same decision.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from secondroute.core.db import Base

# Registers the organizations and units tables so the foreign keys below resolve.
from secondroute.identity.organizations import Organization  # noqa: F401
from secondroute.intake.models import Unit  # noqa: F401


class Decision(Base):
    """One stored decision.

    Attributes:
        unit_id: Unit the decision was made for.
        model_version: Version of the decision engine that produced it.
        risk_profile: Risk profile used for ranking.
        recommended_channel: The recommended channel, or ``SAFE_DEFAULT``.
        confidence: Confidence of the recommendation, ``0``-``1``.
        fallback_used: True when the confidence gate produced ``SAFE_DEFAULT``.
        candidates_json: Per-channel evaluations.
        reasons_json: Why the channel was recommended.
        flip_conditions_json: What would change the recommendation.
        data_freshness_json: Age and provenance of every data source used.
        input_snapshot_hash: SHA-256 of the canonical input snapshot.
        input_snapshot_json: The exact inputs the decision was made from.
        exploration_propensity: Propensity of the recommended choice (Phase 6).
        calibration_version: The recalibration version in force when the
            decision was made (Phase 4 - F4.6).
    """

    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    model_version: Mapped[str] = mapped_column(String(60), nullable=False, default="decision-v1")
    risk_profile: Mapped[str] = mapped_column(String(30), nullable=False, default="balanced")
    recommended_channel: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fallback_channel: Mapped[str | None] = mapped_column(String(40), nullable=True)
    candidates_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    reasons_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    flip_conditions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    data_freshness_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    action_steps_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    input_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    input_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    exploration_propensity: Mapped[float | None] = mapped_column(Float, nullable=True)
    calibration_version: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)

    # Relationships
    unit = relationship("Unit", backref="decisions")

    __table_args__ = (
        Index("ix_decisions_unit_created", "unit_id", "created_at"),
        Index("ix_decisions_recommended", "recommended_channel"),
    )

    def __repr__(self) -> str:
        return (
            f"<Decision(id={self.id}, unit_id={self.unit_id}, "
            f"channel={self.recommended_channel}, confidence={self.confidence})>"
        )

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    @property
    def candidates(self) -> list[dict[str, Any]]:
        """Return the stored candidate evaluations."""
        return _load_json(self.candidates_json, default=[])

    @property
    def reasons(self) -> list[dict[str, Any]]:
        """Return the stored reasons."""
        return _load_json(self.reasons_json, default=[])

    @property
    def flip_conditions(self) -> list[dict[str, Any]]:
        """Return the stored flip conditions."""
        return _load_json(self.flip_conditions_json, default=[])

    @property
    def data_freshness(self) -> dict[str, Any]:
        """Return the stored data freshness information."""
        return _load_json(self.data_freshness_json, default={})

    @property
    def action_steps(self) -> list[dict[str, Any]]:
        """Return the stored action steps."""
        return _load_json(self.action_steps_json, default=[])

    @property
    def input_snapshot(self) -> dict[str, Any]:
        """Return the stored input snapshot."""
        return _load_json(self.input_snapshot_json, default={})


def _load_json[T](raw: str, default: T) -> T:
    """Parse a JSON column, falling back to ``default``."""
    if not raw:
        return default
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return default
    if isinstance(parsed, type(default)):
        return parsed  # type: ignore[return-value]
    return default


def canonical_json(payload: Any) -> str:
    """Return the canonical JSON representation used for hashing.

    Keys are sorted and separators are compact, so the same logical payload
    always produces the same string.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def hash_snapshot(snapshot: Any) -> str:
    """Return the SHA-256 hash of an input snapshot."""
    return hashlib.sha256(canonical_json(snapshot).encode("utf-8")).hexdigest()
