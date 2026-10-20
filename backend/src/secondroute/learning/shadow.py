"""
Shadow mode for Phase 6 (F6.2).

A candidate model runs alongside the active one, logs predictions, and does
not affect what users see. Shadow predictions are stored for every decision.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, UTC
from typing import Any, Optional
from uuid import UUID

import structlog
from pydantic import BaseModel, ConfigDict

from secondroute.core.db import Base
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = structlog.get_logger(__name__)


# Shadow prediction storage table
class ShadowPrediction(Base):
    """Stores shadow model predictions for comparison.

    These predictions are logged but never shown to users.
    """

    __tablename__ = "shadow_predictions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_model_version = Column(String(60), nullable=False)
    active_model_version = Column(String(60), nullable=False)
    shadow_recommended_channel = Column(String(40), nullable=True)
    shadow_confidence = Column(Float, nullable=True)
    shadow_candidates_json = Column(Text, nullable=False, default="[]")
    active_recommended_channel = Column(String(40), nullable=True)
    active_confidence = Column(Float, nullable=True)
    channel_match = Column(Boolean, nullable=False, default=False)
    confidence_delta = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now(UTC))

    __table_args__ = (
        Index("ix_shadow_predictions_decision", "decision_id"),
        Index("ix_shadow_predictions_candidate", "candidate_model_version"),
    )

    def __repr__(self) -> str:
        return (
            f"<ShadowPrediction(id={self.id}, decision_id={self.decision_id}, "
            f"candidate={self.candidate_model_version}, channel_match={self.channel_match})>"
        )


@dataclass
class ShadowResult:
    """Result of running a shadow model alongside the active one.

    Attributes:
        shadow_recommended_channel: Channel recommended by the shadow model.
        shadow_confidence: Confidence of the shadow model.
        shadow_candidates: Per-channel evaluations from the shadow model.
        active_recommended_channel: Channel recommended by the active model.
        active_confidence: Confidence of the active model.
        channel_match: Whether both models agree on the channel.
        confidence_delta: Difference in confidence (shadow - active).
    """

    shadow_recommended_channel: str
    shadow_confidence: float
    shadow_candidates: list[dict] = field(default_factory=list)
    active_recommended_channel: str = ""
    active_confidence: float = 0.0
    channel_match: bool = False
    confidence_delta: float = 0.0


class ShadowModeService:
    """Service for running shadow models alongside the active model.

    The candidate model runs in parallel, logs its prediction, but never
    affects what the user sees. This allows safe evaluation of new models
    before promotion.
    """

    def __init__(self, candidate_model_version: str) -> None:
        self.candidate_model_version = candidate_model_version

    async def run_shadow(  # noqa: PLR0913, PLR0917
        self,
        session: AsyncSession,
        decision_id: UUID,
        active_recommended_channel: str,
        active_confidence: float,
        _active_candidates: list[dict],
        active_model_version: str,
        shadow_evaluation: dict,
    ) -> ShadowResult:
        """Run a shadow model and store its prediction.

        Args:
            session: Database session.
            decision_id: ID of the decision being evaluated.
            active_recommended_channel: Channel from the active model.
            active_confidence: Confidence from the active model.
            _active_candidates: Per-channel evaluations from the active model.
            active_model_version: Version of the active model.
            shadow_evaluation: Evaluation result from the shadow model.

        Returns:
            ShadowResult with comparison data.
        """
        shadow_recommended_channel = shadow_evaluation.get("recommended_channel", "SAFE_DEFAULT")
        shadow_confidence = shadow_evaluation.get("confidence", 0.0)
        shadow_candidates = shadow_evaluation.get("candidates", [])

        channel_match = shadow_recommended_channel == active_recommended_channel
        confidence_delta = shadow_confidence - active_confidence

        result = ShadowResult(
            shadow_recommended_channel=shadow_recommended_channel,
            shadow_confidence=shadow_confidence,
            shadow_candidates=shadow_candidates,
            active_recommended_channel=active_recommended_channel,
            active_confidence=active_confidence,
            channel_match=channel_match,
            confidence_delta=confidence_delta,
        )

        # Store the shadow prediction
        prediction = ShadowPrediction(
            decision_id=decision_id,
            candidate_model_version=self.candidate_model_version,
            active_model_version=active_model_version,
            shadow_recommended_channel=shadow_recommended_channel,
            shadow_confidence=shadow_confidence,
            shadow_candidates_json=json.dumps(shadow_candidates),
            active_recommended_channel=active_recommended_channel,
            active_confidence=active_confidence,
            channel_match=channel_match,
            confidence_delta=confidence_delta,
        )
        session.add(prediction)
        await session.flush()

        logger.info(
            "shadow_prediction_stored",
            decision_id=str(decision_id),
            candidate=self.candidate_model_version,
            active_channel=active_recommended_channel,
            shadow_channel=shadow_recommended_channel,
            channel_match=channel_match,
            confidence_delta=confidence_delta,
        )

        return result

    async def get_shadow_predictions(
        self,
        session: AsyncSession,
        decision_id: Optional[UUID] = None,
        candidate_model_version: Optional[str] = None,
        limit: int = 100,
    ) -> list[ShadowPrediction]:
        """Retrieve shadow predictions for analysis.

        Args:
            session: Database session.
            decision_id: Optional filter by decision ID.
            candidate_model_version: Optional filter by candidate version.
            limit: Maximum results.

        Returns:
            List of ShadowPrediction objects.
        """
        query = select(ShadowPrediction).order_by(ShadowPrediction.created_at.desc())

        if decision_id:
            query = query.where(ShadowPrediction.decision_id == decision_id)
        if candidate_model_version:
            query = query.where(ShadowPrediction.candidate_model_version == candidate_model_version)

        query = query.limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_agreement_rate(
        self,
        session: AsyncSession,
        candidate_model_version: Optional[str] = None,
    ) -> dict[str, Any]:
        """Compute agreement rate between shadow and active models.

        Args:
            session: Database session.
            candidate_model_version: Optional filter by candidate version.

        Returns:
            Dictionary with agreement statistics.
        """
        query = select(ShadowPrediction)
        if candidate_model_version:
            query = query.where(ShadowPrediction.candidate_model_version == candidate_model_version)

        result = await session.execute(query)
        predictions = result.scalars().all()

        if not predictions:
            return {
                "total": 0,
                "agreement_rate": 0.0,
                "channel_match_rate": 0.0,
                "avg_confidence_delta": 0.0,
            }

        total = len(predictions)
        matches = sum(1 for p in predictions if p.channel_match)
        avg_delta = sum(p.confidence_delta or 0.0 for p in predictions) / total

        return {
            "total": total,
            "agreement_rate": matches / total,
            "channel_match_rate": matches / total,
            "avg_confidence_delta": avg_delta,
        }
