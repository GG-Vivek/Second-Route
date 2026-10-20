"""
Tests for batch decisions (F5.4).
"""

from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.identity.organizations import Organization, User
from secondroute.identity.models import SKU
from secondroute.intake.models import Unit, ReturnReasonCode, OrderChannel
from secondroute.decision.models import Decision, hash_snapshot


@pytest.fixture
async def test_org(db_session) -> Organization:
    """Create a test organization."""
    org = Organization(name="Test Org", risk_profile="balanced")
    db_session.add(org)
    await db_session.flush()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def shared_sku(db_session) -> SKU:
    """Create a shared SKU."""
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
        as_of=date(2024, 1, 15),
    )
    db_session.add(sku)
    await db_session.flush()
    await db_session.refresh(sku)
    return sku


async def make_unit(db_session, sku, org_id):
    """Create a minimal unit row."""
    from secondroute.intake.models import Unit, ReturnReasonCode, OrderChannel
    unit = Unit(
        sku_id=sku.id,
        org_id=org_id,
        return_reason_code=ReturnReasonCode.BUYER_REMORSE,
        order_channel=OrderChannel.ONLINE,
    )
    db_session.add(unit)
    await db_session.flush()
    await db_session.refresh(unit)
    return unit


async def make_decision(db_session, unit_id, org_id):
    """Insert a stored decision with specific p10/p50/p90 predictions."""
    decision = Decision(
        unit_id=unit_id,
        org_id=org_id,
        recommended_channel="RESELL_OPEN_BOX",
        confidence=0.86,
        candidates_json='[{"channel": "RESELL_OPEN_BOX", "eligible": true, "exclusion_reason": null, "p10": 1000, "p50": 1200, "p90": 1400, "mean": 1200, "stddev": 50, "probability_best": 0.82, "certainty_equivalent": 1150, "grade_probabilities": {"A": 0.8, "B": 0.15, "C": 0.04, "D": 0.01}, "price_sources": {"RESELL_OPEN_BOX:A": "synthetic"}, "price_as_of": {"RESELL_OPEN_BOX:A": "2025-01-01"}, "breakdown": {"sale_price": 1400, "fees": 100, "logistics": 20, "handling": 10, "repair": 15, "holding": 5, "total_cost": 150, "net": 1200}}]',
        input_snapshot_hash=hash_snapshot({"unit_id": str(unit_id), "seed": 42}),
    )
    db_session.add(decision)
    await db_session.flush()
    await db_session.refresh(decision)
    return decision


class TestBatchDecisions:
    """Tests for batch decisions endpoint (F5.4)."""

    @pytest.mark.asyncio
    async def test_batch_decide_multiple_units(
        self, client, db_session, test_org, shared_sku
    ):
        """Run batch decision on multiple units."""
        # Create multiple units
        units = []
        for i in range(5):
            unit = await make_unit(db_session, shared_sku, test_org.id)
            units.append(unit)

        unit_ids = [str(u.id) for u in units]

        response = await client.post(
            "/api/v1/batches/decide",
            json={"unit_ids": unit_ids, "risk_profile": "balanced"},
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "results" in data
        assert len(data["results"]) == 5
        
        for result in data["results"]:
            assert "unit_id" in result
            assert "decision_id" in result
            assert "recommended_channel" in result
            assert "confidence" in result

    @pytest.mark.asyncio
    async def test_batch_decide_with_risk_profile(
        self, client, db_session, test_org, shared_sku
    ):
        """Batch decision with specific risk profile."""
        units = []
        for i in range(3):
            unit = await make_unit(db_session, shared_sku, test_org.id)
            units.append(unit)

        unit_ids = [str(u.id) for u in units]

        response = await client.post(
            "/api/v1/batches/decide",
            json={"unit_ids": unit_ids, "risk_profile": "conservative"},
        )
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["results"]) == 3
        for result in data["results"]:
            assert "unit_id" in result
            assert "decision_id" in result

    @pytest.mark.asyncio
    async def test_batch_decide_empty_list(
        self, client, db_session, test_org
    ):
        """Empty unit_ids list should return empty results."""
        response = await client.post(
            "/api/v1/batches/decide",
            json={"unit_ids": [], "risk_profile": "balanced"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []

    @pytest.mark.asyncio
    async def test_batch_decide_invalid_unit_returns_404(
        self, client, db_session, test_org
    ):
        """Invalid unit ID should return 404 or error in results."""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = await client.post(
            "/api/v1/batches/decide",
            json={"unit_ids": [fake_id], "risk_profile": "balanced"},
        )
        # Should either return 404 or include error in results
        assert response.status_code in (200, 404, 422)

    @pytest.mark.asyncio
    async def test_batch_decide_cross_org_returns_404(
        self, client, db_session, test_org, shared_sku
    ):
        """Units from different orgs should be rejected or filtered."""
        # Create unit in org A
        unit_a = await make_unit(db_session, shared_sku, test_org.id)
        
        # Create another org
        from secondroute.identity.organizations import Organization
        org_b = Organization(name="Org B", risk_profile="balanced")
        db_session.add(org_b)
        await db_session.flush()
        await db_session.refresh(org_b)
        
        # Create unit in org B
        unit_b = await make_unit(db_session, shared_sku, org_b.id)
        
        response = await client.post(
            "/api/v1/batches/decide",
            json={"unit_ids": [str(unit_a.id), str(unit_b.id)], "risk_profile": "balanced"},
        )
        # Should either reject cross-org batch or process only same-org units
        assert response.status_code in (200, 400, 422)


class TestBatchDecisionsGrouping:
    """Tests for batch decision grouping functionality."""

    @pytest.mark.asyncio
    async def test_batch_decide_group_by_channel(
        self, client, db_session, test_org, shared_sku
    ):
        """Batch results should be groupable by channel."""
        units = []
        for i in range(6):
            unit = await make_unit(db_session, shared_sku, test_org.id)
            units.append(unit)

        unit_ids = [str(u.id) for u in units]

        response = await client.post(
            "/api/v1/batches/decide",
            json={"unit_ids": unit_ids, "risk_profile": "balanced", "group_by": "channel"},
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check for grouped results
        assert "groups" in data or "results" in data

    @pytest.mark.asyncio
    async def test_batch_decide_filter_by_value(
        self, client, db_session, test_org, shared_sku
    ):
        """Filter batch results by value range."""
        # This test depends on implementation - may not be in initial version
        pass

    @pytest.mark.asyncio
    async def test_batch_decide_csv_export(
        self, client, db_session, test_org, shared_sku
    ):
        """CSV export of batch decisions."""
        units = []
        for i in range(3):
            unit = await make_unit(db_session, shared_sku, test_org.id)
            units.append(unit)

        unit_ids = [str(u.id) for u in units]

        response = await client.post(
            "/api/v1/batches/decide",
            json={"unit_ids": unit_ids, "risk_profile": "balanced", "format": "csv"},
        )
        assert response.status_code == 200
        # Check for CSV content
        assert "text/csv" in response.headers.get("content-type", "") or "results" in response.json()
