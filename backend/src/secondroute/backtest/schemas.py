"""
Backtest request and response schemas (Phase 5 - F5.6).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ConfidenceIntervalRead(BaseModel):
    """A point estimate with a bootstrap interval around it."""

    point_estimate: float
    lower: float
    upper: float
    confidence: float
    method: str
    samples: int
    seed: int
    n: int
    excludes_zero: bool


class SkippedDecisionRead(BaseModel):
    """A decision that was left out of the comparison, and why."""

    decision_id: str
    reason: str


class LookAheadFindingRead(BaseModel):
    """One problem found in a decision's provenance."""

    decision_id: str
    kind: str
    field: str
    as_of: Optional[str] = None
    decision_time: str
    detail: str


class LookAheadReportRead(BaseModel):
    """The result of the look-ahead check."""

    has_leak: bool
    is_clean: bool
    finding_count: int
    findings: list[LookAheadFindingRead] = Field(default_factory=list)


class BacktestRequest(BaseModel):
    """Ask for a backtest over a window of past decisions.

    The baseline is named rather than hard-coded, because which channel the
    partner uses today is not yet known (PLAN.md, Appendix F). The report
    always says which baseline it used.

    The organisation is explicit. A backtest is a tenant-scoped read, and
    making the tenant explicit keeps the endpoint compatible with the
    tenant-isolation policies: once authentication lands, the organisation
    comes from the token and is checked against this value.
    """

    org_id: UUID = Field(description="The organisation whose decisions are replayed.")
    name: str = Field(default="Backtest", max_length=120)
    baseline: str = Field(
        default="fixed-channel",
        description="Baseline policy: 'fixed-channel' or 'most-common-channel'.",
    )
    baseline_channel: Optional[str] = Field(
        default=None,
        description="Channel the fixed-channel baseline recommends.",
    )
    window_start: Optional[datetime] = Field(
        default=None, description="Earliest decision time to include."
    )
    window_end: Optional[datetime] = Field(
        default=None, description="Latest decision time to include."
    )
    confidence: float = Field(default=0.95, gt=0.0, lt=1.0)
    samples: int = Field(default=10_000, ge=1, le=200_000)
    seed: int = Field(default=0)


class BacktestReportRead(BaseModel):
    """The outcome of a backtest."""

    baseline_name: str
    baseline_description: str
    baseline_channel: Optional[str] = None
    decision_count: int
    skipped: list[SkippedDecisionRead] = Field(default_factory=list)
    mean_engine_net: Optional[float] = None
    mean_baseline_net: Optional[float] = None
    mean_difference: Optional[float] = None
    interval: Optional[ConfidenceIntervalRead] = None
    confidence: float
    method: str
    win_rate: Optional[float] = None
    channel_breakdown: dict[str, dict[str, int]] = Field(default_factory=dict)
    lookahead: Optional[LookAheadReportRead] = None
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)


class BacktestRunRead(BaseModel):
    """A stored backtest run."""

    id: str
    org_id: Optional[str] = None
    created_at: datetime
    name: str
    baseline_name: str
    baseline_channel: Optional[str] = None
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    decision_count: int
    mean_difference: Optional[float] = None
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    confidence: float
    method: str
    samples: int
    seed: int
    is_synthetic: bool
    report: dict[str, Any] = Field(default_factory=dict)
