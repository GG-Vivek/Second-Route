"""
Tests for the SKU catalog and serial prefix lookup (Phase 1 - F1.1, F1.2).
"""

import pytest
from datetime import date
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.identity.models import SKU, SerialPrefix


class TestSKUCatalog:
    """Tests for SKU catalog CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_sku(self, client: AsyncClient) -> None:
        """Test creating a new SKU."""
        sku_data = {
            "family": "MacBook Pro",
            "model_name": "M3 Pro",
            "year": "2023",
            "storage_gb": "512",
            "ram_gb": "18",
            "color": "Space Gray",
            "region": "US",
            "specs_json": {"cpu": "Apple M3 Pro"},
            "source": "manufacturer_specs",
            "as_of": "2024-01-15",
        }

        response = await client.post("/api/v1/skus", json=sku_data)
        assert response.status_code == 201

        data = response.json()
        assert data["family"] == "MacBook Pro"
        assert data["model_name"] == "M3 Pro"
        assert data["storage_gb"] == "512"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_duplicate_sku_returns_409(self, client: AsyncClient) -> None:
        """Test that creating a duplicate SKU variant returns 409."""
        sku_data = {
            "family": "MacBook Pro",
            "model_name": "M3 Pro",
            "year": "2023",
            "storage_gb": "512",
            "ram_gb": "18",
            "color": "Space Gray",
            "region": "US",
            "specs_json": {},
            "source": "manufacturer_specs",
            "as_of": "2024-01-15",
        }

        # Create first
        response1 = await client.post("/api/v1/skus", json=sku_data)
        assert response1.status_code == 201

        # Create duplicate
        response2 = await client.post("/api/v1/skus", json=sku_data)
        assert response2.status_code == 409
        assert "already exists" in response2.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_skus(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test listing SKUs."""
        # Create test SKUs
        sku1 = SKU(
            family="MacBook Pro",
            model_name="M3 Pro",
            year="2023",
            storage_gb="512",
            ram_gb="18",
            color="Space Gray",
            region="US",
            specs_json={},
            source="manufacturer_specs",
            as_of=date(2024, 1, 15),
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
            source="manufacturer_specs",
            as_of=date(2024, 1, 15),
        )
        db_session.add_all([sku1, sku2])
        await db_session.commit()

        response = await client.get("/api/v1/skus")
        assert response.status_code == 200

        data = response.json()
        assert len(data) >= 2
        families = [s["family"] for s in data]
        assert "MacBook Pro" in families
        assert "MacBook Air" in families

    @pytest.mark.asyncio
    async def test_list_skus_with_family_filter(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test listing SKUs with family filter."""
        response = await client.get("/api/v1/skus?family=MacBook Pro")
        assert response.status_code == 200

        data = response.json()
        for sku in data:
            assert sku["family"] == "MacBook Pro"

    @pytest.mark.asyncio
    async def test_get_sku_by_id(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test getting a SKU by ID."""
        sku = SKU(
            family="Test Family",
            model_name="Test Model",
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

        response = await client.get(f"/api/v1/skus/{sku.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == str(sku.id)
        assert data["family"] == "Test Family"

    @pytest.mark.asyncio
    async def test_get_nonexistent_sku_returns_404(self, client: AsyncClient) -> None:
        """Test getting a non-existent SKU returns 404."""
        import uuid

        fake_id = uuid.uuid4()

        response = await client.get(f"/api/v1/skus/{fake_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestSerialPrefixLookup:
    """Tests for serial prefix to SKU lookup (F1.2)."""

    @pytest.mark.asyncio
    async def test_lookup_known_prefix(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test looking up a known serial prefix returns the SKU."""
        # Create SKU and prefix
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
            as_of=date(2024, 1, 15),
        )
        db_session.add(sku)
        await db_session.commit()
        await db_session.refresh(sku)

        prefix = SerialPrefix(
            prefix="C02",
            sku_id=sku.id,
            source="manufacturer_data",
            as_of=date(2024, 1, 15),
        )
        db_session.add(prefix)
        await db_session.commit()

        # Lookup
        response = await client.get("/api/v1/skus/lookup/serial?serial=C02XYZ123")
        assert response.status_code == 200

        data = response.json()
        assert data["matched_prefix"] == "C02"
        assert data["sku"]["family"] == "MacBook Pro"
        assert data["sku"]["model_name"] == "M3 Pro"

    @pytest.mark.asyncio
    async def test_lookup_longest_prefix_match(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that the longest matching prefix is used."""
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
            as_of=date(2024, 1, 15),
        )
        db_session.add(sku)
        await db_session.commit()
        await db_session.refresh(sku)

        # Add both short and long prefixes
        prefix_short = SerialPrefix(
            prefix="C0",
            sku_id=sku.id,
            source="test",
            as_of=date(2024, 1, 15),
        )
        prefix_long = SerialPrefix(
            prefix="C02",
            sku_id=sku.id,
            source="test",
            as_of=date(2024, 1, 15),
        )
        db_session.add_all([prefix_short, prefix_long])
        await db_session.commit()

        # Should match the longer prefix
        response = await client.get("/api/v1/skus/lookup/serial?serial=C02XYZ123")
        assert response.status_code == 200
        assert response.json()["matched_prefix"] == "C02"

    @pytest.mark.asyncio
    async def test_lookup_unknown_prefix_returns_404(self, client: AsyncClient) -> None:
        """Test that unknown serial prefix returns 404 with manual_selection_required."""
        response = await client.get("/api/v1/skus/lookup/serial?serial=UNKNOWN123")
        assert response.status_code == 404

        data = response.json()
        # FastAPI wraps HTTPException detail in {"detail": ...}
        detail = data.get("detail", data)
        assert detail["error"] == "manual_selection_required"
        assert "manual selection required" in detail["message"].lower()
        assert detail["serial"] == "UNKNOWN123"

    @pytest.mark.asyncio
    async def test_lookup_malformed_serial_returns_404(self, client: AsyncClient) -> None:
        """Test that malformed serial returns 404 (not 422)."""
        # Empty serial should be caught by validation
        response = await client.get("/api/v1/skus/lookup/serial?serial=")
        assert response.status_code == 422  # Validation error for empty string

        # Very short serial that won't match anything
        response = await client.get("/api/v1/skus/lookup/serial?serial=X")
        assert response.status_code == 404
        data = response.json()
        detail = data.get("detail", data)
        assert detail["error"] == "manual_selection_required"

    @pytest.mark.asyncio
    async def test_create_serial_prefix(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test creating a serial prefix mapping."""
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

        prefix_data = {
            "prefix": "ABC",
            "sku_id": str(sku.id),
            "source": "test_data",
            "as_of": "2024-01-15",
        }

        response = await client.post("/api/v1/skus/serial-prefixes", json=prefix_data)
        assert response.status_code == 201

        data = response.json()
        assert data["prefix"] == "ABC"
        assert data["sku_id"] == str(sku.id)

    @pytest.mark.asyncio
    async def test_create_duplicate_prefix_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that creating a duplicate prefix returns 409."""
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

        prefix_data = {
            "prefix": "DUP",
            "sku_id": str(sku.id),
            "source": "test",
            "as_of": "2024-01-15",
        }

        response1 = await client.post("/api/v1/skus/serial-prefixes", json=prefix_data)
        assert response1.status_code == 201

        response2 = await client.post("/api/v1/skus/serial-prefixes", json=prefix_data)
        assert response2.status_code == 409
        assert "already exists" in response2.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_prefix_for_nonexistent_sku_returns_404(self, client: AsyncClient) -> None:
        """Test that creating a prefix for non-existent SKU returns 404."""
        import uuid

        fake_id = uuid.uuid4()

        prefix_data = {
            "prefix": "NEW",
            "sku_id": str(fake_id),
            "source": "test",
            "as_of": "2024-01-15",
        }

        response = await client.post("/api/v1/skus/serial-prefixes", json=prefix_data)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestSeedData:
    """Tests for seed data loading."""

    @pytest.mark.asyncio
    async def test_seed_csv_loads_idempotently(self, db_session: AsyncSession) -> None:
        """Test that the seed CSV can be loaded twice without duplicates."""
        from scripts.load_skus import load_skus_from_csv
        from pathlib import Path

        # CSV is at project root /data/seeds/skus.csv
        csv_path = Path(__file__).parent.parent.parent / "data" / "seeds" / "skus.csv"

        # First load
        created1, skipped1 = await load_skus_from_csv(csv_path, db_session)
        assert created1 > 0
        assert skipped1 == 0

        # Second load
        created2, skipped2 = await load_skus_from_csv(csv_path, db_session)
        assert created2 == 0
        assert skipped2 == created1  # All skipped on second run

    @pytest.mark.asyncio
    async def test_all_seed_rows_have_source_and_as_of(self, db_session: AsyncSession) -> None:
        """Test that every seeded SKU has source and as_of fields."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))

        from scripts.load_skus import load_skus_from_csv

        # CSV is at project root /data/seeds/skus.csv
        csv_path = Path(__file__).parent.parent.parent / "data" / "seeds" / "skus.csv"
        await load_skus_from_csv(csv_path, db_session)

        result = await db_session.execute(select(SKU))
        skus = result.scalars().all()

        assert len(skus) > 0
        for sku in skus:
            assert sku.source is not None
            assert len(sku.source) > 0
            assert sku.as_of is not None
