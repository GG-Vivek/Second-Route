"""
Monthly expert review for Phase 6 (F6.9).

Workflow that samples 30 random decisions per category for expert review.
Reviewer labels agreement and reason. Labels are stored and can feed training.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, UTC
from typing import Any, Optional, Sequence
from uuid import UUID

import numpy as np
import structlog
from pydantic import BaseModel, ConfigDict

from secondroute.core.db import Base
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = structlog.get_logger(__name__)

# Default sample size per category
DEFAULT_SAMPLE_SIZE = 30


class ExpertReviewLabel(Base):
    """Stores expert review labels for decisions.

    Attributes:
        decision_id: The decision being reviewed.
        reviewer_id: The expert reviewer.
        agreement: Whether the reviewer agrees with the decision.
        reason: Reason for agreement/disagreement.
        suggested_channel: Suggested alternative channel (if disagreeing).
        reviewed_at: Timestamp of the review.
    """

    __tablename__ = "expert_review_labels"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id = Column(String(255), nullable=False)
    agreement = Column(Boolean, nullable=False)
    reason = Column(Text, nullable=True)
    suggested_channel = Column(String(40), nullable=True)
    reviewed_at = Column(DateTime, nullable=False, default=datetime.now(UTC))

    __table_args__ = (
        Index("ix_expert_review_labels_decision", "decision_id"),
        Index("ix_expert_review_labels_reviewer", "reviewer_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ExpertReviewLabel(id={self.id}, decision_id={self.decision_id}, "
            f"agreement={self.agreement})>"
        )


@dataclass
class ReviewSample:
    """A sampled decision for expert review.

    Attributes:
        decision_id: The decision ID.
        sku_family: The SKU family.
        recommended_channel: The recommended channel.
        confidence: The decision confidence.
        sample_seed: The seed used for sampling.
    """

    decision_id: UUID
    sku_family: str
    recommended_channel: str
    confidence: float
    sample_seed: int


@dataclass
class ExpertReviewSummary:
    """Summary of expert review results.

    Attributes:
        total_reviewed: Total number of decisions reviewed.
        agreement_count: Number of agreements.
        disagreement_count: Number of disagreements.
        agreement_rate: Rate of agreement.
        by_channel: Agreement rate by channel.
        by_reason: Count of each disagreement reason.
    """

    total_reviewed: int
    agreement_count: int
    disagreement_count: int
    agreement_rate: float
    by_channel: dict[str, float] = field(default_factory=dict)
    by_reason: dict[str, int] = field(default_factory=dict)


class ExpertReviewService:
    """Service for monthly expert review workflow.

    Samples 30 random decisions per category for expert review.
    Reviewer labels agreement and reason. Labels are stored and can
    feed training.
    """

    def __init__(
        self,
        sample_size: int = DEFAULT_SAMPLE_SIZE,
        seed: int = 42,
    ) -> None:
        self.sample_size = sample_size
        self.seed = seed

    def sample_decisions(
        self,
        decisions: list[dict[str, Any]],
        category: str,
        seed: int | None = None,
    ) -> list[ReviewSample]:
        """Sample random decisions for expert review.

        The sample is reproducible from a seed.

        Args:
            decisions: List of decision dictionaries with decision_id, sku_family,
                      recommended_channel, confidence.
            category: The category to sample from.
            seed: Optional seed override. Uses self.seed if None.

        Returns:
            List of ReviewSample objects.
        """
        if seed is None:
            seed = self.seed

        # Filter decisions by category
        category_decisions = [d for d in decisions if d.get("sku_family") == category]

        if not category_decisions:
            return []

        # Use seeded RNG for reproducible sampling
        rng = np.random.default_rng(seed)

        # Sample without replacement
        n = min(self.sample_size, len(category_decisions))
        indices = rng.choice(len(category_decisions), size=n, replace=False)

        samples = []
        for idx in indices:
            d = category_decisions[idx]
            samples.append(
                ReviewSample(
                    decision_id=UUID(str(d["decision_id"])),
                    sku_family=d.get("sku_family", ""),
                    recommended_channel=d.get("recommended_channel", ""),
                    confidence=d.get("confidence", 0.0),
                    sample_seed=seed,
                )
            )

        return samples

    def sample_all_categories(
        self,
        decisions: list[dict[str, Any]],
        categories: list[str],
        seed: int | None = None,
    ) -> dict[str, list[ReviewSample]]:
        """Sample decisions for all categories.

        Args:
            decisions: List of decision dictionaries.
            categories: List of categories to sample from.
            seed: Optional seed override.

        Returns:
            Dictionary mapping category -> list of ReviewSample.
        """
        if seed is None:
            seed = self.seed

        results = {}
        for i, category in enumerate(categories):
            # Use a different seed for each category for independence
            category_seed = seed + i
            results[category] = self.sample_decisions(decisions, category, seed=category_seed)

        return results

    async def record_review(  # noqa: PLR0913, PLR0917
        self,
        session: AsyncSession,
        decision_id: UUID,
        reviewer_id: str,
        agreement: bool,
        reason: str | None = None,
        suggested_channel: str | None = None,
    ) -> ExpertReviewLabel:
        """Record an expert review label.

        Args:
            session: Database session.
            decision_id: The decision being reviewed.
            reviewer_id: The expert reviewer.
            agreement: Whether the reviewer agrees.
            reason: Reason for agreement/disagreement.
            suggested_channel: Suggested alternative channel.

        Returns:
            The created ExpertReviewLabel.
        """
        label = ExpertReviewLabel(
            decision_id=decision_id,
            reviewer_id=reviewer_id,
            agreement=agreement,
            reason=reason,
            suggested_channel=suggested_channel,
            reviewed_at=datetime.now(UTC),
        )
        session.add(label)
        await session.flush()

        logger.info(
            "expert_review_recorded",
            decision_id=str(decision_id),
            reviewer=reviewer_id,
            agreement=agreement,
        )

        return label

    async def get_review_labels(
        self,
        session: AsyncSession,
        decision_id: UUID | None = None,
        reviewer_id: str | None = None,
        limit: int = 100,
    ) -> list[ExpertReviewLabel]:
        """Get expert review labels.

        Args:
            session: Database session.
            decision_id: Optional filter by decision ID.
            reviewer_id: Optional filter by reviewer.
            limit: Maximum results.

        Returns:
            List of ExpertReviewLabel objects.
        """
        query = select(ExpertReviewLabel).order_by(ExpertReviewLabel.reviewed_at.desc())

        if decision_id:
            query = query.where(ExpertReviewLabel.decision_id == decision_id)
        if reviewer_id:
            query = query.where(ExpertReviewLabel.reviewer_id == reviewer_id)

        query = query.limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    def compute_summary(
        self,
        labels: list[ExpertReviewLabel],
    ) -> ExpertReviewSummary:
        """Compute summary statistics from review labels.

        Args:
            labels: List of ExpertReviewLabel objects.

        Returns:
            ExpertReviewSummary with statistics.
        """
        total = len(labels)
        agreements = sum(1 for label in labels if label.agreement)
        disagreements = total - agreements
        agreement_rate = agreements / total if total > 0 else 0.0

        # By channel (need decision info - simplified here)
        by_channel: dict[str, float] = {}

        # By reason
        by_reason: dict[str, int] = {}
        for label in labels:
            if not label.agreement and label.reason:
                reason = str(label.reason)
                by_reason[reason] = by_reason.get(reason, 0) + 1

        return ExpertReviewSummary(
            total_reviewed=total,
            agreement_count=agreements,
            disagreement_count=disagreements,
            agreement_rate=agreement_rate,
            by_channel=by_channel,
            by_reason=by_reason,
        )
