"""
Backtest run persistence (Phase 5 - F5.6).

A backtest is a report, and a report is worth keeping: the team needs a
backtest result to show, and a result nobody can reproduce is not evidence.
The run records the baseline it compared against, the seed and sample
count of the interval, and the full report payload.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from secondroute.core.db import Base

# Registers the organizations table so the foreign key below resolves.
from secondroute.identity.organizations import Organization  # noqa: F401


class BacktestRun(Base):
    """One stored backtest.

    Attributes:
        org_id: The organisation whose decisions were replayed.
        name: A human-readable name for the run.
        baseline_name: Identifies the baseline policy that was compared.
        baseline_channel: The channel the baseline chose, when it has one.
        window_start: Earliest decision time in scope.
        window_end: Latest decision time in scope.
        decision_count: How many decisions took part in the comparison.
        mean_difference: The paired mean difference in net, per unit.
        ci_lower: Lower bound of the bootstrap interval.
        ci_upper: Upper bound of the bootstrap interval.
        confidence: The confidence level of the interval.
        method: How the interval was produced.
        samples: Number of bootstrap resamples.
        seed: The RNG seed, so the interval can be reproduced.
        report_json: The full report.
        is_synthetic: True when the replayed decisions used synthetic prices.
    """

    __tablename__ = "backtest_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="Backtest")
    baseline_name: Mapped[str] = mapped_column(String(60), nullable=False)
    baseline_channel: Mapped[str | None] = mapped_column(String(40), nullable=True)
    window_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decision_count: Mapped[int] = mapped_column(nullable=False, default=0)
    mean_difference: Mapped[float | None] = mapped_column(Float, nullable=True)
    ci_lower: Mapped[float | None] = mapped_column(Float, nullable=True)
    ci_upper: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.95)
    method: Mapped[str] = mapped_column(
        String(60), nullable=False, default="paired-bootstrap-percentile"
    )
    samples: Mapped[int] = mapped_column(nullable=False, default=10_000)
    seed: Mapped[int] = mapped_column(nullable=False, default=0)
    report_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    is_synthetic: Mapped[bool] = mapped_column(nullable=False, default=True)

    __table_args__ = (Index("ix_backtest_runs_org_created", "org_id", "created_at"),)

    def __repr__(self) -> str:
        return (
            f"<BacktestRun(id={self.id}, baseline={self.baseline_name}, "
            f"decisions={self.decision_count}, mean_difference={self.mean_difference})>"
        )

    @property
    def report(self) -> dict[str, Any]:
        """Return the stored report."""
        import json

        try:
            parsed = json.loads(self.report_json)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
