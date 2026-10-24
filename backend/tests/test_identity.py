"""
Tests for the SKU catalog and serial prefix lookup (Phase 1 - F1.1, F1.2).
"""

import pytest
from datetime import date
from httpx import AsyncClient
from pathlib import Path
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
        first = await load_skus_from_csv(csv_path, db_session)
        assert first.created > 0
        assert first.skipped == 0

        # Second load
        second = await load_skus_from_csv(csv_path, db_session)
        assert second.created == 0
        assert second.updated == 0  # Nothing to bring forward
        assert second.skipped == first.created  # All skipped on second run

    @pytest.mark.asyncio
    async def test_a_row_the_catalogue_changed_is_refreshed(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """A row that already exists is brought back to what the CSV says.

        The catalogue is the CSV. A loader that only ever inserts leaves the
        database saying something the catalogue no longer says -- the row
        keeps the summary, and the category, it was born with.
        """
        from scripts.load_skus import load_skus_from_csv

        csv_path = tmp_path / "skus.csv"
        csv_path.write_text(
            "family,model_name,year,storage_gb,ram_gb,color,region,specs_json,source,as_of\n"
            'TestTV,55-inch,2024,,,Black,US,"{""summary"": ""first thought""}",'
            "manufacturer_specs,2024-01-15\n",
            encoding="utf-8",
        )
        first = await load_skus_from_csv(csv_path, db_session)
        assert first.created == 1

        csv_path.write_text(
            "family,model_name,year,storage_gb,ram_gb,color,region,specs_json,source,as_of\n"
            'TestTV,55-inch,2024,,,Black,US,"{""summary"": ""second thought"",'
            ' ""category"": ""tv""}",manufacturer_specs,2025-06-01\n',
            encoding="utf-8",
        )
        second = await load_skus_from_csv(csv_path, db_session)

        assert second.created == 0
        assert second.updated == 1
        assert second.skipped == 0

        result = await db_session.execute(select(SKU))
        sku = result.scalars().one()
        assert sku.specs_json["category"] == "tv"
        assert sku.specs_json["summary"] == "second thought"
        assert sku.source == "manufacturer_specs"
        assert sku.as_of == date(2025, 6, 1)

    @pytest.mark.asyncio
    async def test_a_row_the_catalogue_dropped_goes_away(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """A row nothing needs any more is removed with the catalogue's edit.

        Deleting a row from the CSV is how the catalogue says "this stopped
        being sold". Keeping it would show the shop a product the catalogue
        has retired.
        """
        from scripts.load_skus import load_skus_from_csv

        csv_path = tmp_path / "skus.csv"
        header = "family,model_name,year,storage_gb,ram_gb,color,region,specs_json,source,as_of\n"
        row = '{family},{model},2024,,,Black,US,"{{""summary"": ""a device""}}",manufacturer_specs,2024-01-15\n'

        csv_path.write_text(header + row.format(family="Retired", model="Model"), encoding="utf-8")
        await load_skus_from_csv(csv_path, db_session)

        csv_path.write_text(header + row.format(family="Current", model="Model"), encoding="utf-8")
        second = await load_skus_from_csv(csv_path, db_session)

        assert second.created == 1
        assert second.removed == 1

        result = await db_session.execute(select(SKU))
        assert {sku.family for sku in result.scalars().all()} == {"Current"}

    @pytest.mark.asyncio
    async def test_a_dropped_row_with_units_behind_it_is_kept(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """A retired row that still has a unit against it is not removed.

        The unit's unit is a record of what came back. Removing its product
        out from under it would leave an inspection of nothing.
        """
        from datetime import UTC, datetime

        from scripts.load_skus import load_skus_from_csv
        from secondroute.intake.models import OrderChannel, ReturnReasonCode, Unit

        csv_path = tmp_path / "skus.csv"
        header = "family,model_name,year,storage_gb,ram_gb,color,region,specs_json,source,as_of\n"
        csv_path.write_text(
            header + 'Retired,Model,2024,,,Black,US,"{""summary"": ""a device""}",'
            "manufacturer_specs,2024-01-15\n",
            encoding="utf-8",
        )
        await load_skus_from_csv(csv_path, db_session)

        result = await db_session.execute(select(SKU))
        sku = result.scalars().one()
        db_session.add(
            Unit(
                sku_id=sku.id,
                serial="KEEPME",
                received_at=datetime.now(UTC),
                return_reason_code=ReturnReasonCode.BUYER_REMORSE,
                order_channel=OrderChannel.ONLINE,
            )
        )
        await db_session.commit()

        csv_path.write_text(
            header + 'Current,Model,2024,,,Black,US,"{""summary"": ""a device""}",'
            "manufacturer_specs,2024-01-15\n",
            encoding="utf-8",
        )
        second = await load_skus_from_csv(csv_path, db_session)

        assert second.created == 1
        assert second.removed == 0
        assert second.retained == 1

        result = await db_session.execute(select(SKU))
        families = {row.family for row in result.scalars().all()}
        assert families == {"Retired", "Current"}

    @pytest.mark.asyncio
    async def test_a_delete_of_a_product_in_use_is_refused_by_the_database(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """The delete asks the database, and takes no for an answer.

        In production the tenant policies hide other organisations' rows
        from the reference check, so the delete is what really decides. Its
        refusal has to land as "retained" rather than as a broken
        transaction: the rest of the load still has to run.
        """
        from sqlalchemy import text

        from scripts.load_skus import _remove_retired, load_skus_from_csv
        from secondroute.intake.models import OrderChannel, ReturnReasonCode, Unit

        csv_path = tmp_path / "skus.csv"
        csv_path.write_text(
            "family,model_name,year,storage_gb,ram_gb,color,region,specs_json,source,as_of\n"
            'Retired,Model,2024,,,Black,US,"{""summary"": ""a device""}",'
            "manufacturer_specs,2024-01-15\n",
            encoding="utf-8",
        )
        await load_skus_from_csv(csv_path, db_session)

        result = await db_session.execute(select(SKU))
        sku = result.scalars().one()
        db_session.add(
            Unit(
                sku_id=sku.id,
                serial="KEEPME",
                return_reason_code=ReturnReasonCode.BUYER_REMORSE,
                order_channel=OrderChannel.ONLINE,
            )
        )
        await db_session.commit()

        # SQLite does not enforce foreign keys until asked. The
        # enforcement is what makes this test the same test the database
        # runs in production.
        await db_session.execute(text("PRAGMA foreign_keys=ON"))

        assert await _remove_retired(db_session, sku) is False

        # The savepoint caught it, so the transaction is still usable.
        result = await db_session.execute(select(SKU))
        assert [row.family for row in result.scalars().all()] == ["Retired"]

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
