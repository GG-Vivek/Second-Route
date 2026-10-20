"""
Tests for the audit log (Phase 1 - F1.7).

The acceptance criterion is that every mutation produces *exactly one*
audit row, and that the rows cannot be edited through the API.

The "exactly one" half is a regression guard: the listeners wrote two
rows for one change at one point, and a test that only checked that a row
existed would not have noticed.
"""

from __future__ import annotations

import json
from datetime import date
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.db import set_current_actor
from secondroute.decision.models import Decision
from secondroute.feedback.models import AuditAction, AuditLog, Outcome
from secondroute.identity.models import SKU
from secondroute.intake.models import (
    Inspection,
    OrderChannel,
    ReturnReasonCode,
    Unit,
)


async def _make_sku(db_session: AsyncSession, suffix: str = "") -> SKU:
    """Create a SKU to hang the units off."""
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
    return sku


async def _make_unit(db_session: AsyncSession, sku: SKU, suffix: str = "") -> Unit:
    """Create a unit."""
    unit = Unit(
        sku_id=sku.id,
        serial=f"AUD{suffix}",
        return_reason_code=ReturnReasonCode.BUYER_REMORSE,
        order_channel=OrderChannel.ONLINE,
    )
    db_session.add(unit)
    await db_session.commit()
    await db_session.refresh(unit)
    return unit


async def _make_decision(db_session: AsyncSession, unit: Unit) -> Decision:
    """Create a decision."""
    decision = Decision(
        unit_id=unit.id,
        model_version="decision-v1",
        risk_profile="balanced",
        recommended_channel="RESELL_OPEN_BOX",
        confidence=0.8,
        fallback_used=False,
        candidates_json="[]",
        reasons_json="[]",
        flip_conditions_json="[]",
        data_freshness_json=json.dumps({"is_synthetic": True}),
        action_steps_json="[]",
        input_snapshot_hash="abc123",
        input_snapshot_json="{}",
    )
    db_session.add(decision)
    await db_session.commit()
    await db_session.refresh(decision)
    return decision


async def _count(
    db_session: AsyncSession,
    entity: str,
    entity_id: str,
) -> int:
    """Count the audit rows for one entity."""
    result = await db_session.execute(
        select(func.count())
        .select_from(AuditLog)
        .where(AuditLog.entity == entity, AuditLog.entity_id == entity_id)
    )
    return int(result.scalar_one())


@pytest.fixture(autouse=True)
def _reset_actor():
    """Keep the actor from leaking between the tests.

    The actor is a context variable, so it is global state: a test that
    named a user and did not clear it would change the actor recorded by
    every test that ran after it.
    """
    set_current_actor(None)
    yield
    set_current_actor(None)


class TestExactlyOneAuditRow:
    """Every mutation writes exactly one row, not two."""

    @pytest.mark.asyncio
    async def test_one_row_per_unit_create(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """A unit create writes one row, not one per flush."""
        sku = await _make_sku(db_session, suffix="1")

        response = await client.post(
            "/api/v1/units",
            json={
                "sku_id": str(sku.id),
                "serial": "ONE-1",
                "return_reason_code": "buyer_remorse",
                "order_channel": "online",
            },
        )
        assert response.status_code == 201
        unit_id = response.json()["id"]

        assert await _count(db_session, "units", unit_id) == 1

    @pytest.mark.asyncio
    async def test_one_row_per_outcome(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Recording an outcome writes one row for the outcome."""
        sku = await _make_sku(db_session, suffix="2")
        unit = await _make_unit(db_session, sku, suffix="2")
        await _make_decision(db_session, unit)

        response = await client.post(
            f"/api/v1/units/{unit.id}/outcome",
            json={
                "channel_taken": "RESELL_OPEN_BOX",
                "sale_price": 900.0,
                "fees_actual": 100.0,
                "repair_cost_actual": 0.0,
                "logistics_actual": 0.0,
                "days_to_disposition": 7,
                "final_status": "sold",
            },
        )
        assert response.status_code == 201
        outcome_id = response.json()["id"]

        assert await _count(db_session, "outcomes", outcome_id) == 1

    @pytest.mark.asyncio
    async def test_one_row_per_inspection(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """An inspection create writes one row."""
        sku = await _make_sku(db_session, suffix="3")
        unit = await _make_unit(db_session, sku, suffix="3")

        response = await client.post(
            f"/api/v1/units/{unit.id}/inspections",
            json={
                "battery_health_pct": "95",
                "battery_cycles": "120",
                "cosmetic_grade": "A",
                "functional_tests_json": {},
                "activation_lock": "none",
                "accessories_json": {},
            },
        )
        assert response.status_code == 201
        inspection_id = response.json()["id"]

        assert await _count(db_session, "inspections", inspection_id) == 1


class TestAuditedEntities:
    """The entities that have to be audited."""

    @pytest.mark.asyncio
    async def test_an_outcome_is_audited(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """An outcome is a fact a person asserted, so it is audited."""
        sku = await _make_sku(db_session, suffix="4")
        unit = await _make_unit(db_session, sku, suffix="4")
        await _make_decision(db_session, unit)

        response = await client.post(
            f"/api/v1/units/{unit.id}/outcome",
            json={
                "channel_taken": "RESELL_OPEN_BOX",
                "sale_price": 900.0,
                "fees_actual": 100.0,
                "repair_cost_actual": 0.0,
                "logistics_actual": 0.0,
                "days_to_disposition": 7,
                "final_status": "sold",
            },
        )
        assert response.status_code == 201
        outcome_id = response.json()["id"]

        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity == "outcomes",
                AuditLog.entity_id == outcome_id,
            )
        )
        row = result.scalar_one()
        assert row.action == AuditAction.CREATE
        assert row.payload_json["data"]["final_status"] == "sold"
        assert row.payload_json["data"]["sale_price"] == pytest.approx(900.0)


class TestAuditActor:
    """The actor is the user who made the change."""

    @pytest.mark.asyncio
    async def test_the_actor_is_the_current_user(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """A change made by a named user is recorded under that name."""
        sku = await _make_sku(db_session, suffix="5")
        set_current_actor("inspector@example.com")

        response = await client.post(
            "/api/v1/units",
            json={
                "sku_id": str(sku.id),
                "serial": "ACTOR-1",
                "return_reason_code": "buyer_remorse",
                "order_channel": "online",
            },
        )
        assert response.status_code == 201
        unit_id = response.json()["id"]
        set_current_actor(None)

        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity == "units",
                AuditLog.entity_id == unit_id,
            )
        )
        row = result.scalar_one()
        assert row.actor == "inspector@example.com"

    @pytest.mark.asyncio
    async def test_an_unauthenticated_change_is_anonymous(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """A change with no user behind it is still recorded."""
        sku = await _make_sku(db_session, suffix="6")
        set_current_actor(None)

        response = await client.post(
            "/api/v1/units",
            json={
                "sku_id": str(sku.id),
                "serial": "ACTOR-2",
                "return_reason_code": "buyer_remorse",
                "order_channel": "online",
            },
        )
        assert response.status_code == 201
        unit_id = response.json()["id"]

        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity == "units",
                AuditLog.entity_id == unit_id,
            )
        )
        row = result.scalar_one()
        assert row.actor == "anonymous"


class TestAuditLogIsReadOnly:
    """The rows cannot be edited through the API."""

    @pytest.mark.asyncio
    async def test_the_audit_log_cannot_be_changed(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Every write method on the audit log is refused."""
        row = AuditLog(
            actor="someone@example.com",
            action=AuditAction.CREATE,
            entity="units",
            entity_id=str(uuid4()),
            payload_json={"action": "create", "data": {}},
        )
        db_session.add(row)
        await db_session.commit()
        await db_session.refresh(row)

        for method in ("put", "patch", "delete"):
            response = await getattr(client, method)(f"/api/v1/audit-log/{row.id}")
            assert response.status_code == 405, f"{method.upper()} was not refused"

        # The row is still there, unchanged.
        result = await db_session.execute(select(AuditLog).where(AuditLog.id == row.id))
        assert result.scalar_one().actor == "someone@example.com"

    @pytest.mark.asyncio
    async def test_the_audit_log_cannot_be_created(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """A row cannot be inserted through the API either."""
        response = await client.post(
            "/api/v1/audit-log",
            json={
                "actor": "someone@example.com",
                "action": "create",
                "entity": "units",
                "entity_id": str(uuid4()),
                "payload_json": {},
            },
        )
        assert response.status_code == 405


class TestOutcomeAuditPayload:
    """The payload of an outcome row holds what was asserted."""

    @pytest.mark.asyncio
    async def test_the_payload_holds_the_realized_numbers(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The realized numbers are in the audit row."""
        sku = await _make_sku(db_session, suffix="7")
        unit = await _make_unit(db_session, sku, suffix="7")
        await _make_decision(db_session, unit)

        response = await client.post(
            f"/api/v1/units/{unit.id}/outcome",
            json={
                "channel_taken": "RESELL_OPEN_BOX",
                "sale_price": 1234.56,
                "fees_actual": 78.90,
                "repair_cost_actual": 12.0,
                "logistics_actual": 5.0,
                "days_to_disposition": 3,
                "final_status": "sold",
            },
        )
        assert response.status_code == 201
        outcome_id = response.json()["id"]

        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity == "outcomes",
                AuditLog.entity_id == outcome_id,
            )
        )
        data = result.scalar_one().payload_json["data"]
        assert data["sale_price"] == pytest.approx(1234.56)
        assert data["fees_actual"] == pytest.approx(78.90)
        assert data["days_to_disposition"] == 3
        assert data["channel_taken"] == "RESELL_OPEN_BOX"


class TestInspectionAudit:
    """The inspection is audited with its grade."""

    @pytest.mark.asyncio
    async def test_an_inspection_records_its_grade(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The grade is in the audit row."""
        sku = await _make_sku(db_session, suffix="8")
        unit = await _make_unit(db_session, sku, suffix="8")

        response = await client.post(
            f"/api/v1/units/{unit.id}/inspections",
            json={
                "battery_health_pct": "88",
                "battery_cycles": "200",
                "cosmetic_grade": "B",
                "functional_tests_json": {"screen": "ok"},
                "activation_lock": "none",
                "accessories_json": {},
            },
        )
        assert response.status_code == 201
        inspection_id = response.json()["id"]

        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity == "inspections",
                AuditLog.entity_id == inspection_id,
            )
        )
        data = result.scalar_one().payload_json["data"]
        assert data["cosmetic_grade"] == "B"
        assert data["battery_health_pct"] == "88"
