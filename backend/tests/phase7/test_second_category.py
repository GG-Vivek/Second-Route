"""
Tests for second category onboarding (Phase 7 - F7.1).
"""

import pytest
from datetime import datetime
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.identity.models import SKU
from secondroute.intake.models import Unit, Inspection, ReturnReasonCode, OrderChannel
from secondroute.decision.engine import decide_unit
from secondroute.pricing.sources import SyntheticPriceSource


class TestSecondCategoryOnboarding:
    """Tests that a new category can be added by config alone."""

    @pytest.mark.asyncio
    async def test_new_category_produces_decision_card(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that a new SKU family (phones) produces a decision card."""
        # Create a phone SKU (new category)
        sku = SKU(
            family="iPhone",
            model_name="15 Pro",
            year="2023",
            storage_gb="256",
            ram_gb="8",
            color="Natural Titanium",
            region="US",
            specs_json={"cpu": "A17 Pro", "display": "6.1-inch Super Retina XDR"},
            source="manufacturer_specs",
            as_of=datetime(2024, 1, 15).date(),
        )
        db_session.add(sku)
        await db_session.commit()
        await db_session.refresh(sku)

        # Create a unit for this phone
        unit = Unit(
            sku_id=sku.id,
            serial="IPHONE123",
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)

        # Create an inspection
        inspection = Inspection(
            unit_id=unit.id,
            battery_health_pct="95",
            cosmetic_grade="A",
            functional_tests_json={"display": True, "camera": True},
            activation_lock="none",
            accessories_json={"charger": True},
            notes="Excellent condition",
        )
        db_session.add(inspection)
        await db_session.commit()
        await db_session.refresh(inspection)

        # Create cost tables for the new category
        from secondroute.costs.models import CostTable, CostKind

        cost_rows = [
            CostTable(
                kind=CostKind.CHANNEL_FEE_PCT,
                key="RESELL_OPEN_BOX",
                value=0.12,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.CHANNEL_FEE_PCT,
                key="RESELL_REFURB",
                value=0.15,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.FIXED_FEE,
                key="RESELL_OPEN_BOX",
                value=2.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.FIXED_FEE,
                key="RESELL_REFURB",
                value=3.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.LOGISTICS_COST,
                key="RESELL_OPEN_BOX",
                value=8.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.LOGISTICS_COST,
                key="RESELL_REFURB",
                value=12.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.HANDLING_COST,
                key="RESELL_OPEN_BOX",
                value=5.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.HANDLING_COST,
                key="RESELL_REFURB",
                value=10.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.REPAIR_COST,
                key="RESELL_OPEN_BOX",
                value=0.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.REPAIR_COST,
                key="RESELL_REFURB",
                value=20.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.HOLDING_COST_PER_DAY,
                key="RESELL_OPEN_BOX",
                value=0.5,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.HOLDING_COST_PER_DAY,
                key="RESELL_REFURB",
                value=0.5,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.EXPECTED_DAYS_TO_SELL,
                key="RESELL_OPEN_BOX",
                value=7.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.EXPECTED_DAYS_TO_SELL,
                key="RESELL_REFURB",
                value=14.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.RESALE_RECOVERY_PCT,
                key="RESELL_OPEN_BOX",
                value=0.90,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.RESALE_RECOVERY_PCT,
                key="RESELL_REFURB",
                value=0.75,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
        ]
        db_session.add_all(cost_rows)
        await db_session.commit()

        # Run decision with synthetic price source
        price_source = SyntheticPriceSource(sku_family="iPhone")
        risk_profile = "balanced"

        decision = await decide_unit(
            db_session,
            unit.id,
            price_source,
            risk_profile=risk_profile,
            seed=42,
        )

        # Verify a decision card is produced
        assert decision is not None
        assert decision.recommended_channel is not None
        assert decision.confidence >= 0.0
        assert decision.confidence <= 1.0
        assert decision.candidates is not None
        assert len(decision.candidates) > 0

        # Verify the decision can be fetched via API
        response = await client.get(f"/api/v1/decisions/{decision.id}")
        assert response.status_code == 200
        data = response.json()
        assert "recommended_channel" in data
        assert "confidence" in data
        assert "candidates" in data

    @pytest.mark.asyncio
    async def test_synthetic_price_source_unknown_family(self, db_session: AsyncSession) -> None:
        """Test that unknown SKU family uses default multiplier."""
        # Create a phone SKU
        sku = SKU(
            family="Samsung Galaxy",
            model_name="S24 Ultra",
            year="2024",
            storage_gb="512",
            ram_gb="12",
            color="Titanium Black",
            region="US",
            specs_json={},
            source="manufacturer_specs",
            as_of=datetime(2024, 1, 15).date(),
        )
        db_session.add(sku)
        await db_session.commit()
        await db_session.refresh(sku)

        # Create a unit
        unit = Unit(
            sku_id=sku.id,
            serial="GALAXY123",
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)

        # Create an inspection
        inspection = Inspection(
            unit_id=unit.id,
            battery_health_pct="90",
            cosmetic_grade="A",
            functional_tests_json={"display": True, "camera": True},
            activation_lock="none",
            accessories_json={"charger": True},
        )
        db_session.add(inspection)
        await db_session.commit()
        await db_session.refresh(inspection)

        # Create cost tables
        from secondroute.costs.models import CostTable, CostKind

        cost_rows = [
            CostTable(
                kind=CostKind.CHANNEL_FEE_PCT,
                key="RESELL_OPEN_BOX",
                value=0.12,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.CHANNEL_FEE_PCT,
                key="RESELL_REFURB",
                value=0.15,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.FIXED_FEE,
                key="RESELL_OPEN_BOX",
                value=2.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.FIXED_FEE,
                key="RESELL_REFURB",
                value=3.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.LOGISTICS_COST,
                key="RESELL_OPEN_BOX",
                value=8.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.LOGISTICS_COST,
                key="RESELL_REFURB",
                value=12.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.HANDLING_COST,
                key="RESELL_OPEN_BOX",
                value=5.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.HANDLING_COST,
                key="RESELL_REFURB",
                value=10.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.REPAIR_COST,
                key="RESELL_OPEN_BOX",
                value=0.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.REPAIR_COST,
                key="RESELL_REFURB",
                value=20.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.HOLDING_COST_PER_DAY,
                key="RESELL_OPEN_BOX",
                value=0.5,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.HOLDING_COST_PER_DAY,
                key="RESELL_REFURB",
                value=0.5,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.EXPECTED_DAYS_TO_SELL,
                key="RESELL_OPEN_BOX",
                value=7.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.EXPECTED_DAYS_TO_SELL,
                key="RESELL_REFURB",
                value=14.0,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.RESALE_RECOVERY_PCT,
                key="RESELL_OPEN_BOX",
                value=0.90,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
            CostTable(
                kind=CostKind.RESALE_RECOVERY_PCT,
                key="RESELL_REFURB",
                value=0.75,
                source="test",
                as_of=datetime(2024, 1, 15).date(),
            ),
        ]
        db_session.add_all(cost_rows)
        await db_session.commit()

        # Run decision with synthetic price source (unknown family uses default multiplier 1.0)
        price_source = SyntheticPriceSource(sku_family="Samsung Galaxy")
        risk_profile = "balanced"

        decision = await decide_unit(
            db_session,
            unit.id,
            price_source,
            risk_profile=risk_profile,
            seed=42,
        )

        # Verify a decision card is produced even for unknown family
        assert decision is not None
        assert decision.recommended_channel is not None
        assert decision.confidence >= 0.0
        assert decision.confidence <= 1.0
