"""
Pydantic schemas for the decision API (Phase 2 - F2.9).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from secondroute.decision.confidence import SAFE_DEFAULT


class CostBreakdownRead(BaseModel):
    """Expected cost components for one channel."""

    sale_price: float
    fees: float
    logistics: float
    handling: float
    repair: float
    holding: float
    total_cost: float
    net: float


class CandidateRead(BaseModel):
    """One evaluated channel on the decision card."""

    channel: str
    eligible: bool
    exclusion_reason: Optional[str] = None
    mean: float
    stddev: float
    p10: float
    p50: float
    p90: float
    probability_best: float = 0.0
    certainty_equivalent: float = 0.0
    grade_probabilities: dict[str, float] = Field(default_factory=dict)
    price_sources: dict[str, str] = Field(default_factory=dict)
    price_as_of: dict[str, str] = Field(default_factory=dict)
    breakdown: CostBreakdownRead


class ReasonRead(BaseModel):
    """One reason why a channel was recommended."""

    code: str
    label: str
    contribution: float
    favours_recommended: bool
    text: str


class FlipConditionRead(BaseModel):
    """One input whose change would flip the recommendation."""

    input_name: str
    input_kind: str
    current_value: float | str
    threshold_value: float | str
    new_channel: str
    direction: str
    description: str


class ActionStepRead(BaseModel):
    """One action step for the operator."""

    order: int
    title: str
    detail: str
    reference: Optional[str] = None


class DataFreshnessRead(BaseModel):
    """Freshness and provenance of the data behind a decision."""

    price_sources: dict[str, str] = Field(default_factory=dict)
    price_as_of: dict[str, str] = Field(default_factory=dict)
    cost_sources: dict[str, str] = Field(default_factory=dict)
    cost_as_of: dict[str, str] = Field(default_factory=dict)
    is_synthetic: bool = True
    warnings: list[str] = Field(default_factory=list)


class DecisionRead(BaseModel):
    """A stored decision."""

    id: UUID
    unit_id: UUID
    created_at: datetime
    model_version: str
    risk_profile: str
    recommended_channel: str
    confidence: float
    fallback_used: bool
    fallback_channel: Optional[str] = None
    candidates: list[CandidateRead] = Field(default_factory=list)
    reasons: list[ReasonRead] = Field(default_factory=list)
    flip_conditions: list[FlipConditionRead] = Field(default_factory=list)
    action_steps: list[ActionStepRead] = Field(default_factory=list)
    data_freshness: DataFreshnessRead = Field(default_factory=DataFreshnessRead)
    input_snapshot_hash: str
    is_prototype: bool = True
    prototype_badge: str = "Prototype - synthetic prices"

    model_config = ConfigDict(from_attributes=True)


class ExplanationRead(BaseModel):
    """One explanation of a decision.

    The source says who wrote it: ``model`` or ``template``. The reason
    says why: it passed the validator, it was refused for a number the
    decision does not contain, the model could not be reached.
    """

    id: UUID
    decision_id: UUID
    text: str
    source: str
    reason: str
    model: Optional[str] = None
    unseen_numbers: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DecisionCreate(BaseModel):
    """Request body for running a decision."""

    risk_profile: str = Field(
        default="balanced",
        description="Risk profile used to rank the channels.",
    )
    force: bool = Field(
        default=False,
        description="Recompute even when a recent decision already exists.",
    )
    as_of: Optional[datetime] = Field(
        default=None,
        description=(
            "Timestamp used to look up prices. Defaults to now. Pass the same "
            "value twice to get byte-identical output."
        ),
    )


class DecisionSummaryRead(BaseModel):
    """Lightweight decision summary used in list views."""

    id: UUID
    unit_id: UUID
    created_at: datetime
    recommended_channel: str
    confidence: float
    fallback_used: bool
    risk_profile: str

    model_config = ConfigDict(from_attributes=True)


class DecisionListRead(BaseModel):
    """A page of decisions."""

    items: list[DecisionSummaryRead]
    total: int
    limit: int
    offset: int


class ReproducibilityRead(BaseModel):
    """Result of replaying a stored decision from its snapshot."""

    decision_id: UUID
    input_snapshot_hash: str
    replayed_hash: str
    matches: bool
    recommended_channel: str
    confidence: float
    details: dict[str, Any] = Field(default_factory=dict)


class DensityBinRead(BaseModel):
    """One bar of the density histogram."""

    x: float = Field(description="Middle of the bar, in the units of the net value.")
    density: float = Field(ge=0.0, description="Probability density at that point.")


class ChannelDistributionRead(BaseModel):
    """The distribution of the net value for one channel."""

    channel: str
    eligible: bool
    exclusion_reason: Optional[str] = None
    mean: float
    stddev: float
    p10: float
    p50: float
    p90: float
    probability_best: float
    bins: list[DensityBinRead] = Field(default_factory=list)


class DistributionAxisRead(BaseModel):
    """The shared axis every channel is drawn against."""

    min: float
    max: float


class DistributionRead(BaseModel):
    """The distribution of the net value across every channel.

    This is the engine's own Monte Carlo output, replayed from the stored
    snapshot. It is a replay and not a copy: if the price data has moved
    since the decision was made, the replay reflects that, which is why
    the response carries the snapshot hash and whether the replay still
    agrees with the stored decision.
    """

    decision_id: UUID
    input_snapshot_hash: str
    model_version: str
    risk_profile: str
    recommended_channel: str
    confidence: float
    matches_stored_decision: bool = Field(
        description=(
            "Whether the replay still recommends the same channel with the "
            "same confidence as the stored decision."
        )
    )
    bin_count: int
    axis: DistributionAxisRead
    channels: list[ChannelDistributionRead] = Field(default_factory=list)


SAFE_DEFAULT_CHANNEL = SAFE_DEFAULT
