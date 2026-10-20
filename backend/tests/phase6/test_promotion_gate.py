"""
Tests for the promotion gate (Phase 6 - F6.3).
"""

import pytest
from datetime import datetime, timezone, UTC
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.learning.promotion import (
    PromotionGate,
    PromotionRecord,
    PromotionResult,
)


class TestPromotionGateEvaluate:
    """Tests for PromotionGate.evaluate()."""

    def test_eligible_candidate(self) -> None:
        """Test that a candidate that beats active on both metrics is eligible."""
        gate = PromotionGate(min_sample=50)

        result = gate.evaluate(
            candidate_net_mae=0.10,
            active_net_mae=0.15,
            candidate_ece=0.03,
            active_ece=0.05,
            sample_size=100,
        )

        assert result.eligible is True
        assert "Eligible for promotion" in result.reason
        assert result.net_mae_improved is True
        assert result.ece_improved is True
        assert result.sufficient_sample is True

    def test_insufficient_sample(self) -> None:
        """Test that insufficient sample size blocks promotion."""
        gate = PromotionGate(min_sample=50)

        result = gate.evaluate(
            candidate_net_mae=0.10,
            active_net_mae=0.15,
            candidate_ece=0.03,
            active_ece=0.05,
            sample_size=30,
        )

        assert result.eligible is False
        assert "Insufficient sample size" in result.reason
        assert result.sufficient_sample is False

    def test_net_mae_not_improved(self) -> None:
        """Test that worse net MAE blocks promotion."""
        gate = PromotionGate(min_sample=50)

        result = gate.evaluate(
            candidate_net_mae=0.20,  # Worse than active
            active_net_mae=0.15,
            candidate_ece=0.03,
            active_ece=0.05,
            sample_size=100,
        )

        assert result.eligible is False
        assert "Net MAE not improved" in result.reason
        assert result.net_mae_improved is False
        assert result.ece_improved is True

    def test_ece_not_improved(self) -> None:
        """Test that worse ECE blocks promotion."""
        gate = PromotionGate(min_sample=50)

        result = gate.evaluate(
            candidate_net_mae=0.10,
            active_net_mae=0.15,
            candidate_ece=0.08,  # Worse than active
            active_ece=0.05,
            sample_size=100,
        )

        assert result.eligible is False
        assert "ECE not improved" in result.reason
        assert result.net_mae_improved is True
        assert result.ece_improved is False

    def test_both_metrics_not_improved(self) -> None:
        """Test that worse on both metrics blocks promotion."""
        gate = PromotionGate(min_sample=50)

        result = gate.evaluate(
            candidate_net_mae=0.20,  # Worse
            active_net_mae=0.15,
            candidate_ece=0.08,  # Worse
            active_ece=0.05,
            sample_size=100,
        )

        assert result.eligible is False
        # Should report net MAE first
        assert "Net MAE not improved" in result.reason

    def test_equal_net_mae_blocks(self) -> None:
        """Test that equal net MAE blocks promotion (must be strictly better)."""
        gate = PromotionGate(min_sample=50)

        result = gate.evaluate(
            candidate_net_mae=0.15,  # Equal to active
            active_net_mae=0.15,
            candidate_ece=0.03,
            active_ece=0.05,
            sample_size=100,
        )

        assert result.eligible is False
        assert "Net MAE not improved" in result.reason

    def test_equal_ece_blocks(self) -> None:
        """Test that equal ECE blocks promotion (must be strictly better)."""
        gate = PromotionGate(min_sample=50)

        result = gate.evaluate(
            candidate_net_mae=0.10,
            active_net_mae=0.15,
            candidate_ece=0.05,  # Equal to active
            active_ece=0.05,
            sample_size=100,
        )

        assert result.eligible is False
        assert "ECE not improved" in result.reason

    def test_custom_min_sample(self) -> None:
        """Test with custom minimum sample size."""
        gate = PromotionGate(min_sample=10)

        result = gate.evaluate(
            candidate_net_mae=0.10,
            active_net_mae=0.15,
            candidate_ece=0.03,
            active_ece=0.05,
            sample_size=15,
        )

        assert result.eligible is True

    def test_boundary_sample_size(self) -> None:
        """Test with sample size exactly at minimum."""
        gate = PromotionGate(min_sample=50)

        result = gate.evaluate(
            candidate_net_mae=0.10,
            active_net_mae=0.15,
            candidate_ece=0.03,
            active_ece=0.05,
            sample_size=50,
        )

        assert result.eligible is True


class TestPromotionGateRecord:
    """Tests for PromotionGate.record_promotion()."""

    @pytest.mark.asyncio
    async def test_record_promotion_approved(self, db_session: AsyncSession) -> None:
        """Test recording an approved promotion."""
        gate = PromotionGate(min_sample=50)

        result = gate.evaluate(
            candidate_net_mae=0.10,
            active_net_mae=0.15,
            candidate_ece=0.03,
            active_ece=0.05,
            sample_size=100,
        )

        record = await gate.record_promotion(
            session=db_session,
            candidate_model_version="decision-v2",
            active_model_version="decision-v1",
            result=result,
            promoted_by="admin@example.com",
        )

        assert record is not None
        assert record.candidate_model_version == "decision-v2"
        assert record.active_model_version == "decision-v1"
        assert record.promoted is True
        assert record.promoted_by == "admin@example.com"
        assert record.sample_size == 100
        assert record.net_mae_candidate == 0.10
        assert record.net_mae_active == 0.15

    @pytest.mark.asyncio
    async def test_record_promotion_rejected(self, db_session: AsyncSession) -> None:
        """Test recording a rejected promotion."""
        gate = PromotionGate(min_sample=50)

        result = gate.evaluate(
            candidate_net_mae=0.20,  # Worse
            active_net_mae=0.15,
            candidate_ece=0.03,
            active_ece=0.05,
            sample_size=100,
        )

        record = await gate.record_promotion(
            session=db_session,
            candidate_model_version="decision-v2",
            active_model_version="decision-v1",
            result=result,
        )

        assert record is not None
        assert record.promoted is False
        assert "Net MAE not improved" in record.reason

    @pytest.mark.asyncio
    async def test_promotion_history(self, db_session: AsyncSession) -> None:
        """Test retrieving promotion history."""
        gate = PromotionGate(min_sample=50)

        # Create multiple promotion records
        for i in range(3):
            result = gate.evaluate(
                candidate_net_mae=0.10,
                active_net_mae=0.15,
                candidate_ece=0.03,
                active_ece=0.05,
                sample_size=100,
            )
            await gate.record_promotion(
                session=db_session,
                candidate_model_version=f"decision-v{i+2}",
                active_model_version="decision-v1",
                result=result,
            )

        # Get all history
        history = await gate.get_promotion_history(session=db_session)
        assert len(history) == 3

        # Filter by candidate version
        history_v2 = await gate.get_promotion_history(
            session=db_session,
            candidate_model_version="decision-v2",
        )
        assert len(history_v2) == 1
        assert history_v2[0].candidate_model_version == "decision-v2"

    @pytest.mark.asyncio
    async def test_promotion_is_recorded(self, db_session: AsyncSession) -> None:
        """Test that promotion decisions are recorded (audited)."""
        gate = PromotionGate(min_sample=50)

        result = gate.evaluate(
            candidate_net_mae=0.10,
            active_net_mae=0.15,
            candidate_ece=0.03,
            active_ece=0.05,
            sample_size=100,
        )

        record = await gate.record_promotion(
            session=db_session,
            candidate_model_version="decision-v2",
            active_model_version="decision-v1",
            result=result,
        )

        # Verify record exists in database
        db_result = await db_session.execute(
            select(PromotionRecord).where(PromotionRecord.id == record.id)
        )
        db_record = db_result.scalar_one_or_none()
        assert db_record is not None
        assert db_record.candidate_model_version == "decision-v2"
        assert db_record.promoted is True