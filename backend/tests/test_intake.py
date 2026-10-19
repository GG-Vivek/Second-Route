"""
Tests for the unit intake and inspection record (Phase 1 - F1.3, F1.4, F1.5).
"""

import pytest
from datetime import datetime
from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.identity.models import SKU
from secondroute.intake.models import (
    Unit,
    Inspection,
    Photo,
    UnitStatus,
    ReturnReasonCode,
    OrderChannel,
)


class TestUnitIntake:
    """Tests for unit intake API (F1.3)."""

    @pytest.mark.asyncio
    async def test_create_unit(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test creating a new unit intake record."""
        # Create a SKU first
        sku = SKU(
            family="MacBook Pro",
            model_name="M3 Pro",
            year="2023",
            storage_gb="512",
            ram_gb="18",
            color="Space Gray",
            region="US",
            specs_json={},
            source="manufacturer_specs",
            as_of=datetime(2024, 1, 15).date(),
        )
        db_session.add(sku)
        await db_session.commit()
        await db_session.refresh(sku)

        unit_data = {
            "sku_id": str(sku.id),
            "serial": "C02XYZ123",
            "return_reason_code": "buyer_remorse",
            "order_channel": "online",
        }

        response = await client.post("/api/v1/units", json=unit_data)
        assert response.status_code == 201

        data = response.json()
        assert data["sku_id"] == str(sku.id)
        assert data["serial"] == "C02XYZ123"
        assert data["return_reason_code"] == "buyer_remorse"
        assert data["order_channel"] == "online"
        assert data["status"] == "received"
        assert "id" in data
        assert "received_at" in data

    @pytest.mark.asyncio
    async def test_create_unit_without_serial(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test creating a unit without serial number."""
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

        unit_data = {
            "sku_id": str(sku.id),
            "return_reason_code": "defective",
            "order_channel": "retail",
        }

        response = await client.post("/api/v1/units", json=unit_data)
        assert response.status_code == 201

        data = response.json()
        assert data["serial"] is None
        assert data["return_reason_code"] == "defective"
        assert data["status"] == "received"

    @pytest.mark.asyncio
    async def test_create_unit_invalid_sku_returns_404(self, client: AsyncClient) -> None:
        """Test that creating a unit with invalid SKU returns 404."""
        fake_id = uuid4()
        unit_data = {
            "sku_id": str(fake_id),
            "return_reason_code": "buyer_remorse",
            "order_channel": "online",
        }

        response = await client.post("/api/v1/units", json=unit_data)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_unit_invalid_reason_code_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that invalid return reason code returns 422."""
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

        unit_data = {
            "sku_id": str(sku.id),
            "return_reason_code": "invalid_reason",
            "order_channel": "online",
        }

        response = await client.post("/api/v1/units", json=unit_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_units(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test listing units."""
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

        # Create units
        unit1 = Unit(
            sku_id=sku.id,
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        unit2 = Unit(
            sku_id=sku.id,
            return_reason_code=ReturnReasonCode.DEFECTIVE,
            order_channel=OrderChannel.RETAIL,
        )
        db_session.add_all([unit1, unit2])
        await db_session.commit()

        response = await client.get("/api/v1/units")
        assert response.status_code == 200

        data = response.json()
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_list_units_with_status_filter(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test listing units with status filter."""
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

        unit1 = Unit(
            sku_id=sku.id,
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
            status=UnitStatus.RECEIVED,
        )
        unit2 = Unit(
            sku_id=sku.id,
            return_reason_code=ReturnReasonCode.DEFECTIVE,
            order_channel=OrderChannel.RETAIL,
            status=UnitStatus.INSPECTED,
        )
        db_session.add_all([unit1, unit2])
        await db_session.commit()

        response = await client.get("/api/v1/units?status=received")
        assert response.status_code == 200

        data = response.json()
        for unit in data:
            assert unit["status"] == "received"

    @pytest.mark.asyncio
    async def test_get_unit_detail(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test getting unit detail with inspections and photos."""
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
            sku_id=sku.id,
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)

        response = await client.get(f"/api/v1/units/{unit.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == str(unit.id)
        assert "inspections" in data
        assert "photos" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_unit_returns_404(self, client: AsyncClient) -> None:
        """Test getting a non-existent unit returns 404."""
        fake_id = uuid4()

        response = await client.get(f"/api/v1/units/{fake_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_unit_status(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test updating unit status."""
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
            sku_id=sku.id,
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)

        response = await client.patch(
            f"/api/v1/units/{unit.id}/status", json={"status": "inspected"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "inspected"
        assert data["id"] == str(unit.id)


class TestInspectionRecord:
    """Tests for inspection record API (F1.4)."""

    @pytest.mark.asyncio
    async def test_create_inspection(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test creating an inspection record."""
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
            sku_id=sku.id,
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)

        inspection_data = {
            "battery_health_pct": "95",
            "battery_cycles": "50",
            "cosmetic_grade": "A",
            "functional_tests_json": {"display": True, "keyboard": True, "ports": True},
            "activation_lock": "none",
            "accessories_json": {"charger": True, "box": False},
            "notes": "Excellent condition",
        }

        response = await client.post(f"/api/v1/units/{unit.id}/inspections", json=inspection_data)
        assert response.status_code == 201

        data = response.json()
        assert data["unit_id"] == str(unit.id)
        assert data["battery_health_pct"] == "95"
        assert data["cosmetic_grade"] == "A"
        assert data["activation_lock"] == "none"
        assert "id" in data
        assert "created_at" in data

        # Verify unit status changed to inspected
        unit_check = await db_session.get(Unit, unit.id)
        assert unit_check is not None
        assert unit_check.status == UnitStatus.INSPECTED

    @pytest.mark.asyncio
    async def test_create_inspection_battery_health_out_of_range(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that battery health outside 0-100 returns 422."""
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
            sku_id=sku.id,
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)

        inspection_data = {
            "battery_health_pct": "150",  # Invalid - over 100
            "cosmetic_grade": "A",
            "functional_tests_json": {},
            "activation_lock": "none",
            "accessories_json": {},
        }

        response = await client.post(f"/api/v1/units/{unit.id}/inspections", json=inspection_data)
        assert response.status_code == 422
        detail = response.json()["detail"]
        # FastAPI validation errors are a list
        if isinstance(detail, list):
            assert any("between 0 and 100" in str(e.get("msg", "")) for e in detail)
        else:
            assert "between 0 and 100" in str(detail)

    @pytest.mark.asyncio
    async def test_create_inspection_battery_health_negative(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that negative battery health returns 422."""
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
            sku_id=sku.id,
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)

        inspection_data = {
            "battery_health_pct": "-10",  # Invalid - negative
            "cosmetic_grade": "A",
            "functional_tests_json": {},
            "activation_lock": "none",
            "accessories_json": {},
        }

        response = await client.post(f"/api/v1/units/{unit.id}/inspections", json=inspection_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_inspection_nonexistent_unit_returns_404(
        self, client: AsyncClient
    ) -> None:
        """Test creating inspection for non-existent unit returns 404."""
        fake_id = uuid4()
        inspection_data = {
            "battery_health_pct": "95",
            "cosmetic_grade": "A",
            "functional_tests_json": {},
            "activation_lock": "none",
            "accessories_json": {},
        }

        response = await client.post(f"/api/v1/units/{fake_id}/inspections", json=inspection_data)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_multiple_inspections_append_only(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that multiple inspections are append-only and don't overwrite."""
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
            sku_id=sku.id,
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)

        # First inspection
        inspection1 = {
            "battery_health_pct": "95",
            "cosmetic_grade": "A",
            "functional_tests_json": {},
            "activation_lock": "none",
            "accessories_json": {},
        }
        response1 = await client.post(f"/api/v1/units/{unit.id}/inspections", json=inspection1)
        assert response1.status_code == 201
        inspection1_id = response1.json()["id"]

        # Second inspection
        inspection2 = {
            "battery_health_pct": "85",
            "cosmetic_grade": "B",
            "functional_tests_json": {},
            "activation_lock": "none",
            "accessories_json": {},
        }
        response2 = await client.post(f"/api/v1/units/{unit.id}/inspections", json=inspection2)
        assert response2.status_code == 201
        inspection2_id = response2.json()["id"]

        # List inspections - should have both
        response = await client.get(f"/api/v1/units/{unit.id}/inspections")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # First inspection should still exist
        ids = [i["id"] for i in data]
        assert inspection1_id in ids
        assert inspection2_id in ids
        # Ordered by created_at
        assert data[0]["id"] == inspection1_id
        assert data[1]["id"] == inspection2_id


class TestPhotoUpload:
    """Tests for photo upload records (F1.5 - metadata only)."""

    @pytest.mark.asyncio
    async def test_create_photo_record(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test creating a photo record."""
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
            sku_id=sku.id,
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
            functional_tests_json="{}",
            activation_lock="none",
            accessories_json="{}",
        )
        db_session.add(inspection)
        await db_session.commit()
        await db_session.refresh(inspection)

        photo_data = {
            "inspection_id": str(inspection.id),
            "storage_path": "/uploads/unit_123/photo_1.jpg",
            "exif_stripped": True,
        }

        response = await client.post(f"/api/v1/units/{unit.id}/photos", json=photo_data)
        assert response.status_code == 201

        data = response.json()
        assert data["unit_id"] == str(unit.id)
        assert data["inspection_id"] == str(inspection.id)
        assert data["storage_path"] == "/uploads/unit_123/photo_1.jpg"
        assert data["exif_stripped"] is True

    @pytest.mark.asyncio
    async def test_create_photo_nonexistent_unit_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test creating photo for non-existent unit returns 404."""
        fake_id = uuid4()
        photo_data = {
            "inspection_id": str(uuid4()),
            "storage_path": "/uploads/test.jpg",
            "exif_stripped": True,
        }

        response = await client.post(f"/api/v1/units/{fake_id}/photos", json=photo_data)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_photo_nonexistent_inspection_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test creating photo for non-existent inspection returns 404."""
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
            sku_id=sku.id,
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)

        photo_data = {
            "inspection_id": str(uuid4()),  # Non-existent inspection
            "storage_path": "/uploads/test.jpg",
            "exif_stripped": True,
        }

        response = await client.post(f"/api/v1/units/{unit.id}/photos", json=photo_data)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_photos(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test listing photos for a unit."""
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
            sku_id=sku.id,
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
            functional_tests_json="{}",
            activation_lock="none",
            accessories_json="{}",
        )
        db_session.add(inspection)
        await db_session.commit()
        await db_session.refresh(inspection)

        # Add photos
        photo1 = Photo(
            unit_id=unit.id,
            inspection_id=inspection.id,
            storage_path="/uploads/1.jpg",
            exif_stripped="true",
        )
        photo2 = Photo(
            unit_id=unit.id,
            inspection_id=inspection.id,
            storage_path="/uploads/2.jpg",
            exif_stripped="true",
        )
        db_session.add_all([photo1, photo2])
        await db_session.commit()

        response = await client.get(f"/api/v1/units/{unit.id}/photos")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2
