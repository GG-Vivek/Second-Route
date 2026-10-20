"""
Tests for monthly expert review (Phase 6 - F6.9).
"""

import pytest
from datetime import datetime, timezone, UTC
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.learning.expert_review import (
    ExpertReviewService,
    ExpertReviewLabel,
    ExpertReviewSummary,
    ReviewSample,
    DEFAULT_SAMPLE_SIZE,
)


class TestExpertReviewSampling:
    """Tests for expert review sampling."""

    def test_sample_decisions_reproducible(self) -> None:
        """Test that sampling is reproducible from a seed."""
        service = ExpertReviewService(sample_size=5, seed=42)

        decisions = [
            {
                "decision_id": str(uuid4()),
                "sku_family": "MacBook Pro",
                "recommended_channel": "RESELL_OPEN_BOX",
                "confidence": 0.85,
            }
            for _ in range(50)
        ]

        # Set consistent decision IDs
        for _i, d in enumerate(decisions):
            d["decision_id"] = str(uuid4())

        samples1 = service.sample_decisions(decisions, "MacBook Pro", seed=42)
        samples2 = service.sample_decisions(decisions, "MacBook Pro", seed=42)

        # Should be reproducible
        assert len(samples1) == len(samples2)
        assert [s.decision_id for s in samples1] == [s.decision_id for s in samples2]

    def test_sample_size(self) -> None:
        """Test that sample size is correct."""
        service = ExpertReviewService(sample_size=10, seed=42)

        decisions = [
            {
                "decision_id": str(uuid4()),
                "sku_family": "MacBook Pro",
                "recommended_channel": "RESELL_OPEN_BOX",
                "confidence": 0.85,
            }
            for _ in range(50)
        ]

        samples = service.sample_decisions(decisions, "MacBook Pro", seed=42)
        assert len(samples) == 10

    def test_sample_size_capped_by_available(self) -> None:
        """Test that sample size is capped by available decisions."""
        service = ExpertReviewService(sample_size=30, seed=42)

        decisions = [
            {
                "decision_id": str(uuid4()),
                "sku_family": "MacBook Pro",
                "recommended_channel": "RESELL_OPEN_BOX",
                "confidence": 0.85,
            }
            for _ in range(10)
        ]

        samples = service.sample_decisions(decisions, "MacBook Pro", seed=42)
        assert len(samples) == 10

    def test_sample_empty_category(self) -> None:
        """Test sampling from empty category."""
        service = ExpertReviewService(sample_size=30, seed=42)

        decisions = [
            {
                "decision_id": str(uuid4()),
                "sku_family": "MacBook Air",
                "recommended_channel": "RESELL_OPEN_BOX",
                "confidence": 0.85,
            }
            for _ in range(10)
        ]

        samples = service.sample_decisions(decisions, "MacBook Pro", seed=42)
        assert len(samples) == 0

    def test_sample_all_categories(self) -> None:
        """Test sampling from all categories."""
        service = ExpertReviewService(sample_size=5, seed=42)

        decisions = []
        for family in ["MacBook Pro", "MacBook Air", "ThinkPad X1 Carbon"]:
            for _ in range(20):
                decisions.append(
                    {
                        "decision_id": str(uuid4()),
                        "sku_family": family,
                        "recommended_channel": "RESELL_OPEN_BOX",
                        "confidence": 0.85,
                    }
                )

        results = service.sample_all_categories(
            decisions, ["MacBook Pro", "MacBook Air", "ThinkPad X1 Carbon"], seed=42
        )

        assert len(results) == 3
        assert len(results["MacBook Pro"]) == 5
        assert len(results["MacBook Air"]) == 5
        assert len(results["ThinkPad X1 Carbon"]) == 5

    def test_sample_reproducible_with_different_seeds(self) -> None:
        """Test that different seeds produce different samples."""
        service = ExpertReviewService(sample_size=5, seed=42)

        decisions = [
            {
                "decision_id": str(uuid4()),
                "sku_family": "MacBook Pro",
                "recommended_channel": "RESELL_OPEN_BOX",
                "confidence": 0.85,
            }
            for _ in range(50)
        ]

        samples1 = service.sample_decisions(decisions, "MacBook Pro", seed=42)
        samples2 = service.sample_decisions(decisions, "MacBook Pro", seed=99)

        # Different seeds should produce different samples
        ids1 = [str(s.decision_id) for s in samples1]
        ids2 = [str(s.decision_id) for s in samples2]
        assert ids1 != ids2

    def test_sample_seed_stored(self) -> None:
        """Test that sample seed is stored in the sample."""
        service = ExpertReviewService(sample_size=5, seed=42)

        decisions = [
            {
                "decision_id": str(uuid4()),
                "sku_family": "MacBook Pro",
                "recommended_channel": "RESELL_OPEN_BOX",
                "confidence": 0.85,
            }
            for _ in range(20)
        ]

        samples = service.sample_decisions(decisions, "MacBook Pro", seed=42)
        for sample in samples:
            assert sample.sample_seed == 42


class TestExpertReviewLabels:
    """Tests for expert review labels."""

    @pytest.mark.asyncio
    async def test_record_review_agreement(self, db_session: AsyncSession) -> None:
        """Test recording an agreement label."""
        service = ExpertReviewService()
        decision_id = uuid4()

        label = await service.record_review(
            session=db_session,
            decision_id=decision_id,
            reviewer_id="expert@example.com",
            agreement=True,
            reason="Looks correct",
        )

        assert label is not None
        assert label.decision_id == decision_id
        assert label.reviewer_id == "expert@example.com"
        assert bool(label.agreement) is True
        assert label.reason == "Looks correct"

    @pytest.mark.asyncio
    async def test_record_review_disagreement(self, db_session: AsyncSession) -> None:
        """Test recording a disagreement label."""
        service = ExpertReviewService()
        decision_id = uuid4()

        label = await service.record_review(
            session=db_session,
            decision_id=decision_id,
            reviewer_id="expert@example.com",
            agreement=False,
            reason="Wrong channel",
            suggested_channel="RESELL_REFURB",
        )

        assert label is not None
        assert bool(label.agreement) is False
        assert label.reason == "Wrong channel"
        assert label.suggested_channel == "RESELL_REFURB"

    @pytest.mark.asyncio
    async def test_get_review_labels(self, db_session: AsyncSession) -> None:
        """Test retrieving review labels."""
        service = ExpertReviewService()
        decision_id = uuid4()

        await service.record_review(
            session=db_session,
            decision_id=decision_id,
            reviewer_id="expert@example.com",
            agreement=True,
        )

        labels = await service.get_review_labels(
            session=db_session,
            decision_id=decision_id,
        )

        assert len(labels) == 1
        assert labels[0].decision_id == decision_id

    @pytest.mark.asyncio
    async def test_get_review_labels_by_reviewer(self, db_session: AsyncSession) -> None:
        """Test retrieving review labels by reviewer."""
        service = ExpertReviewService()

        await service.record_review(
            session=db_session,
            decision_id=uuid4(),
            reviewer_id="expert1@example.com",
            agreement=True,
        )
        await service.record_review(
            session=db_session,
            decision_id=uuid4(),
            reviewer_id="expert2@example.com",
            agreement=False,
        )

        labels = await service.get_review_labels(
            session=db_session,
            reviewer_id="expert1@example.com",
        )

        assert len(labels) == 1
        assert labels[0].reviewer_id == "expert1@example.com"

    @pytest.mark.asyncio
    async def test_multiple_reviews_same_decision(self, db_session: AsyncSession) -> None:
        """Test that multiple reviews can be recorded for the same decision."""
        service = ExpertReviewService()
        decision_id = uuid4()

        await service.record_review(
            session=db_session,
            decision_id=decision_id,
            reviewer_id="expert1@example.com",
            agreement=True,
        )
        await service.record_review(
            session=db_session,
            decision_id=decision_id,
            reviewer_id="expert2@example.com",
            agreement=False,
        )

        labels = await service.get_review_labels(
            session=db_session,
            decision_id=decision_id,
        )

        assert len(labels) == 2


class TestExpertReviewSummary:
    """Tests for expert review summary."""

    def test_compute_summary(self) -> None:
        """Test computing summary statistics."""
        service = ExpertReviewService()

        # Create mock labels
        labels = []
        for i in range(10):
            label = ExpertReviewLabel(
                decision_id=uuid4(),
                reviewer_id="expert@example.com",
                agreement=i < 7,  # 7 agreements, 3 disagreements
                reason="Wrong channel" if i >= 7 else None,
                reviewed_at=datetime.now(UTC),
            )
            labels.append(label)

        summary = service.compute_summary(labels)

        assert summary.total_reviewed == 10
        assert summary.agreement_count == 7
        assert summary.disagreement_count == 3
        assert summary.agreement_rate == 0.7
        assert summary.by_reason.get("Wrong channel") == 3

    def test_compute_summary_empty(self) -> None:
        """Test computing summary with no labels."""
        service = ExpertReviewService()
        summary = service.compute_summary([])

        assert summary.total_reviewed == 0
        assert summary.agreement_count == 0
        assert summary.disagreement_count == 0
        assert summary.agreement_rate == 0.0
