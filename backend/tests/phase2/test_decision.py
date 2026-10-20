"""
Tests for the decision API and persistence (F2.9).
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import pytest
from sqlalchemy import select

from secondroute.decision.engine import DECISION_MODEL_VERSION
from secondroute.decision.models import Decision, hash_snapshot
from secondroute.identity.models import SKU
from secondroute.intake.models import Inspection, Unit
from secondroute.intake.models import OrderChannel, ReturnReasonCode


async def make_unit(db_session: AsyncSession, *, battery: str = "95", grade: str = "A") -> Unit:
    """Create a unit with one inspection, ready to be decided."""
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

    unit = Unit(
        sku_id=sku.id,
        return_reason_code=ReturnReasonCode.BUYER_REMORSE,
        order_channel=OrderChannel.ONLINE,
    )
    db_session.add(unit)
    await db_session.flush()

    inspection = Inspection(
        unit_id=unit.id,
        battery_health_pct=battery,
        battery_cycles="120",
        cosmetic_grade=grade,
        functional_tests_json='{"display": true, "keyboard": true}',
        activation_lock="none",
        accessories_json='{"charger": true}',
    )
    db_session.add(inspection)
    await db_session.flush()
    await db_session.refresh(unit)
    return unit


class TestDecisionApi:
    """The decision endpoints."""

    @pytest.mark.asyncio
    async def test_create_decision(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """A decision can be requested for an inspected unit."""
        unit = await make_unit(db_session)
        response = await client.post(f"/api/v1/units/{unit.id}/decide")
        assert response.status_code == 201
        data = response.json()
        assert data["unit_id"] == str(unit.id)
        assert data["recommended_channel"]
        assert 0.0 <= data["confidence"] <= 1.0
        assert data["input_snapshot_hash"]
        assert data["is_prototype"] is True

    @pytest.mark.asyncio
    async def test_decision_includes_candidates_reasons_and_steps(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The decision card payload is complete."""
        unit = await make_unit(db_session)
        response = await client.post(f"/api/v1/units/{unit.id}/decide")
        data = response.json()

        assert len(data["candidates"]) == 5  # 4 resale channels + parts harvest
        assert data["reasons"]
        assert data["action_steps"]
        assert data["data_freshness"]["is_synthetic"] is True
        assert data["data_freshness"]["warnings"]

    @pytest.mark.asyncio
    async def test_decision_for_unit_without_inspection_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """A unit with no inspection cannot be decided."""
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
        unit = Unit(
            sku_id=sku.id,
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        db_session.add(unit)
        await db_session.flush()

        response = await client.post(f"/api/v1/units/{unit.id}/decide")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_decision_for_unknown_unit_returns_404(self, client: AsyncClient) -> None:
        """An unknown unit returns a not-found."""
        response = await client.post(f"/api/v1/units/{uuid4()}/decide")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_decision(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """A stored decision can be read back."""
        unit = await make_unit(db_session)
        created = await client.post(f"/api/v1/units/{unit.id}/decide")
        decision_id = created.json()["id"]

        response = await client.get(f"/api/v1/decisions/{decision_id}")
        assert response.status_code == 200
        assert response.json()["id"] == decision_id

    @pytest.mark.asyncio
    async def test_get_unknown_decision_returns_404(self, client: AsyncClient) -> None:
        """An unknown decision returns a not-found."""
        response = await client.get(f"/api/v1/decisions/{uuid4()}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_unit_decisions(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """A unit's decisions can be listed."""
        unit = await make_unit(db_session)
        await client.post(f"/api/v1/units/{unit.id}/decide")
        await client.post(f"/api/v1/units/{unit.id}/decide")

        response = await client.get(f"/api/v1/units/{unit.id}/decisions")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_decisions_are_append_only(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Running the decision twice stores two rows and changes the first."""
        unit = await make_unit(db_session)
        first = await client.post(f"/api/v1/units/{unit.id}/decide")
        first_id = first.json()["id"]
        first_hash = first.json()["input_snapshot_hash"]

        second = await client.post(f"/api/v1/units/{unit.id}/decide")
        second_id = second.json()["id"]

        assert first_id != second_id

        reread = await client.get(f"/api/v1/decisions/{first_id}")
        assert reread.json()["input_snapshot_hash"] == first_hash


class TestReproducibility:
    """A decision must be reproducible from its snapshot."""

    @pytest.mark.asyncio
    async def test_identical_inputs_give_identical_output(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The same unit and the same as-of give the same recommendation and hash."""
        unit = await make_unit(db_session)
        as_of = "2025-06-01T00:00:00"
        payload = {"risk_profile": "balanced", "as_of": as_of}
        first = await client.post(f"/api/v1/units/{unit.id}/decide", json=payload)
        second = await client.post(f"/api/v1/units/{unit.id}/decide", json=payload)

        assert first.json()["recommended_channel"] == second.json()["recommended_channel"]
        assert first.json()["confidence"] == pytest.approx(second.json()["confidence"])
        assert first.json()["input_snapshot_hash"] == second.json()["input_snapshot_hash"]

    @pytest.mark.asyncio
    async def test_decision_can_be_reproduced_from_its_snapshot(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The reproduce endpoint replays the decision."""
        unit = await make_unit(db_session)
        created = await client.post(f"/api/v1/units/{unit.id}/decide")
        decision_id = created.json()["id"]

        response = await client.get(f"/api/v1/decisions/{decision_id}/reproduce")
        assert response.status_code == 200
        data = response.json()
        assert data["matches"] is True
        assert data["replayed_hash"] == data["input_snapshot_hash"]
        assert data["recommended_channel"] == created.json()["recommended_channel"]

    @pytest.mark.asyncio
    async def test_reproduce_for_unknown_decision_returns_404(self, client: AsyncClient) -> None:
        """An unknown decision cannot be reproduced."""
        response = await client.get(f"/api/v1/decisions/{uuid4()}/reproduce")
        assert response.status_code == 404


class TestDecisionPersistence:
    """The stored decision row."""

    @pytest.mark.asyncio
    async def test_snapshot_hash_is_stable(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The stored hash matches a fresh hash of the stored snapshot."""
        unit = await make_unit(db_session)
        created = await client.post(f"/api/v1/units/{unit.id}/decide")
        decision_id = UUID(created.json()["id"])

        result = await db_session.execute(select(Decision).where(Decision.id == decision_id))
        decision = result.scalar_one()
        assert decision.input_snapshot_hash == hash_snapshot(decision.input_snapshot)

    @pytest.mark.asyncio
    async def test_model_version_is_recorded(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The engine version is stored with the decision."""
        unit = await make_unit(db_session)
        created = await client.post(f"/api/v1/units/{unit.id}/decide")
        assert created.json()["model_version"] == DECISION_MODEL_VERSION

    @pytest.mark.asyncio
    async def test_risk_profile_is_recorded(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The risk profile is stored with the decision."""
        unit = await make_unit(db_session)
        created = await client.post(
            f"/api/v1/units/{unit.id}/decide", json={"risk_profile": "conservative"}
        )
        assert created.json()["risk_profile"] == "conservative"

    @pytest.mark.asyncio
    async def test_snapshot_records_the_inputs(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The snapshot captures everything needed to replay the decision."""
        unit = await make_unit(db_session)
        created = await client.post(f"/api/v1/units/{unit.id}/decide")
        decision_id = UUID(created.json()["id"])

        result = await db_session.execute(select(Decision).where(Decision.id == decision_id))
        decision = result.scalar_one()
        snapshot = decision.input_snapshot

        assert snapshot["unit_id"] == str(unit.id)
        assert snapshot["signals"]["battery_health_pct"] == pytest.approx(95.0)
        assert snapshot["signals"]["cosmetic_grade"] == "A"
        assert snapshot["cost_book"]
        assert snapshot["seed"]
        assert snapshot["samples"]

    @pytest.mark.asyncio
    async def test_data_freshness_records_the_price_source(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Every price used is traceable to a source and an as-of date."""
        unit = await make_unit(db_session)
        created = await client.post(f"/api/v1/units/{unit.id}/decide")
        decision_id = UUID(created.json()["id"])

        result = await db_session.execute(select(Decision).where(Decision.id == decision_id))
        decision = result.scalar_one()
        freshness = decision.data_freshness

        assert freshness["price_sources"]
        assert freshness["price_as_of"]
        assert freshness["cost_sources"]
        assert freshness["cost_as_of"]
