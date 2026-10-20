"""
Tests for the partner sold-data CSV import (F3.2).
"""

from __future__ import annotations

import csv
import io
import json
from datetime import date
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.identity.models import SKU
from secondroute.ingest.models import ImportFile
from secondroute.ingest.sales import (
    auto_detect_mapping,
    file_hash,
    import_sales,
    parse_sales_csv,
    preview_sales_file,
)
from secondroute.ingest.schemas import ColumnMapping
from secondroute.pricing.models import PriceObservation

HEADER = "sku_id,grade,channel,price,sold_at\n"


def build_csv(rows: list[str], header: str = HEADER) -> bytes:
    """Build a sales CSV from raw data rows."""
    return (header + "\n".join(rows) + "\n").encode("utf-8")


async def make_sku(
    session: AsyncSession,
    *,
    family: str = "MacBook Pro",
    model_name: str = "M3 Pro",
) -> SKU:
    """Create a SKU for the tests."""
    sku = SKU(
        family=family,
        model_name=model_name,
        year="2023",
        storage_gb="512",
        ram_gb="18",
        color="Space Gray",
        region="US",
        specs_json={},
        source="test",
        as_of=date(2025, 1, 15),
    )
    session.add(sku)
    await session.flush()
    await session.refresh(sku)
    return sku


class TestAutoDetection:
    """The mapping step works out the columns on its own."""

    def test_detects_the_common_headers(self) -> None:
        """The usual partner headers are detected."""
        mapping = auto_detect_mapping(
            ["sku_id", "grade", "channel", "price", "sold_at", "quantity"]
        )
        assert mapping is not None
        assert mapping.sku == "sku_id"
        assert mapping.grade == "grade"
        assert mapping.channel == "channel"
        assert mapping.price == "price"
        assert mapping.sold_at == "sold_at"
        assert mapping.quantity == "quantity"

    def test_detects_alternative_headers(self) -> None:
        """Alternative names are detected too."""
        mapping = auto_detect_mapping(
            ["Product SKU", "Item Condition", "Sales Channel", "Amount", "Date"]
        )
        assert mapping is not None
        assert mapping.sku == "Product SKU"
        assert mapping.grade == "Item Condition"
        assert mapping.channel == "Sales Channel"
        assert mapping.price == "Amount"
        assert mapping.sold_at == "Date"

    def test_missing_column_gives_no_mapping(self) -> None:
        """A partial match is not a usable mapping."""
        mapping = auto_detect_mapping(["sku_id", "grade", "price"])
        assert mapping is None

    def test_quantity_is_optional(self) -> None:
        """The quantity column is optional."""
        mapping = auto_detect_mapping(["sku_id", "grade", "channel", "price", "sold_at"])
        assert mapping is not None
        assert mapping.quantity is None


class TestPreview:
    """The preview describes the file without touching the database."""

    def test_preview_reports_the_columns(self) -> None:
        """The columns come back."""
        content = build_csv(["abc, A, RESELL_OPEN_BOX, 100, 2025-05-01"])
        preview = preview_sales_file(content, "sales.csv")
        assert preview.columns == ["sku_id", "grade", "channel", "price", "sold_at"]
        assert preview.row_count == 1
        assert preview.filename == "sales.csv"
        assert preview.file_hash == file_hash(content)

    def test_preview_suggests_a_mapping(self) -> None:
        """The suggested mapping is present when the file is well formed."""
        content = build_csv(["abc, A, RESELL_OPEN_BOX, 100, 2025-05-01"])
        preview = preview_sales_file(content, "sales.csv")
        assert preview.suggested_mapping is not None
        assert preview.suggested_mapping.price == "price"

    def test_preview_of_an_unmappable_file(self) -> None:
        """An unmappable file gets no suggestion, not a wrong one."""
        content = build_csv(["a,b"], header="x,y\n")
        preview = preview_sales_file(content, "sales.csv")
        assert preview.suggested_mapping is None


class TestParsing:
    """Every row is validated."""

    @pytest.mark.asyncio
    async def test_valid_rows_are_parsed(self, db_session: AsyncSession) -> None:
        """A good row comes out the other side."""
        sku = await make_sku(db_session)
        content = build_csv([f"{sku.id},B,RESELL_OPEN_BOX,1250.00,2025-05-01"])
        outcome = await parse_sales_csv(
            db_session,
            content,
            ColumnMapping(
                sku="sku_id", grade="grade", channel="channel", price="price", sold_at="sold_at"
            ),
        )
        assert outcome.total == 1
        assert len(outcome.rows) == 1
        assert not outcome.rejected

        row = outcome.rows[0]
        assert row.sku_id == sku.id
        assert row.grade == "B"
        assert row.channel == "RESELL_OPEN_BOX"
        assert row.price == 1250.0

    @pytest.mark.asyncio
    async def test_unknown_sku_is_rejected(self, db_session: AsyncSession) -> None:
        """A row for a SKU that does not exist is rejected with a reason."""
        content = build_csv(
            ["00000000-0000-0000-0000-000000000000,B,RESELL_OPEN_BOX,100,2025-05-01"]
        )
        outcome = await parse_sales_csv(
            db_session,
            content,
            ColumnMapping(
                sku="sku_id", grade="grade", channel="channel", price="price", sold_at="sold_at"
            ),
        )
        assert not outcome.rows
        assert outcome.rejected[0].reason == "unknown_sku"
        assert outcome.rejected[0].row_number == 2

    @pytest.mark.asyncio
    async def test_invalid_grade_is_rejected(self, db_session: AsyncSession) -> None:
        """An unrecognised grade is rejected."""
        sku = await make_sku(db_session)
        content = build_csv([f"{sku.id},ZZZ,RESELL_OPEN_BOX,100,2025-05-01"])
        outcome = await parse_sales_csv(
            db_session,
            content,
            ColumnMapping(
                sku="sku_id", grade="grade", channel="channel", price="price", sold_at="sold_at"
            ),
        )
        assert outcome.rejected[0].reason == "invalid_grade"

    @pytest.mark.asyncio
    async def test_invalid_channel_is_rejected(self, db_session: AsyncSession) -> None:
        """An unknown channel is rejected."""
        sku = await make_sku(db_session)
        content = build_csv([f"{sku.id},B,MYSTERY,100,2025-05-01"])
        outcome = await parse_sales_csv(
            db_session,
            content,
            ColumnMapping(
                sku="sku_id", grade="grade", channel="channel", price="price", sold_at="sold_at"
            ),
        )
        assert outcome.rejected[0].reason == "invalid_channel"

    @pytest.mark.asyncio
    async def test_non_positive_price_is_rejected(self, db_session: AsyncSession) -> None:
        """A price of zero or less is rejected."""
        sku = await make_sku(db_session)
        content = build_csv([f"{sku.id},B,RESELL_OPEN_BOX,0,2025-05-01"])
        outcome = await parse_sales_csv(
            db_session,
            content,
            ColumnMapping(
                sku="sku_id", grade="grade", channel="channel", price="price", sold_at="sold_at"
            ),
        )
        assert outcome.rejected[0].reason == "invalid_price"

    @pytest.mark.asyncio
    async def test_bad_date_is_rejected(self, db_session: AsyncSession) -> None:
        """A date that cannot be read is rejected."""
        sku = await make_sku(db_session)
        content = build_csv([f"{sku.id},B,RESELL_OPEN_BOX,100,not-a-date"])
        outcome = await parse_sales_csv(
            db_session,
            content,
            ColumnMapping(
                sku="sku_id", grade="grade", channel="channel", price="price", sold_at="sold_at"
            ),
        )
        assert outcome.rejected[0].reason == "invalid_date"

    @pytest.mark.asyncio
    async def test_channel_aliases_are_accepted(self, db_session: AsyncSession) -> None:
        """A partner's own channel names are understood."""
        sku = await make_sku(db_session)
        content = build_csv([f"{sku.id},B,open box,100,2025-05-01"])
        outcome = await parse_sales_csv(
            db_session,
            content,
            ColumnMapping(
                sku="sku_id", grade="grade", channel="channel", price="price", sold_at="sold_at"
            ),
        )
        assert outcome.rows[0].channel == "RESELL_OPEN_BOX"

    @pytest.mark.asyncio
    async def test_price_with_currency_symbol_is_parsed(self, db_session: AsyncSession) -> None:
        """A price written as ``$1,250.00`` is understood."""
        sku = await make_sku(db_session)
        content = build_csv([f'{sku.id},B,RESELL_OPEN_BOX,"$1,250.00",2025-05-01'])
        outcome = await parse_sales_csv(
            db_session,
            content,
            ColumnMapping(
                sku="sku_id", grade="grade", channel="channel", price="price", sold_at="sold_at"
            ),
        )
        assert outcome.rows[0].price == 1250.0


class TestImport:
    """The import itself."""

    @pytest.mark.asyncio
    async def test_import_writes_observations(self, db_session: AsyncSession) -> None:
        """Accepted rows become price observations."""
        sku = await make_sku(db_session)
        content = build_csv(
            [
                f"{sku.id},A,RESELL_OPEN_BOX,1800,2025-05-01",
                f"{sku.id},B,RESELL_OPEN_BOX,1500,2025-05-02",
            ]
        )
        result = await import_sales(db_session, content, filename="sales.csv", source="partner_a")
        assert result.rows_imported == 2
        assert result.rows_rejected == 0
        assert result.already_imported is False

        observations = (await db_session.execute(select(PriceObservation))).scalars().all()
        assert len(observations) == 2
        assert all(o.source == "partner_a" for o in observations)
        assert all(o.is_synthetic is False for o in observations)

    @pytest.mark.asyncio
    async def test_dry_run_writes_nothing(self, db_session: AsyncSession) -> None:
        """A dry run leaves the database alone."""
        sku = await make_sku(db_session)
        content = build_csv([f"{sku.id},A,RESELL_OPEN_BOX,1800,2025-05-01"])
        result = await import_sales(
            db_session, content, filename="sales.csv", source="partner_a", dry_run=True
        )
        assert result.dry_run is True
        assert result.rows_imported == 1

        observations = (await db_session.execute(select(PriceObservation))).scalars().all()
        assert not observations

    @pytest.mark.asyncio
    async def test_dry_run_matches_the_real_run(self, db_session: AsyncSession) -> None:
        """The acceptance criterion: the dry run reports the same counts."""
        sku = await make_sku(db_session)
        content = build_csv(
            [
                f"{sku.id},A,RESELL_OPEN_BOX,1800,2025-05-01",
                f"{sku.id},B,RESELL_OPEN_BOX,1500,2025-05-02",
                "not-a-uuid,B,RESELL_OPEN_BOX,100,2025-05-03",
                f"{sku.id},ZZZ,RESELL_OPEN_BOX,100,2025-05-04",
            ]
        )
        dry = await import_sales(
            db_session, content, filename="sales.csv", source="partner_a", dry_run=True
        )
        real = await import_sales(db_session, content, filename="sales.csv", source="partner_a")

        assert dry.rows_total == real.rows_total
        assert dry.rows_imported == real.rows_imported
        assert dry.rows_rejected == real.rows_rejected
        assert [r.reason for r in dry.rejected] == [r.reason for r in real.rejected]

    @pytest.mark.asyncio
    async def test_reimporting_the_same_file_changes_nothing(
        self, db_session: AsyncSession
    ) -> None:
        """The acceptance criterion: the import is idempotent."""
        sku = await make_sku(db_session)
        content = build_csv([f"{sku.id},A,RESELL_OPEN_BOX,1800,2025-05-01"])

        first = await import_sales(db_session, content, filename="sales.csv", source="partner_a")
        await db_session.commit()

        second = await import_sales(db_session, content, filename="sales.csv", source="partner_a")

        assert first.already_imported is False
        assert second.already_imported is True
        assert second.rows_imported == first.rows_imported

        observations = (await db_session.execute(select(PriceObservation))).scalars().all()
        assert len(observations) == 1

    @pytest.mark.asyncio
    async def test_rejected_rows_are_reported_with_reasons(self, db_session: AsyncSession) -> None:
        """The rejection reasons come back."""
        content = build_csv(["not-a-uuid,B,RESELL_OPEN_BOX,100,2025-05-01"])
        result = await import_sales(db_session, content, filename="sales.csv", source="partner_a")
        assert result.rows_rejected == 1
        assert result.rejected[0].reason == "unknown_sku"
        assert result.rejected[0].row_number == 2

    @pytest.mark.asyncio
    async def test_unmappable_file_is_rejected(self, db_session: AsyncSession) -> None:
        """A file the auto-detection cannot map is an error."""
        content = b"a,b\n1,2\n"
        with pytest.raises(ValueError, match="could not work out"):
            await import_sales(db_session, content, filename="x.csv", source="partner_a")

    @pytest.mark.asyncio
    async def test_explicit_mapping_is_used(self, db_session: AsyncSession) -> None:
        """An explicit mapping overrides the auto-detection."""
        sku = await make_sku(db_session)
        content = build_csv(
            [f"{sku.id},A,RESELL_OPEN_BOX,1800,2025-05-01"],
            header="product,condition,sales_channel,amount,when\n",
        )
        mapping = ColumnMapping(
            sku="product",
            grade="condition",
            channel="sales_channel",
            price="amount",
            sold_at="when",
        )
        result = await import_sales(
            db_session, content, filename="x.csv", source="partner_a", mapping=mapping
        )
        assert result.rows_imported == 1
        assert result.mapping is not None
        assert result.mapping.price == "amount"

    @pytest.mark.asyncio
    async def test_missing_column_is_rejected(self, db_session: AsyncSession) -> None:
        """A mapping that names a column the file does not have is an error."""
        content = build_csv(
            ["x,A,RESELL_OPEN_BOX,1800,2025-05-01"],
            header="sku_id,grade,channel,price\n",
        )
        mapping = ColumnMapping(
            sku="sku_id", grade="grade", channel="channel", price="price", sold_at="sold_at"
        )
        with pytest.raises(ValueError, match="no column named"):
            await import_sales(
                db_session, content, filename="x.csv", source="partner_a", mapping=mapping
            )


class TestImportApi:
    """The import endpoints."""

    @pytest.mark.asyncio
    async def test_preview_endpoint(self, client: AsyncClient) -> None:
        """The preview endpoint describes the file."""
        content = build_csv(["x,A,RESELL_OPEN_BOX,1800,2025-05-01"])
        response = await client.post(
            "/api/v1/imports/sales/preview",
            files={"file": ("sales.csv", content, "text/csv")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["row_count"] == 1
        assert data["suggested_mapping"]["price"] == "price"

    @pytest.mark.asyncio
    async def test_import_endpoint(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """The import endpoint writes the rows."""
        sku = await make_sku(db_session)
        content = build_csv([f"{sku.id},A,RESELL_OPEN_BOX,1800,2025-05-01"])
        response = await client.post(
            "/api/v1/imports/sales",
            files={"file": ("sales.csv", content, "text/csv")},
            data={"source": "partner_a"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rows_imported"] == 1
        assert data["already_imported"] is False

    @pytest.mark.asyncio
    async def test_import_endpoint_is_idempotent(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The endpoint reports the second import as a no-op."""
        sku = await make_sku(db_session)
        content = build_csv([f"{sku.id},A,RESELL_OPEN_BOX,1800,2025-05-01"])
        files = {"file": ("sales.csv", content, "text/csv")}

        first = await client.post(
            "/api/v1/imports/sales", files=files, data={"source": "partner_a"}
        )
        second = await client.post(
            "/api/v1/imports/sales", files=files, data={"source": "partner_a"}
        )

        assert first.json()["already_imported"] is False
        assert second.json()["already_imported"] is True
        assert second.json()["rows_imported"] == 1

    @pytest.mark.asyncio
    async def test_dry_run_endpoint(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """The dry run endpoint writes nothing."""
        sku = await make_sku(db_session)
        content = build_csv([f"{sku.id},A,RESELL_OPEN_BOX,1800,2025-05-01"])
        response = await client.post(
            "/api/v1/imports/sales",
            files={"file": ("sales.csv", content, "text/csv")},
            data={"source": "partner_a", "dry_run": "true"},
        )
        assert response.status_code == 200
        assert response.json()["dry_run"] is True

        observations = (await db_session.execute(select(PriceObservation))).scalars().all()
        assert not observations

    @pytest.mark.asyncio
    async def test_import_endpoint_rejects_a_bad_mapping(self, client: AsyncClient) -> None:
        """A malformed mapping is a 422."""
        content = build_csv(["x,A,RESELL_OPEN_BOX,1800,2025-05-01"])
        response = await client.post(
            "/api/v1/imports/sales",
            files={"file": ("sales.csv", content, "text/csv")},
            data={"source": "partner_a", "mapping_json": "{not json"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_imports_endpoint(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The import history comes back."""
        sku = await make_sku(db_session)
        content = build_csv([f"{sku.id},A,RESELL_OPEN_BOX,1800,2025-05-01"])
        await client.post(
            "/api/v1/imports/sales",
            files={"file": ("sales.csv", content, "text/csv")},
            data={"source": "partner_a"},
        )
        response = await client.get("/api/v1/imports/sales")
        assert response.status_code == 200
        assert response.json()["total"] == 1
