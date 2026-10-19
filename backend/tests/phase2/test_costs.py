"""
Tests for the cost tables (F2.4).
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import pytest
from pydantic import ValidationError

from secondroute.costs.defaults import default_cost_seeds
from secondroute.costs.models import CostKind, CostTable
from secondroute.costs.schemas import CostCreate, CostUpdate
from secondroute.costs.service import CostBook, CostBookEntry, load_cost_book, seed_default_costs


class TestCostCreateValidation:
    """A cost value can never be saved without a source."""

    def test_source_is_required(self) -> None:
        """Omitting the source is rejected."""
        with pytest.raises(ValidationError):
            CostCreate.model_validate(
                {
                    "kind": CostKind.FIXED_FEE,
                    "key": "RESELL_OPEN_BOX",
                    "value": 25.0,
                    "as_of": "2025-06-01",
                }
            )

    def test_blank_source_is_rejected(self) -> None:
        """An empty source is rejected."""
        with pytest.raises(ValidationError):
            CostCreate.model_validate(
                {
                    "kind": CostKind.FIXED_FEE,
                    "key": "RESELL_OPEN_BOX",
                    "value": 25.0,
                    "source": "",
                    "as_of": "2025-06-01",
                }
            )

    def test_whitespace_source_is_rejected(self) -> None:
        """A whitespace-only source is rejected."""
        with pytest.raises(ValidationError):
            CostCreate.model_validate(
                {
                    "kind": CostKind.FIXED_FEE,
                    "key": "RESELL_OPEN_BOX",
                    "value": 25.0,
                    "source": "   ",
                    "as_of": "2025-06-01",
                }
            )

    def test_valid_cost_is_accepted(self) -> None:
        """A cost with a source is accepted."""
        cost = CostCreate(
            kind=CostKind.FIXED_FEE,
            key="RESELL_OPEN_BOX",
            value=25.0,
            source="partner_quote_2025_06",
            as_of=date(2025, 6, 1),
        )
        assert cost.source == "partner_quote_2025_06"
        assert cost.currency == "USD"

    def test_non_finite_value_is_rejected(self) -> None:
        """Infinity and NaN are rejected."""
        for bad in (float("inf"), float("nan")):
            with pytest.raises(ValidationError):
                CostCreate(
                    kind=CostKind.FIXED_FEE,
                    key="RESELL_OPEN_BOX",
                    value=bad,
                    source="test",
                    as_of=date(2025, 6, 1),
                )


class TestCostUpdateValidation:
    """An update can never blank the source."""

    def test_blank_source_is_rejected(self) -> None:
        """An empty source is rejected on update."""
        with pytest.raises(ValidationError):
            CostUpdate(source="")

    def test_whitespace_source_is_rejected(self) -> None:
        """A whitespace-only source is rejected on update."""
        with pytest.raises(ValidationError):
            CostUpdate(source="  \t ")

    def test_valid_update_is_accepted(self) -> None:
        """A normal update is accepted."""
        update = CostUpdate(value=31.5, source="partner_quote_2025_07")
        assert update.value == 31.5


class TestDefaults:
    """The default cost set covers every channel and grade."""

    def test_defaults_cover_every_channel(self) -> None:
        """Every channel has a fee, a fixed fee, logistics, handling and holding."""
        seeds = default_cost_seeds()
        kinds_by_key = {(seed.kind, seed.key) for seed in seeds}

        for channel in ("RESELL_OPEN_BOX", "RESELL_REFURB", "RECYCLE", "DONATE"):
            assert (CostKind.CHANNEL_FEE_PCT, channel) in kinds_by_key
            assert (CostKind.FIXED_FEE, channel) in kinds_by_key
            assert (CostKind.LOGISTICS_COST, channel) in kinds_by_key
            assert (CostKind.HANDLING_COST, channel) in kinds_by_key
            assert (CostKind.HOLDING_COST_PER_DAY, channel) in kinds_by_key

    def test_defaults_cover_every_grade(self) -> None:
        """Repair and days-to-sell exist for every channel and grade."""
        seeds = default_cost_seeds()
        kinds_by_key = {(seed.kind, seed.key) for seed in seeds}

        for channel in ("RESELL_OPEN_BOX", "RESELL_REFURB", "RECYCLE", "DONATE"):
            for grade in ("A", "B", "C", "D"):
                assert (CostKind.REPAIR_COST, f"{channel}:{grade}") in kinds_by_key
                assert (CostKind.EXPECTED_DAYS_TO_SELL, f"{channel}:{grade}") in kinds_by_key

    def test_every_default_has_a_source_and_as_of(self) -> None:
        """Provenance is present on every default."""
        for seed in default_cost_seeds():
            assert seed.source
            assert seed.as_of is not None


class TestCostBook:
    """The cost book lookup behaves as expected."""

    def test_get_returns_the_value(self) -> None:
        """A stored value is returned."""
        book = CostBook(
            entries={
                ("fixed_fee", "RESELL_OPEN_BOX"): CostBookEntry(
                    kind="fixed_fee",
                    key="RESELL_OPEN_BOX",
                    value=25.0,
                    source="test",
                    as_of=date(2025, 1, 1),
                )
            }
        )
        assert book.get("fixed_fee", "RESELL_OPEN_BOX") == 25.0

    def test_get_returns_the_default_when_missing(self) -> None:
        """A missing key returns the default."""
        book = CostBook(entries={})
        assert book.get("fixed_fee", "RESELL_OPEN_BOX", default=7.0) == 7.0

    def test_has_reports_presence(self) -> None:
        """Presence is reported correctly."""
        book = CostBook(
            entries={
                ("fixed_fee", "A"): CostBookEntry(
                    kind="fixed_fee",
                    key="A",
                    value=1.0,
                    source="test",
                    as_of=date(2025, 1, 1),
                )
            }
        )
        assert book.has("fixed_fee", "A")
        assert not book.has("fixed_fee", "B")

    def test_with_override_replaces_one_value(self) -> None:
        """An override changes one entry and leaves the rest alone."""
        book = CostBook(
            entries={
                ("fixed_fee", "A"): CostBookEntry(
                    kind="fixed_fee",
                    key="A",
                    value=1.0,
                    source="test",
                    as_of=date(2025, 1, 1),
                ),
                ("fixed_fee", "B"): CostBookEntry(
                    kind="fixed_fee",
                    key="B",
                    value=2.0,
                    source="test",
                    as_of=date(2025, 1, 1),
                ),
            }
        )
        overridden = book.with_override("fixed_fee", "A", 9.0)
        assert overridden.get("fixed_fee", "A") == 9.0
        assert overridden.get("fixed_fee", "B") == 2.0
        assert book.get("fixed_fee", "A") == 1.0

    def test_with_override_keeps_provenance(self) -> None:
        """An override keeps the original source and as-of date."""
        book = CostBook(
            entries={
                ("fixed_fee", "A"): CostBookEntry(
                    kind="fixed_fee",
                    key="A",
                    value=1.0,
                    source="original_source",
                    as_of=date(2025, 1, 1),
                )
            }
        )
        overridden = book.with_override("fixed_fee", "A", 9.0)
        assert overridden.source_for("fixed_fee", "A") == "original_source"


class TestCostApi:
    """The admin API reads and writes cost values."""

    @pytest.mark.asyncio
    async def test_seed_defaults_is_idempotent(self, db_session: AsyncSession) -> None:
        """Seeding twice adds nothing the second time."""
        first = await seed_default_costs(db_session)
        second = await seed_default_costs(db_session)
        assert first > 0
        assert second == 0

    @pytest.mark.asyncio
    async def test_load_cost_book_reads_the_rows(self, db_session: AsyncSession) -> None:
        """The cost book is built from the table."""
        await seed_default_costs(db_session)
        book = await load_cost_book(db_session)
        assert book.get(CostKind.FIXED_FEE, "RESELL_OPEN_BOX") > 0
        assert book.source_for(CostKind.FIXED_FEE, "RESELL_OPEN_BOX") is not None

    @pytest.mark.asyncio
    async def test_list_costs_endpoint(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """The list endpoint returns the seeded rows."""
        await seed_default_costs(db_session)
        response = await client.get("/api/v1/costs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0
        assert all(item["source"] for item in data["items"])

    @pytest.mark.asyncio
    async def test_create_cost_requires_source(self, client: AsyncClient) -> None:
        """Creating a cost without a source returns 422."""
        response = await client.post(
            "/api/v1/costs",
            json={
                "kind": "fixed_fee",
                "key": "MYSTERY",
                "value": 10.0,
                "as_of": "2025-06-01",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_and_update_cost(self, client: AsyncClient) -> None:
        """A cost can be created and then updated."""
        created = await client.post(
            "/api/v1/costs",
            json={
                "kind": "fixed_fee",
                "key": "MYSTERY",
                "value": 10.0,
                "source": "test_source",
                "as_of": "2025-06-01",
            },
        )
        assert created.status_code == 201
        cost_id = created.json()["id"]

        updated = await client.patch(
            f"/api/v1/costs/{cost_id}",
            json={"value": 12.5, "source": "updated_source"},
        )
        assert updated.status_code == 200
        assert updated.json()["value"] == 12.5
        assert updated.json()["source"] == "updated_source"

    @pytest.mark.asyncio
    async def test_update_rejects_blank_source(self, client: AsyncClient) -> None:
        """Blanking the source on update returns 422."""
        created = await client.post(
            "/api/v1/costs",
            json={
                "kind": "fixed_fee",
                "key": "MYSTERY2",
                "value": 10.0,
                "source": "test_source",
                "as_of": "2025-06-01",
            },
        )
        cost_id = created.json()["id"]
        response = await client.patch(f"/api/v1/costs/{cost_id}", json={"source": ""})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_duplicate_cost_returns_409(self, client: AsyncClient) -> None:
        """Creating the same cost twice returns a conflict."""
        payload = {
            "kind": "fixed_fee",
            "key": "DUPLICATE",
            "value": 10.0,
            "source": "test_source",
            "as_of": "2025-06-01",
        }
        first = await client.post("/api/v1/costs", json=payload)
        second = await client.post("/api/v1/costs", json=payload)
        assert first.status_code == 201
        assert second.status_code == 409

    @pytest.mark.asyncio
    async def test_cost_kinds_endpoint(self, client: AsyncClient) -> None:
        """The kinds endpoint documents every cost kind."""
        response = await client.get("/api/v1/costs/kinds")
        assert response.status_code == 200
        kinds = {item["kind"] for item in response.json()["kinds"]}
        assert CostKind.FIXED_FEE in kinds
        assert CostKind.REPAIR_COST in kinds


class TestCostModel:
    """The cost table row model."""

    def test_repr_mentions_the_kind(self) -> None:
        """The repr is useful in a log."""
        row = CostTable(kind="fixed_fee", key="A", value=1.0, source="s", as_of=date(2025, 1, 1))
        assert "fixed_fee" in repr(row)

    def test_org_id_is_optional(self) -> None:
        """Organisation scoping arrives in Phase 5."""
        row = CostTable(kind="fixed_fee", key="A", value=1.0, source="s", as_of=date(2025, 1, 1))
        assert row.org_id is None
        assert row.id is None or isinstance(row.id, uuid4().__class__)
