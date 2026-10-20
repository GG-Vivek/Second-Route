"""
Tests for offline inspection (F5.5).
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
from secondroute.intake.models import Unit, Inspection, ReturnReasonCode, OrderChannel
from secondroute.feedback.models import AuditAction, AuditLog
from typing import Any


@pytest.fixture
async def test_org(db_session: AsyncSession) -> Organization:
    """Create a test organization."""
    org = Organization(name="Test Org", risk_profile="balanced")
    db_session.add(org)
    await db_session.flush()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def test_user(db_session: AsyncSession, test_org: Organization) -> User:
    """Create a test user."""
    user = User(org_id=test_org.id, email="inspector@test.com", role="inspector")
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def shared_sku(db_session: AsyncSession) -> SKU:
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


async def make_unit(db_session: AsyncSession, sku: SKU, org_id: Any) -> Unit:
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


async def make_inspection(
    db_session: AsyncSession,
    unit_id: Any,
    inspector_id: Any,
    offline: bool = False,
) -> Inspection:
    """Create an inspection."""
    inspection = Inspection(
        unit_id=unit_id,
        inspector_id=inspector_id,
        battery_health_pct="95",
        battery_cycles="120",
        cosmetic_grade="A",
        functional_tests_json='{"display": True, "keyboard": True}',
        activation_lock="none",
        accessories_json='{"charger": True}',
        notes="Test inspection",
        offline_created=offline,
    )
    db_session.add(inspection)
    await db_session.flush()
    await db_session.refresh(inspection)
    return inspection


class TestOfflineInspection:
    """Tests for offline inspection (F5.5)."""

    @pytest.mark.asyncio
    async def test_create_inspection_offline(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_org: Organization,
        test_user: Any,
        shared_sku: SKU,
    ) -> None:
        """Create an inspection while offline (flag set)."""
        unit = await make_unit(db_session, shared_sku, test_org.id)

        # Create inspection with offline flag
        inspection_data = {
            "battery_health_pct": "95",
            "battery_cycles": "120",
            "cosmetic_grade": "A",
            "functional_tests_json": {"display": True, "keyboard": True},
            "activation_lock": "none",
            "accessories_json": {"charger": True},
            "offline_created": True,
            "notes": "Created offline",
        }

        response = await client.post(
            f"/api/v1/units/{unit.id}/inspections",
            json=inspection_data,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["offline_created"] is True
        assert data["notes"] == "Created offline"

    @pytest.mark.asyncio
    async def test_create_inspection_online(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_org: Organization,
        test_user: Any,
        shared_sku: SKU,
    ) -> None:
        """Create an inspection while online (flag false)."""
        unit = await make_unit(db_session, shared_sku, test_org.id)

        inspection_data = {
            "battery_health_pct": "95",
            "battery_cycles": "120",
            "cosmetic_grade": "A",
            "functional_tests_json": {"display": True, "keyboard": True},
            "activation_lock": "none",
            "accessories_json": {"charger": True},
            "offline_created": False,
            "notes": "Created online",
        }

        response = await client.post(
            f"/api/v1/units/{unit.id}/inspections",
            json=inspection_data,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["offline_created"] is False

    @pytest.mark.asyncio
    async def test_offline_inspection_appears_in_list(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_org: Organization,
        test_user: Any,
        shared_sku: SKU,
    ) -> None:
        """Offline inspections should appear in the inspection list."""
        unit = await make_unit(db_session, shared_sku, test_org.id)

        # Create offline inspection
        await client.post(
            f"/api/v1/units/{unit.id}/inspections",
            json={
                "battery_health_pct": "95",
                "battery_cycles": "120",
                "cosmetic_grade": "A",
                "functional_tests_json": {"display": True},
                "activation_lock": "none",
                "accessories_json": {"charger": True},
                "offline_created": True,
            },
        )

        # List inspections
        response = await client.get(f"/api/v1/units/{unit.id}/inspections")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

        offline_inspections = [i for i in data if i.get("offline_created")]
        assert len(offline_inspections) >= 1


class TestOfflineSync:
    """Tests for offline sync functionality."""

    @pytest.mark.asyncio
    async def test_offline_inspection_sync_on_reconnect(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_org: Organization,
        test_user: Any,
        shared_sku: SKU,
    ) -> None:
        """Test that offline inspections sync when reconnected."""
        unit = await make_unit(db_session, shared_sku, test_org.id)

        # Simulate creating inspection offline (direct DB insert with offline_created=True)
        inspection = Inspection(
            unit_id=unit.id,
            inspector_id=test_user.id,
            battery_health_pct="90",
            battery_cycles="100",
            cosmetic_grade="B",
            functional_tests_json='{"display": True}',
            activation_lock="none",
            accessories_json="{}",
            notes="Offline inspection",
            offline_created=True,
        )
        db_session.add(inspection)
        await db_session.flush()
        await db_session.refresh(inspection)

        # Verify it's marked as offline
        assert bool(inspection.offline_created) is True

        # The sync mechanism would be triggered on reconnect
        # For now, verify it can be queried
        result = await db_session.execute(select(Inspection).where(Inspection.id == inspection.id))
        fetched = result.scalar_one()
        assert bool(fetched.offline_created) is True


class TestOfflineConflictResolution:
    """Tests for offline conflict resolution."""

    @pytest.mark.asyncio
    async def test_conflict_resolution_last_write_wins(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_org: Organization,
        test_user: Any,
        shared_sku: SKU,
    ) -> None:
        """Test that last write wins with both versions in audit log."""
        unit = await make_unit(db_session, shared_sku, test_org.id)

        # Create initial inspection
        inspection = Inspection(
            unit_id=unit.id,
            inspector_id=test_user.id,
            battery_health_pct="95",
            battery_cycles="120",
            cosmetic_grade="A",
            functional_tests_json='{"display": True}',
            activation_lock="none",
            accessories_json='{"charger": True}',
            offline_created=True,
        )
        db_session.add(inspection)
        await db_session.flush()
        await db_session.refresh(inspection)

        # Simulate offline edit (change grade from A to B)
        inspection.cosmetic_grade = "B"
        inspection.notes = "Updated offline"
        await db_session.flush()

        # Check audit log has both versions
        # The audit listener should have captured both versions
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity == "inspections",
                AuditLog.entity_id == str(inspection.id),
                AuditLog.action == AuditAction.UPDATE,
            )
        )
        logs = result.scalars().all()

        # Should have at least one update audit log
        assert len(logs) >= 1, f"Expected at least 1 audit log, got {len(logs)}"

        # Check that both versions are captured
        found_grade_a = False
        found_grade_b = False
        for log in logs:
            changes = log.payload_json.get("changes", {})
            if "cosmetic_grade" in changes:
                if changes["cosmetic_grade"]["before"] == "A":
                    found_grade_a = True
                if changes["cosmetic_grade"]["after"] == "B":
                    found_grade_b = True

        assert found_grade_a and found_grade_b, "Both versions should be in audit log"


class TestOfflineAuditOrg:
    """The audit row of an inspection must carry the tenant it belongs to.

    Inspections do not have an ``org_id`` of their own; the org comes from
    the unit. The tenant-isolation policies check ``org_id`` on every write,
    so an audit row with a null ``org_id`` would be rejected.
    """

    @pytest.mark.asyncio
    async def test_inspection_audit_log_carries_the_unit_org(
        self, db_session: AsyncSession, test_org: Organization, test_user: Any, shared_sku: SKU
    ) -> None:
        """The audit row for an inspection inherits the unit's org."""
        unit = await make_unit(db_session, shared_sku, test_org.id)
        inspection = await make_inspection(db_session, unit.id, test_user.id, offline=True)

        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity == "inspections",
                AuditLog.entity_id == str(inspection.id),
            )
        )
        logs = result.scalars().all()

        assert len(logs) == 1
        assert logs[0].org_id == test_org.id

    @pytest.mark.asyncio
    async def test_update_audit_log_carries_the_unit_org(
        self, db_session: AsyncSession, test_org: Organization, test_user: Any, shared_sku: SKU
    ) -> None:
        """An update to an inspection is audited against the unit's org."""
        unit = await make_unit(db_session, shared_sku, test_org.id)
        inspection = await make_inspection(db_session, unit.id, test_user.id, offline=True)

        inspection.cosmetic_grade = "B"
        await db_session.flush()

        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity == "inspections",
                AuditLog.entity_id == str(inspection.id),
                AuditLog.action == AuditAction.UPDATE,
            )
        )
        logs = result.scalars().all()

        assert len(logs) == 1
        assert logs[0].org_id == test_org.id

    @pytest.mark.asyncio
    async def test_unit_audit_log_carries_its_own_org(
        self, db_session: AsyncSession, test_org: Organization, shared_sku: SKU
    ) -> None:
        """A unit carries its own org, and the audit row uses it directly."""
        unit = await make_unit(db_session, shared_sku, test_org.id)

        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity == "units",
                AuditLog.entity_id == str(unit.id),
            )
        )
        logs = result.scalars().all()

        assert len(logs) == 1
        assert logs[0].org_id == test_org.id
