"""
Tests for upstream return-reason insights (Phase 7 - F7.4).
"""

import pytest
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.identity.models import SKU
from secondroute.intake.models import Unit, ReturnReasonCode, OrderChannel
from secondroute.insights.return_reasons import (
    ReturnReasonInsights,
    ReturnReasonReport,
    ReturnReasonSummary,
)


class TestReturnReasonInsights:
    """Tests for return reason insights."""

    @pytest.fixture
    def service(self) -> ReturnReasonInsights:
        """Create a return reason insights service."""
        return ReturnReasonInsights()

    @pytest.mark.asyncio
    async def test_generate_report_empty(
        self, service: ReturnReasonInsights, db_session: AsyncSession
    ) -> None:
        """Test generating report with no units."""
        report = await service.generate_report(db_session)

        assert report is not None
        assert report.total_units == 0
        assert report.total_returns == 0
        assert report.overall_return_rate == 0.0
        assert len(report.by_family) == 0

    @pytest.mark.asyncio
    async def test_generate_report_with_units(
        self, service: ReturnReasonInsights, db_session: AsyncSession
    ) -> None:
        """Test generating report with units."""
        # Create SKUs
        sku1 = SKU(
            family="MacBook Pro",
            model_name="M3 Pro",
            year="2023",
            storage_gb="512",
            ram_gb="18",
            color="Space Gray",
            region="US",
            specs_json={},
            source="test",
            as_of=datetime(2024, 1, 15).date(),
        )
        sku2 = SKU(
            family="MacBook Air",
            model_name="M3",
            year="2024",
            storage_gb="256",
            ram_gb="8",
            color="Midnight",
            region="US",
            specs_json={},
            source="test",
            as_of=datetime(2024, 1, 15).date(),
        )
        db_session.add_all([sku1, sku2])
        await db_session.commit()
        await db_session.refresh(sku1)
        await db_session.refresh(sku2)

        # Create units with different return reasons
        units = [
            Unit(
                sku_id=sku1.id,
                return_reason_code=ReturnReasonCode.BUYER_REMORSE,
                order_channel=OrderChannel.ONLINE,
            ),
            Unit(
                sku_id=sku1.id,
                return_reason_code=ReturnReasonCode.BUYER_REMORSE,
                order_channel=OrderChannel.ONLINE,
            ),
            Unit(
                sku_id=sku1.id,
                return_reason_code=ReturnReasonCode.DEFECTIVE,
                order_channel=OrderChannel.ONLINE,
            ),
            Unit(
                sku_id=sku2.id,
                return_reason_code=ReturnReasonCode.WRONG_ITEM,
                order_channel=OrderChannel.RETAIL,
            ),
            Unit(
                sku_id=sku2.id,
                return_reason_code=ReturnReasonCode.BUYER_REMORSE,
                order_channel=OrderChannel.RETAIL,
            ),
        ]
        db_session.add_all(units)
        await db_session.commit()

        report = await service.generate_report(db_session)

        assert report is not None
        assert report.total_units == 5
        assert report.total_returns == 5
        assert "MacBook Pro" in report.by_family
        assert "MacBook Air" in report.by_family

        # Check MacBook Pro summary
        mbp_summary = report.by_family["MacBook Pro"]
        assert mbp_summary.total_returns == 3
        assert mbp_summary.reason_counts["buyer_remorse"] == 2
        assert mbp_summary.reason_counts["defective"] == 1
        assert mbp_summary.top_reason == "buyer_remorse"
        assert mbp_summary.top_reason_rate == pytest.approx(2 / 3)

        # Check MacBook Air summary
        mba_summary = report.by_family["MacBook Air"]
        assert mba_summary.total_returns == 2
        assert mba_summary.reason_counts["wrong_item"] == 1
        assert mba_summary.reason_counts["buyer_remorse"] == 1

    @pytest.mark.asyncio
    async def test_generate_report_filtered_by_family(
        self, service: ReturnReasonInsights, db_session: AsyncSession
    ) -> None:
        """Test generating report filtered by SKU family."""
        # Create SKUs
        sku1 = SKU(
            family="MacBook Pro",
            model_name="M3 Pro",
            year="2023",
            storage_gb="512",
            ram_gb="18",
            color="Space Gray",
            region="US",
            specs_json={},
            source="test",
            as_of=datetime(2024, 1, 15).date(),
        )
        sku2 = SKU(
            family="MacBook Air",
            model_name="M3",
            year="2024",
            storage_gb="256",
            ram_gb="8",
            color="Midnight",
            region="US",
            specs_json={},
            source="test",
            as_of=datetime(2024, 1, 15).date(),
        )
        db_session.add_all([sku1, sku2])
        await db_session.commit()
        await db_session.refresh(sku1)
        await db_session.refresh(sku2)

        units = [
            Unit(
                sku_id=sku1.id,
                return_reason_code=ReturnReasonCode.BUYER_REMORSE,
                order_channel=OrderChannel.ONLINE,
            ),
            Unit(
                sku_id=sku2.id,
                return_reason_code=ReturnReasonCode.WRONG_ITEM,
                order_channel=OrderChannel.RETAIL,
            ),
        ]
        db_session.add_all(units)
        await db_session.commit()

        # Filter by family
        report = await service.generate_report(db_session, sku_families=["MacBook Pro"])

        assert report is not None
        assert report.total_units == 1
        assert "MacBook Pro" in report.by_family
        assert "MacBook Air" not in report.by_family

    @pytest.mark.asyncio
    async def test_get_top_return_reasons(
        self, service: ReturnReasonInsights, db_session: AsyncSession
    ) -> None:
        """Test getting top return reasons for a family."""
        # Create SKU
        sku = SKU(
            family="MacBook Pro",
            model_name="M3 Pro",
            year="2023",
            storage_gb="512",
            ram_gb="18",
            color="Space Gray",
            region="US",
            specs_json={},
            source="test",
            as_of=datetime(2024, 1, 15).date(),
        )
        db_session.add(sku)
        await db_session.commit()
        await db_session.refresh(sku)

        # Create units with different reasons
        units = [
            Unit(
                sku_id=sku.id,
                return_reason_code=ReturnReasonCode.BUYER_REMORSE,
                order_channel=OrderChannel.ONLINE,
            ),
            Unit(
                sku_id=sku.id,
                return_reason_code=ReturnReasonCode.BUYER_REMORSE,
                order_channel=OrderChannel.ONLINE,
            ),
            Unit(
                sku_id=sku.id,
                return_reason_code=ReturnReasonCode.BUYER_REMORSE,
                order_channel=OrderChannel.ONLINE,
            ),
            Unit(
                sku_id=sku.id,
                return_reason_code=ReturnReasonCode.DEFECTIVE,
                order_channel=OrderChannel.ONLINE,
            ),
            Unit(
                sku_id=sku.id,
                return_reason_code=ReturnReasonCode.WRONG_ITEM,
                order_channel=OrderChannel.ONLINE,
            ),
        ]
        db_session.add_all(units)
        await db_session.commit()

        top_reasons = await service.get_top_return_reasons(db_session, "MacBook Pro", limit=3)

        assert len(top_reasons) == 3
        # Top reason should be buyer_remorse with 3 occurrences
        assert top_reasons[0][0] == "buyer_remorse"
        assert top_reasons[0][1] == 3
        assert top_reasons[0][2] == pytest.approx(3 / 5)

    @pytest.mark.asyncio
    async def test_get_return_rate_by_family(
        self, service: ReturnReasonInsights, db_session: AsyncSession
    ) -> None:
        """Test getting return rate by family."""
        # Create SKUs
        sku1 = SKU(
            family="MacBook Pro",
            model_name="M3 Pro",
            year="2023",
            storage_gb="512",
            ram_gb="18",
            color="Space Gray",
            region="US",
            specs_json={},
            source="test",
            as_of=datetime(2024, 1, 15).date(),
        )
        sku2 = SKU(
            family="MacBook Air",
            model_name="M3",
            year="2024",
            storage_gb="256",
            ram_gb="8",
            color="Midnight",
            region="US",
            specs_json={},
            source="test",
            as_of=datetime(2024, 1, 15).date(),
        )
        db_session.add_all([sku1, sku2])
        await db_session.commit()
        await db_session.refresh(sku1)
        await db_session.refresh(sku2)

        units = [
            Unit(
                sku_id=sku1.id,
                return_reason_code=ReturnReasonCode.BUYER_REMORSE,
                order_channel=OrderChannel.ONLINE,
            ),
            Unit(
                sku_id=sku1.id,
                return_reason_code=ReturnReasonCode.DEFECTIVE,
                order_channel=OrderChannel.ONLINE,
            ),
            Unit(
                sku_id=sku2.id,
                return_reason_code=ReturnReasonCode.WRONG_ITEM,
                order_channel=OrderChannel.RETAIL,
            ),
        ]
        db_session.add_all(units)
        await db_session.commit()

        rates = await service.get_return_rate_by_family(db_session)

        assert "MacBook Pro" in rates
        assert "MacBook Air" in rates
        assert rates["MacBook Pro"] == 2.0
        assert rates["MacBook Air"] == 1.0

    @pytest.mark.asyncio
    async def test_report_reproduces_counts(
        self, service: ReturnReasonInsights, db_session: AsyncSession
    ) -> None:
        """Test that report reproduces counts from raw unit table."""
        # Create SKU
        sku = SKU(
            family="MacBook Pro",
            model_name="M3 Pro",
            year="2023",
            storage_gb="512",
            ram_gb="18",
            color="Space Gray",
            region="US",
            specs_json={},
            source="test",
            as_of=datetime(2024, 1, 15).date(),
        )
        db_session.add(sku)
        await db_session.commit()
        await db_session.refresh(sku)

        # Create units
        units = [
            Unit(
                sku_id=sku.id,
                return_reason_code=ReturnReasonCode.BUYER_REMORSE,
                order_channel=OrderChannel.ONLINE,
            ),
            Unit(
                sku_id=sku.id,
                return_reason_code=ReturnReasonCode.DEFECTIVE,
                order_channel=OrderChannel.ONLINE,
            ),
            Unit(
                sku_id=sku.id,
                return_reason_code=ReturnReasonCode.WRONG_ITEM,
                order_channel=OrderChannel.ONLINE,
            ),
        ]
        db_session.add_all(units)
        await db_session.commit()

        # Get raw count from DB
        result = await db_session.execute(
            select(Unit).join(SKU, Unit.sku_id == SKU.id).where(SKU.family == "MacBook Pro")
        )
        raw_count = len(result.scalars().all())

        # Generate report
        report = await service.generate_report(db_session)

        # Report should reproduce raw count
        assert report.by_family["MacBook Pro"].total_returns == raw_count
