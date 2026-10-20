"""
Promotion gate for Phase 6 (F6.3).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, UTC
from typing import Any, Optional
from uuid import UUID

import structlog
from pydantic import BaseModel, ConfigDict

from secondroute.core.db import Base
from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

MIN_PROMOTION_SAMPLE = 50


class PromotionRecord(Base):
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
        return f"<PromotionRecord(id={self.id}, candidate={self.candidate_model_version}, promoted={self.promoted})>"


@dataclass
class PromotionResult:
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
        query = select(PromotionRecord).order_by(PromotionRecord.promoted_at.desc())

        if candidate_model_version:
            query = query.where(PromotionRecord.candidate_model_version == candidate_model_version)

        query = query.limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())