"""
Regret measurement model (Phase 4 - F4.5).

Regret is the value left on the table by a disposition choice: the best
realized net among the channels that were tried, minus the realized net of
the channel that was actually chosen.

Every row carries a ``regret_kind`` so an observed regret is never confused
with an estimated one, and no report may add the two together without
saying that it did.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from secondroute.core.db import Base


class RegretKind:
    """How a regret figure was arrived at.

    ``OBSERVED`` means every channel was actually tried, so the best
    realized net is a fact. ``ESTIMATED`` means only one channel was tried
    and the best alternative comes from the model, so the figure is an
    estimate and is labelled as one.
    """

    OBSERVED = "observed"
    ESTIMATED = "estimated"

    ALL = (OBSERVED, ESTIMATED)


class RegretMeasurement(Base):
    """One regret measurement, appended once and never changed.

    Attributes:
        org_id: The organisation the measurement belongs to.
        unit_id: The unit the measurement is about.
        outcome_id: The outcome of the chosen channel.
        decision_id: The decision that produced the choice.
        channel_taken: The channel that was actually chosen.
        best_channel: The channel that turned out (or was expected) to be
            the best.
        realized_net: The realized net of the chosen channel.
        best_net: The best realized net, or the model's predicted net when
            the regret is estimated.
        regret: ``best_net - realized_net``, never negative.
        regret_kind: ``observed`` or ``estimated``.
        method: How the figure was produced.
        is_synthetic: True when the underlying prices were synthetic.
        created_at: When the measurement was recorded.
    """

    __tablename__ = "regret_measurements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    outcome_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("outcomes.id", ondelete="CASCADE"),
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
    best_channel: Mapped[str] = mapped_column(String(40), nullable=False)
    realized_net: Mapped[float] = mapped_column(Float, nullable=False)
    best_net: Mapped[float] = mapped_column(Float, nullable=False)
    regret: Mapped[float] = mapped_column(Float, nullable=False)
    regret_kind: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(60), nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    __table_args__ = (
        Index("ix_regret_measurements_unit_kind", "unit_id", "regret_kind"),
        Index("ix_regret_measurements_org_created", "org_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<RegretMeasurement(id={self.id}, unit_id={self.unit_id}, "
            f"regret={self.regret}, kind={self.regret_kind})>"
        )


class CalibrationVersion(Base):
    """One fitted recalibration version.

    A recalibration is never applied silently: each fit produces its own
    version, the version in force is recorded on every decision, and the
    earlier versions stay in the table.

    Attributes:
        org_id: The organisation the version belongs to.
        version: The name of the version.
        mapping_json: The isotonic mapping, as ``[[predicted, calibrated]]``.
        sample_size: How many observations the version was fitted on.
        ece_before: The expected calibration error before the recalibration.
        ece_after: The expected calibration error after the recalibration.
        bins: How many bins the reliability curve uses.
        is_active: True when this version is the one in force.
        created_at: When the version was fitted.
    """

    __tablename__ = "calibration_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    mapping_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ece_before: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ece_after: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    bins: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    __table_args__ = (Index("ix_calibration_versions_org_created", "org_id", "created_at"),)

    def __repr__(self) -> str:
        return (
            f"<CalibrationVersion(id={self.id}, version={self.version}, active={self.is_active})>"
        )
