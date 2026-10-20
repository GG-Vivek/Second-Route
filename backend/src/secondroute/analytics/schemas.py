"""
Pydantic schemas for the analytics module (Phase 4 - F4.3).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChannelPredictionRead(BaseModel):
    """The predicted net range for one channel."""

    channel: str
    p10: float
    p50: float
    p90: float
    mean: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class PredictedVsRealizedRead(BaseModel):
    """One prediction compared against what actually happened."""

    unit_id: UUID
    decision_id: UUID
    outcome_id: UUID
    channel: str
    recommended_channel: str
    used_recommended: bool
    predicted: ChannelPredictionRead
    realized_net: float
    residual: float
    absolute_residual: float
    in_range: bool
    within_p10_p90: bool
    below_p10: bool
    above_p90: bool
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PredictedVsRealizedListRead(BaseModel):
    """A page of predicted vs realized comparisons."""

    items: list[PredictedVsRealizedRead] = Field(default_factory=list)
    total: int = 0
    summary: dict[str, Any] = Field(default_factory=dict)


class SurvivalCurveRead(BaseModel):
    """A Kaplan-Meier survival curve."""

    times: list[int] = Field(default_factory=list)
    survival: list[float] = Field(default_factory=list)
    at_risk: list[int] = Field(default_factory=list)
    events: list[int] = Field(default_factory=list)
    censored: list[int] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TimeToSellCellRead(BaseModel):
    """The time-to-sell estimate for one channel and grade."""

    channel: str
    grade: str
    sample_size: int
    used_fallback: bool
    median_days: Optional[int] = None
    p25_days: Optional[int] = None
    p75_days: Optional[int] = None
    expected_days: Optional[float] = None
    source: str
    as_of: Optional[date] = None
    curve: SurvivalCurveRead = Field(default_factory=SurvivalCurveRead)

    model_config = ConfigDict(from_attributes=True)


class TimeToSellRead(BaseModel):
    """The time-to-sell curves for every channel and grade."""

    min_sample: int
    items: list[TimeToSellCellRead] = Field(default_factory=list)
    total: int = 0
    fallback_count: int = 0
    prior_source: str = "cost_tables:expected_days_to_sell"


class RegretEstimateRead(BaseModel):
    """The regret of one disposition, computed live."""

    unit_id: UUID
    outcome_id: UUID
    decision_id: UUID
    channel_taken: str
    best_channel: str
    realized_net: float
    best_net: float
    regret: float
    regret_kind: str
    method: str

    model_config = ConfigDict(from_attributes=True)


class RegretMeasurementRead(RegretEstimateRead):
    """One stored regret measurement."""

    id: UUID
    is_synthetic: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RegretReportRead(BaseModel):
    """The regret report.

    The observed and the estimated figures are kept apart, and the combined
    total always says what it is made of.
    """

    items: list[RegretEstimateRead] = Field(default_factory=list)
    total: int = 0
    summary: dict[str, Any] = Field(default_factory=dict)


class StoredRegretRead(BaseModel):
    """The regret measurements stored for one unit."""

    items: list[RegretMeasurementRead] = Field(default_factory=list)
    total: int = 0
    summary: dict[str, Any] = Field(default_factory=dict)


class CalibrationBinRead(BaseModel):
    """One bin of the reliability curve."""

    lower: float
    upper: float
    count: int
    mean_predicted: float
    observed_frequency: float
    gap: float

    model_config = ConfigDict(from_attributes=True)


class CalibrationReportRead(BaseModel):
    """The calibration of the engine."""

    bins: list[CalibrationBinRead] = Field(default_factory=list)
    ece: float = 0.0
    sample_size: int = 0
    bin_count: int = 10
    active_version: Optional[str] = None


class CalibrationVersionRead(BaseModel):
    """One fitted recalibration version."""

    id: UUID
    version: str
    sample_size: int
    ece_before: float
    ece_after: float
    bins: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NorthStarSectionRead(BaseModel):
    """The north star of one kind of data."""

    returns_count: int = 0
    net_recovered_total: float = 0.0
    baseline_total: float = 0.0
    net_recovered_per_return: float = 0.0
    baseline_per_return: float = 0.0
    above_baseline_per_return: float = 0.0
    observed_baseline_count: int = 0
    estimated_baseline_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class NorthStarRead(BaseModel):
    """The north star, with the synthetic and the real data apart."""

    synthetic: NorthStarSectionRead = Field(default_factory=NorthStarSectionRead)
    real: NorthStarSectionRead = Field(default_factory=NorthStarSectionRead)
    baseline_channel: str = "RECYCLE"


class RegretBucketRead(BaseModel):
    """The regret of one period."""

    period: str
    count: int = 0
    mean_regret: float = 0.0
    observed_count: int = 0
    estimated_count: int = 0
    observed_mean_regret: float = 0.0
    estimated_mean_regret: float = 0.0


class RegretOverTimeRead(BaseModel):
    """The regret over time, with the synthetic and the real data apart."""

    bucket: str = "month"
    synthetic: list[RegretBucketRead] = Field(default_factory=list)
    real: list[RegretBucketRead] = Field(default_factory=list)


class ReasonCountRead(BaseModel):
    """How often one override reason was given."""

    reason: str
    count: int = 0
    share: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class OverrideRateSectionRead(BaseModel):
    """The override rate of one kind of data."""

    decisions_count: int = 0
    overrides_count: int = 0
    override_rate: float = 0.0
    by_reason: list[ReasonCountRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class OverrideRateRead(BaseModel):
    """The override rate, with the synthetic and the real data apart."""

    synthetic: OverrideRateSectionRead = Field(default_factory=OverrideRateSectionRead)
    real: OverrideRateSectionRead = Field(default_factory=OverrideRateSectionRead)
