"""
Tests for outcome logging (Phase 4 - F4.2).
"""

import pytest
from datetime import datetime
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.identity.models import SKU
from secondroute.intake.models import Unit, Inspection, ReturnReasonCode, OrderChannel
from secondroute.decision.models import Decision
from secondroute.feedback.models import Outcome


async def _make_unit_with_decision(
    db_session: AsyncSession, *, with_decision: bool = True, suffix: str = ""
) -> tuple[Unit, Decision | None]:
    """Create a unit, inspection and (optionally) a decision."""
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
        as_of=datetime(2024, 1, 15).date(),
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

    if not with_decision:
        return unit, None

    decision = Decision(
        unit_id=unit.id,
        model_version="decision-v1",
        risk_profile="balanced",
        recommended_channel="RESELL_OPEN_BOX",
        confidence=0.85,
        fallback_used=False,
        candidates_json="[]",
        reasons_json="[]",
        flip_conditions_json="[]",
        data_freshness_json="{}",
        action_steps_json="[]",
        input_snapshot_hash="abc123",
        input_snapshot_json="{}",
    )
    db_session.add(decision)
    await db_session.commit()
    await db_session.refresh(decision)

    return unit, decision


def _outcome_body(**overrides) -> dict:
    """Build a valid outcome request body."""
    body = {
        "channel_taken": "RESELL_OPEN_BOX",
        "sale_price": 1000.0,
        "fees_actual": 120.0,
        "repair_cost_actual": 0.0,
        "logistics_actual": 25.0,
        "days_to_disposition": 7,
        "final_status": "sold",
    }
    body.update(overrides)
    return body


class TestCreateOutcome:
    """Tests for POST /units/{id}/outcome."""

    @pytest.mark.asyncio
    async def test_create_outcome(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test recording an outcome."""
        unit, decision = await _make_unit_with_decision(db_session)

        response = await client.post(
            f"/api/v1/units/{unit.id}/outcome",
            json=_outcome_body(),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["unit_id"] == str(unit.id)
        assert data["decision_id"] == str(decision.id)
        assert data["channel_taken"] == "RESELL_OPEN_BOX"
        assert data["sale_price"] == 1000.0
        assert data["days_to_disposition"] == 7
        assert data["final_status"] == "sold"
        # net = sale_price - fees - repair - logistics
        assert data["net"] == pytest.approx(1000.0 - 120.0 - 0.0 - 25.0)

    @pytest.mark.asyncio
    async def test_outcome_for_unit_with_no_decision_is_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that a unit with no decision cannot have an outcome."""
        unit, _ = await _make_unit_with_decision(db_session, with_decision=False)

        response = await client.post(
            f"/api/v1/units/{unit.id}/outcome",
            json=_outcome_body(),
        )

        assert response.status_code == 404
        assert "no decision" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_outcome_with_explicit_decision_id(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test recording an outcome with an explicit decision."""
        unit, decision = await _make_unit_with_decision(db_session)

        response = await client.post(
            f"/api/v1/units/{unit.id}/outcome",
            json=_outcome_body(decision_id=str(decision.id)),
        )

        assert response.status_code == 201
        assert response.json()["decision_id"] == str(decision.id)

    @pytest.mark.asyncio
    async def test_outcome_with_nonexistent_decision_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that an outcome referencing a missing decision returns 404."""
        unit, _ = await _make_unit_with_decision(db_session)

        response = await client.post(
            f"/api/v1/units/{unit.id}/outcome",
            json=_outcome_body(decision_id=str(uuid4())),
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_outcome_with_decision_from_another_unit_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that a decision from a different unit is rejected."""
        unit_a, _ = await _make_unit_with_decision(db_session, suffix="A")
        _, decision_b = await _make_unit_with_decision(db_session, suffix="B")

        response = await client.post(
            f"/api/v1/units/{unit_a.id}/outcome",
            json=_outcome_body(decision_id=str(decision_b.id)),
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_second_outcome_creates_new_row(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that a second outcome is appended, not an overwrite."""
        unit, decision = await _make_unit_with_decision(db_session)

        first = await client.post(
            f"/api/v1/units/{unit.id}/outcome",
            json=_outcome_body(sale_price=1000.0),
        )
        assert first.status_code == 201
        first_id = first.json()["id"]

        second = await client.post(
            f"/api/v1/units/{unit.id}/outcome",
            json=_outcome_body(sale_price=900.0, final_status="recycled"),
        )
        assert second.status_code == 201
        second_id = second.json()["id"]

        # Different rows
        assert first_id != second_id

        # Both rows exist
        result = await db_session.execute(select(Outcome).where(Outcome.unit_id == unit.id))
        outcomes = result.scalars().all()
        assert len(outcomes) == 2

        # The first outcome is unchanged
        prices = sorted(o.sale_price for o in outcomes)
        assert prices == [900.0, 1000.0]

    @pytest.mark.asyncio
    async def test_outcome_with_negative_values_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that negative realized costs are rejected."""
        unit, _ = await _make_unit_with_decision(db_session)

        response = await client.post(
            f"/api/v1/units/{unit.id}/outcome",
            json=_outcome_body(sale_price=-100.0),
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_outcome_with_negative_days_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that negative days-to-disposition is rejected."""
        unit, _ = await _make_unit_with_decision(db_session)

        response = await client.post(
            f"/api/v1/units/{unit.id}/outcome",
            json=_outcome_body(days_to_disposition=-1),
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_outcome_with_blank_channel_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that a blank channel is rejected."""
        unit, _ = await _make_unit_with_decision(db_session)

        response = await client.post(
            f"/api/v1/units/{unit.id}/outcome",
            json=_outcome_body(channel_taken="   "),
        )

        assert response.status_code == 422


class TestListOutcomes:
    """Tests for listing outcomes."""

    @pytest.mark.asyncio
    async def test_list_outcomes_for_unit(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test listing the outcomes for a unit."""
        unit, _ = await _make_unit_with_decision(db_session)

        await client.post(f"/api/v1/units/{unit.id}/outcome", json=_outcome_body())

        response = await client.get(f"/api/v1/units/{unit.id}/outcomes")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["channel_taken"] == "RESELL_OPEN_BOX"

    @pytest.mark.asyncio
    async def test_list_outcomes_for_decision(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test listing the outcomes linked to a decision."""
        unit, decision = await _make_unit_with_decision(db_session)

        await client.post(f"/api/v1/units/{unit.id}/outcome", json=_outcome_body())

        response = await client.get(f"/api/v1/decisions/{decision.id}/outcomes")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_list_outcomes_empty(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test listing outcomes when there are none."""
        unit, _ = await _make_unit_with_decision(db_session)

        response = await client.get(f"/api/v1/units/{unit.id}/outcomes")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_get_outcome_by_id(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test getting one outcome by ID."""
        unit, _ = await _make_unit_with_decision(db_session)

        create_response = await client.post(
            f"/api/v1/units/{unit.id}/outcome", json=_outcome_body()
        )
        outcome_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/outcomes/{outcome_id}")
        assert response.status_code == 200
        assert response.json()["id"] == outcome_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_outcome_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting a non-existent outcome returns 404."""
        response = await client.get(f"/api/v1/outcomes/{uuid4()}")
        assert response.status_code == 404


class TestOutcomeImmutability:
    """Tests that outcomes cannot be edited or deleted through the API."""

    @pytest.mark.asyncio
    async def test_outcome_cannot_be_updated(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test there is no endpoint to update an outcome."""
        unit, _ = await _make_unit_with_decision(db_session)

        create_response = await client.post(
            f"/api/v1/units/{unit.id}/outcome", json=_outcome_body()
        )
        outcome_id = create_response.json()["id"]

        assert (await client.patch(f"/api/v1/outcomes/{outcome_id}", json={})).status_code == 405
        assert (await client.put(f"/api/v1/outcomes/{outcome_id}", json={})).status_code == 405

    @pytest.mark.asyncio
    async def test_outcome_cannot_be_deleted(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test there is no endpoint to delete an outcome."""
        unit, _ = await _make_unit_with_decision(db_session)

        create_response = await client.post(
            f"/api/v1/units/{unit.id}/outcome", json=_outcome_body()
        )
        outcome_id = create_response.json()["id"]

        assert (await client.delete(f"/api/v1/outcomes/{outcome_id}")).status_code == 405
