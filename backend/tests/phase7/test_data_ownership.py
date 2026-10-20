"""
Tests for data ownership tools (Phase 7 - F7.6).
"""

import pytest
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.identity.models import SKU
from secondroute.intake.models import Unit, Inspection, ReturnReasonCode, OrderChannel
from secondroute.feedback.models import AuditLog
from secondroute.ownership import (
    DataOwnershipService,
    DataExport,
    DeletionRecord,
)


class TestDataExport:
    """Tests for the DataExport class."""

    def test_empty_export(self) -> None:
        """Test an export with no tables."""
        export = DataExport(org_id=uuid4())
        assert export.row_count == 0
        assert export.to_csv("units") == ""
        assert export.to_csv_bundle() == {}

    def test_add_table(self) -> None:
        """Test adding rows to a table."""
        export = DataExport(org_id=uuid4())
        export.add_table("units", [{"id": "1", "serial": "ABC"}])
        export.add_table("photos", [{"id": "2"}])

        assert export.row_count == 2
        assert len(export.tables) == 2

    def test_to_json(self) -> None:
        """Test JSON serialization."""
        import json

        export = DataExport(org_id=uuid4())
        export.add_table("units", [{"id": "1", "serial": "ABC"}])

        data = json.loads(export.to_json())
        assert data["row_count"] == 1
        assert "units" in data["tables"]

    def test_to_csv(self) -> None:
        """Test CSV serialization."""
        export = DataExport(org_id=uuid4())
        export.add_table(
            "units",
            [
                {"id": "1", "serial": "ABC", "value": 10},
                {"id": "2", "serial": "DEF", "value": 20},
            ],
        )

        csv_text = export.to_csv("units")
        lines = csv_text.strip().split("\n")
        assert len(lines) == 3  # header + 2 rows
        assert "id,serial,value" in lines[0]
        assert "1,ABC,10" in lines[1]

    def test_to_csv_bundle(self) -> None:
        """Test CSV bundle serialization."""
        export = DataExport(org_id=uuid4())
        export.add_table("units", [{"id": "1"}])
        export.add_table("photos", [{"id": "2"}])

        bundle = export.to_csv_bundle()
        assert len(bundle) == 2
        assert "units" in bundle
        assert "photos" in bundle


class TestDataOwnershipService:
    """Tests for the DataOwnershipService."""

    @pytest.fixture
    def service(self) -> DataOwnershipService:
        return DataOwnershipService()

    @pytest.mark.asyncio
    async def test_export_empty_tenant(
        self, service: DataOwnershipService, db_session: AsyncSession
    ) -> None:
        """Test exporting a tenant with no data."""
        export = await service.export_tenant_data(db_session, uuid4())
        assert export.row_count == 0

    @pytest.mark.asyncio
    async def test_export_tenant_data(
        self, service: DataOwnershipService, db_session: AsyncSession
    ) -> None:
        """Test exporting a tenant's data."""
        from secondroute.identity.organizations import Organization

        org = Organization(name="Test Org", risk_profile="balanced")
        db_session.add(org)
        await db_session.commit()
        await db_session.refresh(org)

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
            as_of=datetime(2024, 1, 15).date(),
        )
        db_session.add(sku)
        await db_session.commit()
        await db_session.refresh(sku)

        unit = Unit(
            org_id=org.id,
            sku_id=sku.id,
            serial="TEST123",
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)

        inspection = Inspection(
            unit_id=unit.id,
            battery_health_pct="95",
            cosmetic_grade="A",
            functional_tests_json={"display": True},
            activation_lock="none",
            accessories_json={"charger": True},
        )
        db_session.add(inspection)
        await db_session.commit()

        export = await service.export_tenant_data(db_session, org.id)

        assert export.row_count > 0
        assert "units" in export.tables
        assert len(export.tables["units"]) == 1
        assert export.tables["units"][0]["serial"] == "TEST123"

    @pytest.mark.asyncio
    async def test_delete_tenant_data(
        self, service: DataOwnershipService, db_session: AsyncSession
    ) -> None:
        """Test deleting a tenant's data."""
        from secondroute.identity.organizations import Organization

        org = Organization(name="Delete Me", risk_profile="balanced")
        db_session.add(org)
        await db_session.commit()
        await db_session.refresh(org)

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
            as_of=datetime(2024, 1, 15).date(),
        )
        db_session.add(sku)
        await db_session.commit()
        await db_session.refresh(sku)

        unit = Unit(
            org_id=org.id,
            sku_id=sku.id,
            serial="DELETE_ME",
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)

        inspection = Inspection(
            unit_id=unit.id,
            battery_health_pct="90",
            cosmetic_grade="B",
            functional_tests_json={},
            activation_lock="none",
            accessories_json={},
        )
        db_session.add(inspection)
        await db_session.commit()

        record = await service.delete_tenant_data(
            db_session,
            org.id,
            deleted_by="admin@example.com",
            reason="Contract ended",
        )

        assert isinstance(record, DeletionRecord)
        assert record.org_id == org.id
        assert record.units_deleted == 1
        assert record.inspections_deleted == 1
        assert record.total_rows_deleted >= 2
        assert record.deleted_by == "admin@example.com"
        assert record.reason == "Contract ended"

        # Verify the rows are gone
        result = await db_session.execute(select(Unit).where(Unit.org_id == org.id))
        assert len(result.scalars().all()) == 0

    @pytest.mark.asyncio
    async def test_deletion_leaves_audit_record(
        self, service: DataOwnershipService, db_session: AsyncSession
    ) -> None:
        """Test that a deletion leaves an audit record."""
        from secondroute.identity.organizations import Organization

        org = Organization(name="Audited", risk_profile="balanced")
        db_session.add(org)
        await db_session.commit()
        await db_session.refresh(org)

        record = await service.delete_tenant_data(
            db_session,
            org.id,
            deleted_by="admin@example.com",
            reason="GDPR request",
        )

        records = service.get_deletion_records(org.id)
        assert len(records) == 1
        assert records[0].reason == "GDPR request"
        assert records[0].deleted_by == "admin@example.com"
        assert record.org_id == org.id

    @pytest.mark.asyncio
    async def test_deletion_records_filtered(
        self, service: DataOwnershipService, db_session: AsyncSession
    ) -> None:
        """Test filtering deletion records by tenant."""
        org_a = uuid4()
        org_b = uuid4()

        await service.delete_tenant_data(db_session, org_a, reason="A")
        await service.delete_tenant_data(db_session, org_b, reason="B")

        assert len(service.get_deletion_records()) == 2
        assert len(service.get_deletion_records(org_a)) == 1
        assert service.get_deletion_records(org_a)[0].reason == "A"

    @pytest.mark.asyncio
    async def test_delete_leaves_other_tenant_intact(
        self, service: DataOwnershipService, db_session: AsyncSession
    ) -> None:
        """Test that deleting one tenant leaves another intact."""
        from secondroute.identity.organizations import Organization

        org_a = Organization(name="Keep A", risk_profile="balanced")
        org_b = Organization(name="Delete B", risk_profile="balanced")
        db_session.add_all([org_a, org_b])
        await db_session.commit()
        await db_session.refresh(org_a)
        await db_session.refresh(org_b)

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
            as_of=datetime(2024, 1, 15).date(),
        )
        db_session.add(sku)
        await db_session.commit()
        await db_session.refresh(sku)

        unit_a = Unit(
            org_id=org_a.id,
            sku_id=sku.id,
            serial="KEEP_ME",
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        unit_b = Unit(
            org_id=org_b.id,
            sku_id=sku.id,
            serial="DELETE_ME",
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        db_session.add_all([unit_a, unit_b])
        await db_session.commit()

        await service.delete_tenant_data(db_session, org_b.id, reason="cleanup")

        # Org A's unit survives
        result = await db_session.execute(select(Unit).where(Unit.org_id == org_a.id))
        assert len(result.scalars().all()) == 1

        # Org B's unit is gone
        result = await db_session.execute(select(Unit).where(Unit.org_id == org_b.id))
        assert len(result.scalars().all()) == 0

    @pytest.mark.asyncio
    async def test_delete_removes_audit_logs(
        self, service: DataOwnershipService, db_session: AsyncSession
    ) -> None:
        """Test that tenant audit logs are removed with the tenant data."""
        from secondroute.identity.organizations import Organization

        org = Organization(name="With Logs", risk_profile="balanced")
        db_session.add(org)
        await db_session.commit()
        await db_session.refresh(org)

        audit_log = AuditLog(
            org_id=org.id,
            actor="anonymous",
            action="create",
            entity="units",
            entity_id=str(uuid4()),
            payload_json={"data": {}},
        )
        db_session.add(audit_log)
        await db_session.commit()

        record = await service.delete_tenant_data(db_session, org.id, reason="cleanup")

        assert record.audit_logs_deleted == 1

        result = await db_session.execute(select(AuditLog).where(AuditLog.org_id == org.id))
        assert len(result.scalars().all()) == 0
