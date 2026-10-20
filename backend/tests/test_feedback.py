"""
Tests for the audit log (Phase 1 - F1.7).
"""

import pytest
from datetime import date
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.identity.models import SKU
from secondroute.intake.models import Unit, Inspection, UnitStatus, ReturnReasonCode, OrderChannel
from secondroute.feedback.models import AuditLog, AuditAction


class TestAuditLog:
    """Tests for audit log functionality."""

    @pytest.mark.asyncio
    async def test_audit_log_on_unit_create(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test that creating a unit generates an audit log entry."""
        # Create a SKU first
        sku = SKU(
            family="Test",
            model_name="Model",
            year="2024",
            storage_gb="512",
            ram_gb="16",
            color="Black",
            region="US",
            specs_json={},
            source="test",
            as_of=date(2024, 1, 15),
        )
        db_session.add(sku)
        await db_session.commit()
        await db_session.refresh(sku)

        # Create unit via API
        unit_data = {
            "sku_id": str(sku.id),
            "serial": "TEST123",
            "return_reason_code": "buyer_remorse",
            "order_channel": "online",
        }
        response = await client.post("/api/v1/units", json=unit_data)
        assert response.status_code == 201
        unit_id = response.json()["id"]

        # Check audit log
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity == "units",
                AuditLog.entity_id == unit_id,
                AuditLog.action == AuditAction.CREATE,
            )
        )
        audit_log = result.scalar_one_or_none()

        assert audit_log is not None
        assert audit_log.entity == "units"
        assert audit_log.entity_id == unit_id
        assert audit_log.action == AuditAction.CREATE
        assert audit_log.actor == "anonymous"
        assert "data" in audit_log.payload_json
        assert audit_log.payload_json["data"]["serial"] == "TEST123"
        assert audit_log.payload_json["data"]["return_reason_code"] == "buyer_remorse"

    @pytest.mark.asyncio
    async def test_audit_log_on_unit_update(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test that updating a unit generates an audit log entry."""
        # Create SKU and unit
        sku = SKU(
            family="Test",
            model_name="Model",
            year="2024",
            storage_gb="512",
            ram_gb="16",
            color="Black",
            region="US",
            specs_json={},
            source="test",
            as_of=date(2024, 1, 15),
        )
        db_session.add(sku)
        await db_session.commit()
        await db_session.refresh(sku)

        unit = Unit(
            sku_id=sku.id,
            serial="TEST123",
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)

        # Update unit status via API
        response = await client.patch(f"/api/v1/units/{unit.id}/status", json={"status": "inspected"})
        assert response.status_code == 200

        # Check audit log
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity == "units",
                AuditLog.entity_id == str(unit.id),
                AuditLog.action == AuditAction.UPDATE,
            )
        )
        audit_log = result.scalar_one_or_none()

        assert audit_log is not None
        assert audit_log.action == AuditAction.UPDATE
        assert "changes" in audit_log.payload_json
        assert "status" in audit_log.payload_json["changes"]
        assert audit_log.payload_json["changes"]["status"]["before"] == "received"
        assert audit_log.payload_json["changes"]["status"]["after"] == "inspected"

    @pytest.mark.asyncio
    async def test_audit_log_on_inspection_create(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test that creating an inspection generates an audit log entry."""
        # Create SKU and unit
        sku = SKU(
            family="Test",
            model_name="Model",
            year="2024",
            storage_gb="512",
            ram_gb="16",
            color="Black",
            region="US",
            specs_json={},
            source="test",
            as_of=date(2024, 1, 15),
        )
        db_session.add(sku)
        await db_session.commit()
        await db_session.refresh(sku)

        unit = Unit(
            sku_id=sku.id,
            serial="TEST123",
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)

        # Create inspection via API
        inspection_data = {
            "battery_health_pct": "95",
            "cosmetic_grade": "A",
            "functional_tests_json": {"display": True},
            "activation_lock": "none",
            "accessories_json": {"charger": True},
        }
        response = await client.post(f"/api/v1/units/{unit.id}/inspections", json=inspection_data)
        assert response.status_code == 201
        inspection_id = response.json()["id"]

        # Check audit log
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity == "inspections",
                AuditLog.entity_id == inspection_id,
                AuditLog.action == AuditAction.CREATE,
            )
        )
        audit_log = result.scalar_one_or_none()

        assert audit_log is not None
        assert audit_log.entity == "inspections"
        assert audit_log.entity_id == inspection_id
        assert audit_log.action == AuditAction.CREATE
        assert "data" in audit_log.payload_json
        assert audit_log.payload_json["data"]["battery_health_pct"] == "95"
        assert audit_log.payload_json["data"]["cosmetic_grade"] == "A"

    @pytest.mark.asyncio
    async def test_audit_log_on_sku_create(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test that creating a SKU generates an audit log entry."""
        sku_data = {
            "family": "Test",
            "model_name": "Model",
            "year": "2024",
            "storage_gb": "512",
            "ram_gb": "16",
            "color": "Black",
            "region": "US",
            "specs_json": {},
            "source": "test",
            "as_of": "2024-01-15",
        }
        response = await client.post("/api/v1/skus", json=sku_data)
        assert response.status_code == 201
        sku_id = response.json()["id"]

        # Check audit log
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity == "skus",
                AuditLog.entity_id == sku_id,
                AuditLog.action == AuditAction.CREATE,
            )
        )
        audit_log = result.scalar_one_or_none()

        assert audit_log is not None
        assert audit_log.entity == "skus"
        assert audit_log.entity_id == sku_id
        assert audit_log.action == AuditAction.CREATE

    @pytest.mark.asyncio
    async def test_audit_log_list_endpoint(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test the audit log list endpoint."""
        # Create some audit entries
        sku = SKU(
            family="Test",
            model_name="Model",
            year="2024",
            storage_gb="512",
            ram_gb="16",
            color="Black",
            region="US",
            specs_json={},
            source="test",
            as_of=date(2024, 1, 15),
        )
        db_session.add(sku)
        await db_session.commit()
        await db_session.refresh(sku)

        unit = Unit(
            sku_id=sku.id,
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        db_session.add(unit)
        await db_session.commit()

        # List audit logs
        response = await client.get("/api/v1/audit-log")
        assert response.status_code == 200

        data = response.json()
        assert len(data) >= 2  # At least SKU create and Unit create

        # Check structure
        for log in data:
            assert "id" in log
            assert "entity" in log
            assert "entity_id" in log
            assert "action" in log
            assert "actor" in log
            assert "payload_json" in log
            assert "created_at" in log

    @pytest.mark.asyncio
    async def test_audit_log_filter_by_entity(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test filtering audit logs by entity."""
        response = await client.get("/api/v1/audit-log?entity=units")
        assert response.status_code == 200

        data = response.json()
        for log in data:
            assert log["entity"] == "units"

    @pytest.mark.asyncio
    async def test_audit_log_filter_by_action(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test filtering audit logs by action."""
        response = await client.get("/api/v1/audit-log?action=create")
        assert response.status_code == 200

        data = response.json()
        for log in data:
            assert log["action"] == "create"

    @pytest.mark.asyncio
    async def test_audit_log_get_by_id(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test getting a specific audit log entry by ID."""
        # Create a unit to generate an audit log
        sku = SKU(
            family="Test",
            model_name="Model",
            year="2024",
            storage_gb="512",
            ram_gb="16",
            color="Black",
            region="US",
            specs_json={},
            source="test",
            as_of=date(2024, 1, 15),
        )
        db_session.add(sku)
        await db_session.commit()
        await db_session.refresh(sku)

        unit = Unit(
            sku_id=sku.id,
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)

        # Get the audit log ID
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity == "units",
                AuditLog.entity_id == str(unit.id),
            )
        )
        audit_log = result.scalar_one_or_none()
        assert audit_log is not None

        # Fetch by ID
        response = await client.get(f"/api/v1/audit-log/{audit_log.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == str(audit_log.id)
        assert data["entity"] == "units"
        assert data["entity_id"] == str(unit.id)

    @pytest.mark.asyncio
    async def test_audit_log_no_update_for_no_change(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test that updating with same values doesn't create audit log."""
        # Create SKU and unit
        sku = SKU(
            family="Test",
            model_name="Model",
            year="2024",
            storage_gb="512",
            ram_gb="16",
            color="Black",
            region="US",
            specs_json={},
            source="test",
            as_of=date(2024, 1, 15),
        )
        db_session.add(sku)
        await db_session.commit()
        await db_session.refresh(sku)

        unit = Unit(
            sku_id=sku.id,
            serial="TEST123",
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)

        # Get initial audit log count
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity == "units",
                AuditLog.entity_id == str(unit.id),
            )
        )
        initial_count = len(result.scalars().all())

        # Update with same status (no actual change)
        await client.patch(f"/api/v1/units/{unit.id}/status", json={"status": "received"})

        # Check audit log count hasn't increased
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity == "units",
                AuditLog.entity_id == str(unit.id),
            )
        )
        final_count = len(result.scalars().all())

        assert final_count == initial_count  # No new audit log for no-op update