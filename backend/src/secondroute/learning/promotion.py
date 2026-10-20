"""
Promotion gate for Phase 6 (F6.3).

Promotion requires the shadow model to beat the active model on held-out
outcomes for net MAE and calibration ECE, with a minimum sample size.
Promotion is a recorded, audited action by an admin.
"""

from __future__ import annotations

import logging
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
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = structlog.get_logger(__name__)

# Minimum sample size for promotion
MIN_PROMOTION_SAMPLE = 50


class PromotionRecord(Base):
    """Records a promotion action (audited).

    Attributes:
        candidate_model_version: Version of the candidate model.
        active_model_version: Version of the active model before promotion.
        promoted: Whether the promotion was approved.
        reason: Reason for the decision.
        net_mae_candidate: Net MAE of the candidate model.
        net_mae_active: Net MAE of the active model.
        ece_candidate: Calibration ECE of the candidate model.
        ece_active: Calibration ECE of the active model.
        sample_size: Number of held-out outcomes used.
        promoted_by: Admin who performed the action.
        promoted_at: Timestamp of the promotion.
    """

    __tablename__ = "promotion_records"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_model_version = Column(String(60), nullable=False, index=True)
    active_model_version = Column(String(60), nullable=False)
    promoted = Column(Boolean, nullable=False, default=False)
    reason = Column(Text, nullable=False)
    net_mae_candidate = Column(Float, nullable=True)
    net_mae_active = Column(Float, nullable=True)
    ece_candidate = Column(Float, nullable=True)
    ece_active = Column(Float, nullable=True)
    sample_size = Column(Integer, nullable=False, default=0)
    promoted_by = Column(String(255), nullable=False, default="admin")
    promoted_at = Column(DateTime, nullable=False, default=datetime.now(UTC))

    __table_args__ = (
        Index("ix_promotion_records_candidate", "candidate_model_version"),
        Index("ix_promotion_records_promoted", "promoted"),
    )

    def __repr__(self) -> str:
        return (
            f"<PromotionRecord(id={self.id}, candidate={self.candidate_model_version}, "
            f"active={self.active_model_version}, promoted={self.promoted})>"
        )


@dataclass
class PromotionResult:
    """Result of a promotion gate evaluation.

    Attributes:
        eligible: Whether the candidate is eligible for promotion.
        reason: Reason for the decision.
        net_mae_candidate: Net MAE of the candidate model.
        net_mae_active: Net MAE of the active model.
        ece_candidate: Calibration ECE of the candidate model.
        ece_active: Calibration ECE of the active model.
        sample_size: Number of held-out outcomes used.
        net_mae_improved: Whether net MAE improved.
        ece_improved: Whether ECE improved.
        sufficient_sample: Whether sample size is sufficient.
    """

    eligible: bool
    reason: str
    net_mae_candidate: float = 0.0
    net_mae_active: float = 0.0
    ece_candidate: float = 0.0
    ece_active: float = 0.0
    sample_size: int = 0
    net_mae_improved: bool = False
    ece_improved: bool = False
    sufficient_sample: bool = False


class PromotionGate:
    """Promotion gate for model versions.

    A candidate model must beat the active model on:
    1. Net MAE (lower is better)
    2. Calibration ECE (lower is better)
    3. Minimum sample size (>= MIN_PROMOTION_SAMPLE)

    Promotion is a recorded, audited action by an admin.
    """

    def __init__(self, min_sample: int = MIN_PROMOTION_SAMPLE) -> None:
        self.min_sample = min_sample

    def evaluate(
        self,
        candidate_net_mae: float,
        active_net_mae: float,
        candidate_ece: float,
        active_ece: float,
        sample_size: int,
    ) -> PromotionResult:
        """Evaluate whether a candidate model should be promoted.

        Args:
            candidate_net_mae: Net MAE of the candidate model (lower is better).
            active_net_mae: Net MAE of the active model (lower is better).
            candidate_ece: Calibration ECE of the candidate model (lower is better).
            active_ece: Calibration ECE of the active model (lower is better).
            sample_size: Number of held-out outcomes used.

        Returns:
            PromotionResult with eligibility decision.
        """
        sufficient_sample = sample_size >= self.min_sample
        net_mae_improved = candidate_net_mae < active_net_mae
        ece_improved = candidate_ece < active_ece

        if not sufficient_sample:
            return PromotionResult(
                eligible=False,
                reason=f"Insufficient sample size: {sample_size} < {self.min_sample}",
                net_mae_candidate=candidate_net_mae,
                net_mae_active=active_net_mae,
                ece_candidate=candidate_ece,
                ece_active=active_ece,
                sample_size=sample_size,
                net_mae_improved=net_mae_improved,
                ece_improved=ece_improved,
                sufficient_sample=sufficient_sample,
            )

        if not net_mae_improved:
            return PromotionResult(
                eligible=False,
                reason=f"Net MAE not improved: candidate={candidate_net_mae:.4f} >= active={active_net_mae:.4f}",
                net_mae_candidate=candidate_net_mae,
                net_mae_active=active_net_mae,
                ece_candidate=candidate_ece,
                ece_active=active_ece,
                sample_size=sample_size,
                net_mae_improved=net_mae_improved,
                ece_improved=ece_improved,
                sufficient_sample=sufficient_sample,
            )

        if not ece_improved:
            return PromotionResult(
                eligible=False,
                reason=f"ECE not improved: candidate={candidate_ece:.4f} >= active={active_ece:.4f}",
                net_mae_candidate=candidate_net_mae,
                net_mae_active=active_net_mae,
                ece_candidate=candidate_ece,
                ece_active=active_ece,
                sample_size=sample_size,
                net_mae_improved=net_mae_improved,
                ece_improved=ece_improved,
                sufficient_sample=sufficient_sample,
            )

        return PromotionResult(
            eligible=True,
            reason=f"Eligible for promotion: net MAE improved ({active_net_mae:.4f} -> {candidate_net_mae:.4f}), ECE improved ({active_ece:.4f} -> {candidate_ece:.4f}), sample size sufficient ({sample_size} >= {self.min_sample})",
            net_mae_candidate=candidate_net_mae,
            net_mae_active=active_net_mae,
            ece_candidate=candidate_ece,
            ece_active=active_ece,
            sample_size=sample_size,
            net_mae_improved=net_mae_improved,
            ece_improved=ece_improved,
            sufficient_sample=sufficient_sample,
        )

    async def record_promotion(
        self,
        session: AsyncSession,
        candidate_model_version: str,
        active_model_version: str,
        result: PromotionResult,
        promoted_by: str = "admin",
    ) -> PromotionRecord:
        """Record a promotion decision (audited).

        Args:
            session: Database session.
            candidate_model_version: Version of the candidate model.
            active_model_version: Version of the active model.
            result: PromotionResult from evaluate().
            promoted_by: Admin who performed the action.

        Returns:
            The created PromotionRecord.
        """
        record = PromotionRecord(
            candidate_model_version=candidate_model_version,
            active_model_version=active_model_version,
            promoted=result.eligible,
            reason=result.reason,
            net_mae_candidate=result.net_mae_candidate,
            net_mae_active=result.net_mae_active,
            ece_candidate=result.ece_candidate,
            ece_active=result.ece_active,
            sample_size=result.sample_size,
            promoted_by=promoted_by,
            promoted_at=datetime.now(UTC),
        )
        session.add(record)
        await session.flush()

        logger.info(
            "promotion_recorded",
            candidate=candidate_model_version,
            active=active_model_version,
            promoted=result.eligible,
            reason=result.reason,
            promoted_by=promoted_by,
        )

        return record

    async def get_promotion_history(
        self,
        session: AsyncSession,
        candidate_model_version: str | None = None,
        limit: int = 50,
    ) -> list[PromotionRecord]:
        """Get promotion history.

        Args:
            session: Database session.
            candidate_model_version: Optional filter by candidate version.
            limit: Maximum results.

        Returns:
            List of PromotionRecord objects.
        """
        query = select(PromotionRecord).order_by(PromotionRecord.promoted_at.desc())

        if candidate_model_version:
            query = query.where(PromotionRecord.candidate_model_version == candidate_model_version)

        query = query.limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())