"""
Pydantic schemas for the analytics module (Phase 4 - F4.3).
"""

from __future__ import annotations

from datetime import datetime
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
