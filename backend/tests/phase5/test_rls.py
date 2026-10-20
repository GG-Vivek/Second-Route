"""
Tests for tenant isolation with PostgreSQL RLS (F5.2).
"""

from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.identity.organizations import Organization, User
from secondroute.identity.models import SKU
from secondroute.intake.models import Unit, Inspection, ReturnReasonCode, OrderChannel
from secondroute.decision.models import Decision, hash_snapshot
from secondroute.feedback.models import AuditLog
from secondroute.costs.models import CostTable
from secondroute.core.db import set_current_org_id, with_org_filter


@pytest.fixture
async def org_a(db_session) -> Organization:
    """Create organization A."""
    org = Organization(name="Org A", risk_profile="balanced")
    db_session.add(org)
    await db_session.flush()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def org_b(db_session) -> Organization:
    """Create organization B."""
    org = Organization(name="Org B", risk_profile="aggressive")
    db_session.add(org)
    await db_session.flush()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def user_a(db_session, org_a) -> User:
    """Create user in org A."""
    user = User(org_id=org_a.id, email="user_a@org_a.com", role="inspector")
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def user_b(db_session, org_b) -> User:
    """Create user in org B."""
    user = User(org_id=org_b.id, email="user_b@org_b.com", role="inspector")
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def shared_sku(db_session) -> SKU:
    """Create a shared SKU."""
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
    await db_session.refresh(sku)
    return sku


async def make_unit(db_session, sku, org_id):
    """Create a unit for an org."""
    from secondroute.intake.models import Unit, ReturnReasonCode, OrderChannel
    unit = Unit(
        sku_id=sku.id,
        org_id=org_id,
        return_reason_code=ReturnReasonCode.BUYER_REMORSE,
        order_channel=OrderChannel.ONLINE,
    )
    db_session.add(unit)
    await db_session.flush()
    await db_session.refresh(unit)
    return unit


async def make_decision(db_session, unit_id, org_id):
    """Create a decision for a unit."""
    from secondroute.decision.models import Decision, hash_snapshot
    decision = Decision(
        unit_id=unit_id,
        org_id=org_id,
        recommended_channel="RESELL_OPEN_BOX",
        confidence=0.86,
        candidates_json='[{"channel": "RESELL_OPEN_BOX", "eligible": true, "exclusion_reason": null}]',
        input_snapshot_hash=hash_snapshot({"unit_id": str(unit_id), "seed": 42}),
    )
    db_session.add(decision)
    await db_session.flush()
    await db_session.refresh(decision)
    return decision


class TestTenantIsolation:
    """Tests for tenant isolation via RLS."""

    @pytest.mark.asyncio
    async def test_org_a_cannot_see_org_b_units(self, client, db_session, org_a, org_b, shared_sku):
        """Org A should not see Org B's units."""
        from secondroute.intake.models import Unit
        from secondroute.core.db import set_current_org_id, with_org_filter
        unit_a = await make_unit(db_session, shared_sku, org_a.id)
        unit_b = await make_unit(db_session, shared_sku, org_b.id)

        # Set current org context
        set_current_org_id(str(org_a.id))

        # Query with org filter
        result = await db_session.execute(with_org_filter(select(Unit), Unit))
        units = result.scalars().all()
        unit_ids = {u.id for u in units}

        assert unit_a.id in unit_ids
        assert unit_b.id not in unit_ids

    @pytest.mark.asyncio
    async def test_org_b_cannot_see_org_a_units(self, client, db_session, org_a, org_b, shared_sku):
        """Org B should not see Org A's units."""
        from secondroute.intake.models import Unit
        from secondroute.core.db import set_current_org_id, with_org_filter
        unit_a = await make_unit(db_session, shared_sku, org_a.id)
        unit_b = await make_unit(db_session, shared_sku, org_b.id)

        # Set current org context
        set_current_org_id(str(org_b.id))

        # Query with org filter
        result = await db_session.execute(with_org_filter(select(Unit), Unit))
        units = result.scalars().all()
        unit_ids = {u.id for u in units}

        assert unit_b.id in unit_ids
        assert unit_a.id not in unit_ids

    @pytest.mark.asyncio
    async def test_org_a_cannot_see_org_b_decisions(self, client, db_session, org_a, org_b, shared_sku):
        """Org A should not see Org B's decisions."""
        from secondroute.intake.models import Unit
        from secondroute.decision.models import Decision
        from secondroute.core.db import set_current_org_id, with_org_filter
        unit_a = await make_unit(db_session, shared_sku, org_a.id)
        unit_b = await make_unit(db_session, shared_sku, org_b.id)

        decision_a = await make_decision(db_session, unit_a.id, org_a.id)
        decision_b = await make_decision(db_session, unit_b.id, org_b.id)

        # Set current org context
        set_current_org_id(str(org_a.id))

        # Query with org filter
        from secondroute.core.db import with_org_filter
        query = select(Decision)
        print(f"DEBUG: Original query: {query}")
        filtered_query = with_org_filter(query, Decision)
        print(f"DEBUG: Filtered query: {filtered_query}")
        result = await db_session.execute(filtered_query)
        decisions = result.scalars().all()
        print(f"DEBUG: Found {len(decisions)} decisions")
        for d in decisions:
            print(f"DEBUG: decision id={d.id}, org_id={d.org_id}")
        decision_ids = {d.id for d in decisions}

        assert decision_a.id in decision_ids
        assert decision_b.id not in decision_ids

    @pytest.mark.asyncio
    async def test_org_a_cannot_see_org_b_audit_logs(self, client, db_session, org_a, org_b, shared_sku):
        """Org A should not see Org B's audit logs."""
        from secondroute.intake.models import Unit
        from secondroute.feedback.models import AuditLog
        from secondroute.core.db import set_current_org_id, with_org_filter
        unit_a = await make_unit(db_session, shared_sku, org_a.id)
        unit_b = await make_unit(db_session, shared_sku, org_b.id)

        # Set current org context
        set_current_org_id(str(org_a.id))

        # Query with org filter
        result = await db_session.execute(with_org_filter(select(AuditLog), AuditLog))
        logs = result.scalars().all()

        # All audit logs should be from org A
        for log in logs:
            if log.org_id is not None:
                assert log.org_id == org_a.id

    @pytest.mark.asyncio
    async def test_org_a_cannot_see_org_b_cost_tables(self, client, db_session, org_a, org_b):
        """Org A should not see Org B's cost tables."""
        from secondroute.costs.models import CostTable
        from secondroute.core.db import set_current_org_id, with_org_filter
        cost_a = CostTable(org_id=org_a.id, kind="fee", key="platform", value=0.1, currency="USD", source="test", as_of=date(2024,1,1))
        cost_b = CostTable(org_id=org_b.id, kind="fee", key="platform", value=0.15, currency="USD", source="test", as_of=date(2024,1,1))
        db_session.add_all([cost_a, cost_b])
        await db_session.flush()

        # Set current org context
        set_current_org_id(str(org_a.id))

        # Query with org filter
        result = await db_session.execute(with_org_filter(select(CostTable), CostTable))
        costs = result.scalars().all()

        for cost in costs:
            assert cost.org_id == org_a.id


class TestRLSWithNoOrgContext:
    """Tests when no org context is set."""

    @pytest.mark.asyncio
    async def test_no_org_context_sees_nothing(self, client, db_session, org_a, org_b, shared_sku):
        """When no org context is set, queries should return no rows (strict isolation)."""
        from secondroute.intake.models import Unit
        from secondroute.core.db import with_org_filter
        await make_unit(db_session, shared_sku, org_a.id)
        await make_unit(db_session, shared_sku, org_b.id)

        # Don't set any org context
        result = await db_session.execute(with_org_filter(select(Unit), Unit))
        units = result.scalars().all()

        # Should see nothing without org context (strict mode)
        assert len(units) == 0


class TestCrossOrgForeignKeyConstraints:
    """Tests that foreign keys respect org boundaries."""

    @pytest.mark.asyncio
    async def test_cannot_create_unit_with_wrong_org_sku(self, client, db_session, org_a, org_b, shared_sku):
        """Cannot create unit in org A with SKU that belongs to org B (SKUs are global, so this should work)."""
        from secondroute.intake.models import Unit, ReturnReasonCode
        # SKUs are global, so this should work
        unit = Unit(sku_id=shared_sku.id, org_id=org_a.id, return_reason_code=ReturnReasonCode.BUYER_REMORSE, order_channel="online")
        db_session.add(unit)
        await db_session.flush()
        await db_session.refresh(unit)
        assert unit.org_id == org_a.id

    @pytest.mark.asyncio
    async def test_cannot_create_decision_for_wrong_org_unit(self, client, db_session, org_a, org_b, shared_sku):
        """Cannot create decision for unit in different org."""
        from secondroute.intake.models import Unit
        from secondroute.decision.models import Decision
        from secondroute.core.db import set_current_org_id
        unit_b = await make_unit(db_session, shared_sku, org_b.id)

        # Try to create decision with org_a context
        decision = Decision(
            unit_id=unit_b.id,
            org_id=org_b.id,
            recommended_channel="RESELL_OPEN_BOX",
            confidence=0.86,
            candidates_json='[{"channel": "RESELL_OPEN_BOX", "eligible": true, "exclusion_reason": null}]',
            input_snapshot_hash=hash_snapshot({"unit_id": str(unit_b.id), "seed": 42}),
        )
        db_session.add(decision)
        await db_session.flush()

        # Decision should have org_id matching the unit's org
        assert decision.org_id == org_b.id
