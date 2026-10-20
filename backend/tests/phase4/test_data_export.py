"""
Tests for the data export (Phase 4 - F4.8).
"""

import csv
import io
import json
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.analytics.export import (
    DECISIONS,
    OUTCOMES,
    OVERRIDES,
    combined_hash,
    read_csv,
    row_hash,
    write_csv,
)
from secondroute.decision.models import Decision
from secondroute.feedback.models import Outcome, Override
from secondroute.identity.models import SKU
from secondroute.intake.models import Inspection, OrderChannel, ReturnReasonCode, Unit


async def _make_unit(db_session: AsyncSession, *, suffix: str = "") -> Unit:
    """Create a unit with an inspection."""
    sku = SKU(
        family="Test",
        model_name=f"Model{suffix}",
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
        serial=f"EXP{suffix}",
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
        functional_tests_json={},
        activation_lock="none",
        accessories_json={},
    )
    db_session.add(inspection)
    await db_session.commit()

    return unit


async def _make_decision(
    db_session: AsyncSession,
    unit: Unit,
    *,
    synthetic: bool = True,
) -> Decision:
    """Create a decision."""
    decision = Decision(
        unit_id=unit.id,
        model_version="decision-v1",
        risk_profile="balanced",
        recommended_channel="RESELL_OPEN_BOX",
        confidence=0.8,
        fallback_used=False,
        candidates_json=json.dumps([]),
        reasons_json="[]",
        flip_conditions_json="[]",
        data_freshness_json=json.dumps({"is_synthetic": synthetic}),
        action_steps_json="[]",
        input_snapshot_hash="abc123",
        input_snapshot_json="{}",
    )
    db_session.add(decision)
    await db_session.commit()
    await db_session.refresh(decision)
    return decision


async def _make_outcome(
    db_session: AsyncSession,
    unit: Unit,
    decision: Decision,
) -> Outcome:
    """Create an outcome."""
    outcome = Outcome(
        unit_id=unit.id,
        decision_id=decision.id,
        channel_taken="RESELL_OPEN_BOX",
        sale_price=900.0,
        fees_actual=100.0,
        repair_cost_actual=0.0,
        logistics_actual=0.0,
        days_to_disposition=7,
        final_status="sold",
    )
    db_session.add(outcome)
    await db_session.commit()
    await db_session.refresh(outcome)
    return outcome


async def _make_override(db_session: AsyncSession, decision: Decision) -> Override:
    """Create an override."""
    override = Override(
        decision_id=decision.id,
        chosen_channel="RECYCLE",
        reason_text="Too risky",
    )
    db_session.add(override)
    await db_session.commit()
    await db_session.refresh(override)
    return override


def _rows(csv_text: str) -> list[dict[str, str]]:
    """Parse a CSV into rows."""
    return list(csv.DictReader(io.StringIO(csv_text)))


class TestRowHash:
    """Tests for the row hash."""

    @pytest.mark.asyncio
    async def test_the_hash_covers_the_columns(self) -> None:
        """Test that a changed column changes the hash."""
        row = dict.fromkeys(DECISIONS.hashed_columns, "value")
        first = row_hash(DECISIONS, row)
        row["model_version"] = "decision-v2"

        assert row_hash(DECISIONS, row) != first

    @pytest.mark.asyncio
    async def test_the_hash_is_stable(self) -> None:
        """Test that the same row always gives the same hash."""
        row = dict.fromkeys(DECISIONS.hashed_columns, "value")

        assert row_hash(DECISIONS, row) == row_hash(DECISIONS, dict(row))

    @pytest.mark.asyncio
    async def test_the_combined_hash_follows_the_rows(self) -> None:
        """Test that the combined hash changes when a row changes."""
        first = combined_hash(["a", "b"])
        second = combined_hash(["a", "c"])

        assert first != second


class TestExportRoundTrip:
    """Tests for the round trip of an export."""

    @pytest.mark.asyncio
    async def test_a_written_export_reads_back(self) -> None:
        """Test that a written export round-trips."""
        row = dict.fromkeys(DECISIONS.hashed_columns, "value")
        csv_text = write_csv(DECISIONS, [row])

        result = read_csv(DECISIONS, csv_text)

        assert result.rows == 1
        assert result.matching_hashes == 1
        assert result.mismatching_hashes == 0
        assert result.round_trips is True

    @pytest.mark.asyncio
    async def test_a_tampered_row_is_caught(self) -> None:
        """Test that a changed value no longer matches its hash."""
        row = dict.fromkeys(DECISIONS.hashed_columns, "value")
        csv_text = write_csv(DECISIONS, [row])
        tampered = csv_text.replace("value", "other", 1)

        result = read_csv(DECISIONS, tampered)

        assert result.mismatching_hashes == 1
        assert result.round_trips is False


class TestExportEndpoints:
    """Tests for the export API."""

    @pytest.mark.asyncio
    async def test_the_decisions_export(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that the decisions export has the snapshot hash and the version."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit)
        await _make_override(db_session, decision)

        response = await client.get("/api/v1/export/decisions")

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        rows = _rows(response.text)
        assert len(rows) == 1
        assert rows[0]["input_snapshot_hash"] == "abc123"
        assert rows[0]["model_version"] == "decision-v1"
        assert rows[0]["data_kind"] == "synthetic"
        assert rows[0]["row_hash"]

    @pytest.mark.asyncio
    async def test_the_overrides_export(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that the overrides export has the reason."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit)
        await _make_override(db_session, decision)

        response = await client.get("/api/v1/export/overrides")

        assert response.status_code == 200
        rows = _rows(response.text)
        assert len(rows) == 1
        assert rows[0]["reason_text"] == "Too risky"
        assert rows[0]["chosen_channel"] == "RECYCLE"

    @pytest.mark.asyncio
    async def test_the_outcomes_export(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test that the outcomes export has the realized numbers."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit)
        await _make_outcome(db_session, unit, decision)

        response = await client.get("/api/v1/export/outcomes")

        assert response.status_code == 200
        rows = _rows(response.text)
        assert len(rows) == 1
        assert float(rows[0]["sale_price"]) == pytest.approx(900.0)
        assert float(rows[0]["net"]) == pytest.approx(800.0)
        assert rows[0]["final_status"] == "sold"

    @pytest.mark.asyncio
    async def test_the_export_round_trips(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that re-importing an export reproduces the row count and hashes."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit)
        await _make_outcome(db_session, unit, decision)

        export = await client.get("/api/v1/export/outcomes")
        assert export.status_code == 200

        response = await client.post(
            "/api/v1/export/outcomes/import",
            content=export.text,
            headers={"Content-Type": "text/csv"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["entity"] == "outcomes"
        assert data["rows"] == 1
        assert data["matching_hashes"] == 1
        assert data["mismatching_hashes"] == 0
        assert data["round_trips"] is True
        assert data["hash"]

    @pytest.mark.asyncio
    async def test_a_tampered_export_does_not_round_trip(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that a changed value is caught on the way back in."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit)
        await _make_outcome(db_session, unit, decision)

        export = await client.get("/api/v1/export/outcomes")
        tampered = export.text.replace("sold", "lost", 1)

        response = await client.post(
            "/api/v1/export/outcomes/import",
            content=tampered,
            headers={"Content-Type": "text/csv"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mismatching_hashes"] == 1
        assert data["round_trips"] is False

    @pytest.mark.asyncio
    async def test_an_unknown_export_is_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that an unknown entity is rejected."""
        response = await client.post(
            "/api/v1/export/nonsense/import",
            content="a,b\n1,2\n",
            headers={"Content-Type": "text/csv"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_an_empty_export(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test that an export with nothing in it still has a header."""
        response = await client.get("/api/v1/export/decisions")

        assert response.status_code == 200
        rows = _rows(response.text)
        assert rows == []
        assert "decision_id" in response.text
