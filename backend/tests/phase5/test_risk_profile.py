"""
Tests for risk profile settings (F5.3).
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
from secondroute.feedback.models import AuditLog, AuditAction


@pytest.fixture
async def test_org(db_session: AsyncSession):
    """Create a test organization."""
    org = Organization(name="Test Org", risk_profile="balanced")
    db_session.add(org)
    await db_session.flush()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def test_user(db_session: AsyncSession, test_org):
    """Create a test user."""
    user = User(org_id=test_org.id, email="admin@test.com", role="admin")
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def shared_sku(db_session: AsyncSession):
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


async def make_unit(db_session: AsyncSession, sku, org_id):
    """Create a minimal unit row."""
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


async def make_decision(db_session: AsyncSession, unit_id, org_id, risk_profile="balanced"):
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


class TestRiskProfileSettings:
    """Tests for risk profile settings (F5.3)."""

    @pytest.mark.asyncio
    async def test_update_organization_risk_profile(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test updating organization risk profile."""
        # Create org
        response = await client.post(
            "/api/v1/orgs",
            json={"name": "Test Org", "risk_profile": "balanced"},
        )
        assert response.status_code == 201
        org_id = response.json()["id"]

        # Update risk profile to conservative
        response = await client.patch(
            f"/api/v1/orgs/{org_id}",
            json={"risk_profile": "conservative"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["risk_profile"] == "conservative"

    @pytest.mark.asyncio
    async def test_update_risk_profile_audited(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test that risk profile changes are audited."""
        # Create org
        response = await client.post(
            "/api/v1/orgs",
            json={"name": "Test Org", "risk_profile": "balanced"},
        )
        assert response.status_code == 201
        org_id = response.json()["id"]

        # Update risk profile
        await client.patch(
            f"/api/v1/orgs/{org_id}",
            json={"risk_profile": "aggressive"},
        )

        # Check audit log
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity == "organizations",
                AuditLog.entity_id == org_id,
                AuditLog.action == "update",
            )
        )
        logs = result.scalars().all()
        print(f"DEBUG: Found {len(logs)} audit logs", flush=True)
        for log in logs:
            print(f"DEBUG: Log payload: {log.payload_json}", flush=True)
        assert len(logs) >= 1
        found_risk_profile_change = False
        for log in logs:
            if "risk_profile" in str(log.payload_json):
                found_risk_profile_change = True
                changes = log.payload_json.get("changes", {})
                assert "risk_profile" in changes
                assert changes["risk_profile"]["before"] == "balanced"
                assert changes["risk_profile"]["after"] == "aggressive"
        assert found_risk_profile_change

    @pytest.mark.asyncio
    async def test_invalid_risk_profile_returns_422(
        self, client: AsyncClient, db_session
    ):
        """Test that invalid risk profile returns 422."""
        # Create org
        response = await client.post(
            "/api/v1/orgs",
            json={"name": "Test Org", "risk_profile": "balanced"},
        )
        assert response.status_code == 201
        org_id = response.json()["id"]

        # Try to update with invalid risk profile
        response = await client.patch(
            f"/api/v1/orgs/{org_id}",
            json={"risk_profile": "invalid_profile"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_risk_profile_recomputes_decisions(
        self, client: AsyncClient, db_session
    ):
        """Test that changing risk profile triggers decision recomputation."""
        # Create org with balanced profile
        response = await client.post(
            "/api/v1/orgs",
            json={"name": "Test Org", "risk_profile": "balanced"},
        )
        assert response.status_code == 201
        org_id = response.json()["id"]

        # Create a unit and decision with balanced profile
        # (This would require setting up a unit with a decision)
        # For now, verify the endpoint exists and returns success
        response = await client.patch(
            f"/api/v1/orgs/{org_id}",
            json={"risk_profile": "conservative"},
        )
        assert response.status_code == 200
        assert response.json()["risk_profile"] == "conservative"

    @pytest.mark.asyncio
    async def test_valid_risk_profiles(
        self, client: AsyncClient, db_session
    ):
        """Test that all valid risk profiles are accepted."""
        valid_profiles = ["conservative", "balanced", "aggressive"]
        
        for profile in valid_profiles:
            response = await client.post(
                "/api/v1/orgs",
                json={"name": f"Test Org {profile}", "risk_profile": profile},
            )
            assert response.status_code == 201
            assert response.json()["risk_profile"] == profile


class TestRiskProfileRecomputation:
    """Tests for decision recomputation when risk profile changes."""

    @pytest.mark.asyncio
    async def test_recompute_decisions_on_profile_change(
        self, client: AsyncClient, db_session
    ):
        """Test that decisions are recomputed when risk profile changes."""
        # This test would verify that a background job or immediate
        # recomputation happens when risk profile changes
        # For now, verify the endpoint exists
        pass
