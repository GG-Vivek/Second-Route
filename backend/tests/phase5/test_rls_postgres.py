"""
Row-level security tests against a real PostgreSQL (F5.2).

The policies are the backstop for any endpoint that forgets to filter by
organisation. A test that only exercises the application-level filter
cannot show that the backstop works, because SQLite has no row-level
security at all.

These tests run against a real PostgreSQL and assert the database's own
behaviour: a query with no organisation filter still returns nothing for
another tenant's rows, and a write into another tenant is rejected.

The connection must not be a superuser, and must not own the tables
without ``FORCE ROW LEVEL SECURITY``: both of those bypass the policies
and would make these tests pass without the isolation being real.
"""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.db import set_session_org_id
from secondroute.feedback.models import AuditLog
from secondroute.identity.models import SKU
from secondroute.identity.organizations import Organization
from secondroute.intake.models import (
    Inspection,
    OrderChannel,
    ReturnReasonCode,
    Unit,
)

pytestmark = pytest.mark.asyncio


async def _make_org(session: AsyncSession, name: str) -> Organization:
    """Create an organisation and act as it from here on.

    The organisations table is not tenant-scoped - it is the list of
    tenants - so creating one needs no context. Everything after this does.

    The rows are flushed rather than committed, because the organisation
    setting is transaction-scoped: a commit would end the transaction and
    take the setting with it. The application works the same way, with one
    transaction per request.

    The organisation's id is assigned here so that the context can be set
    before the flush: the audit row for the organisation is written during
    that flush, and the policy checks the organisation on the write.
    """
    org = Organization(id=uuid4(), name=name, risk_profile="balanced")
    session.add(org)
    await set_session_org_id(session, str(org.id))
    await session.flush()
    await session.refresh(org)
    return org


async def _make_unit(session: AsyncSession, sku: SKU, org: Organization) -> Unit:
    """Create a unit for an organisation.

    The caller must already be acting as that organisation: the policy's
    ``WITH CHECK`` refuses a row for any other tenant, which is the point.
    """
    await set_session_org_id(session, str(org.id))
    unit = Unit(
        sku_id=sku.id,
        org_id=org.id,
        serial=f"S{uuid4().hex[:8].upper()}",
        return_reason_code=ReturnReasonCode.BUYER_REMORSE,
        order_channel=OrderChannel.ONLINE,
    )
    session.add(unit)
    await session.flush()
    await session.refresh(unit)
    return unit


@pytest.fixture
async def pg_sku(pg_session: AsyncSession) -> SKU:
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
        as_of=date(2026, 1, 1),
    )
    pg_session.add(sku)
    await pg_session.commit()
    await pg_session.refresh(sku)
    return sku


class TestDatabaseLevelIsolation:
    """The database refuses to hand over another tenant's rows."""

    async def test_a_query_with_no_org_filter_hides_another_tenants_units(
        self, pg_session: AsyncSession, pg_sku: SKU
    ):
        """The policy filters the rows, not the application's filter.

        The query below has no ``org_id`` predicate at all. It returns
        nothing because the row-level security policy excludes the other
        tenant's row.
        """
        org_a = await _make_org(pg_session, "Org A")
        org_b = await _make_org(pg_session, "Org B")
        unit_b = await _make_unit(pg_session, pg_sku, org_b)

        await set_session_org_id(pg_session, str(org_a.id))

        result = await pg_session.execute(select(Unit))
        visible = result.scalars().all()

        assert unit_b.id not in {unit.id for unit in visible}

    async def test_a_tenant_sees_its_own_rows(self, pg_session: AsyncSession, pg_sku: SKU):
        org_a = await _make_org(pg_session, "Org A")
        unit_a = await _make_unit(pg_session, pg_sku, org_a)

        await set_session_org_id(pg_session, str(org_a.id))

        result = await pg_session.execute(select(Unit))
        visible = result.scalars().all()

        assert unit_a.id in {unit.id for unit in visible}

    async def test_switching_tenants_switches_what_is_visible(
        self, pg_session: AsyncSession, pg_sku: SKU
    ):
        """The same query sees a different set of rows per tenant."""
        org_a = await _make_org(pg_session, "Org A")
        unit_a = await _make_unit(pg_session, pg_sku, org_a)
        org_b = await _make_org(pg_session, "Org B")
        unit_b = await _make_unit(pg_session, pg_sku, org_b)

        await set_session_org_id(pg_session, str(org_a.id))
        result = await pg_session.execute(select(Unit))
        assert {unit.id for unit in result.scalars().all()} == {unit_a.id}

        await set_session_org_id(pg_session, str(org_b.id))
        result = await pg_session.execute(select(Unit))
        assert {unit.id for unit in result.scalars().all()} == {unit_b.id}

    async def test_no_organisation_context_sees_nothing(
        self, pg_session: AsyncSession, pg_sku: SKU
    ):
        """Without a tenant set, the policies fail closed."""
        org_a = await _make_org(pg_session, "Org A")
        await _make_unit(pg_session, pg_sku, org_a)

        await set_session_org_id(pg_session, None)

        result = await pg_session.execute(select(Unit))
        assert result.scalars().all() == []

    async def test_writing_into_another_tenant_is_rejected(
        self, pg_session: AsyncSession, pg_sku: SKU
    ):
        """A row for a tenant the session does not act for cannot be written.

        The write is refused by the policy's ``WITH CHECK``, not by the
        application.
        """
        org_a = await _make_org(pg_session, "Org A")
        org_b = await _make_org(pg_session, "Org B")

        await set_session_org_id(pg_session, str(org_a.id))

        intruder = Unit(
            sku_id=pg_sku.id,
            org_id=org_b.id,
            serial=f"S{uuid4().hex[:8].upper()}",
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        pg_session.add(intruder)

        with pytest.raises(DBAPIError, match="row-level security"):
            await pg_session.commit()

        await pg_session.rollback()

    async def test_inspections_are_isolated_through_their_unit(
        self, pg_session: AsyncSession, pg_sku: SKU
    ):
        """An inspection has no ``org_id``; the policy follows its unit."""
        org_a = await _make_org(pg_session, "Org A")
        org_b = await _make_org(pg_session, "Org B")
        unit_b = await _make_unit(pg_session, pg_sku, org_b)

        inspection = Inspection(
            unit_id=unit_b.id,
            battery_health_pct="95",
            battery_cycles="120",
            cosmetic_grade="A",
            functional_tests_json="{}",
            activation_lock="none",
            accessories_json="{}",
        )
        pg_session.add(inspection)
        await pg_session.commit()

        await set_session_org_id(pg_session, str(org_a.id))

        result = await pg_session.execute(select(Inspection))
        assert result.scalars().all() == []

    async def test_audit_rows_are_isolated(self, pg_session: AsyncSession, pg_sku: SKU):
        """The audit trail of one tenant is not readable by another."""
        org_a = await _make_org(pg_session, "Org A")
        org_b = await _make_org(pg_session, "Org B")
        await _make_unit(pg_session, pg_sku, org_b)

        # The audit listener writes a row for the unit, in the unit's org.
        await set_session_org_id(pg_session, str(org_b.id))
        result = await pg_session.execute(select(AuditLog).where(AuditLog.entity == "units"))
        assert len(result.scalars().all()) == 1

        await set_session_org_id(pg_session, str(org_a.id))
        result = await pg_session.execute(select(AuditLog).where(AuditLog.entity == "units"))
        assert result.scalars().all() == []

    async def test_the_organisation_setting_is_transaction_local(
        self, pg_session: AsyncSession, pg_sku: SKU
    ):
        """The setting does not outlive the transaction.

        A connection is reused between requests, so a setting that survived
        the transaction would leak one tenant's rows into the next
        request.
        """
        org_a = await _make_org(pg_session, "Org A")
        await _make_unit(pg_session, pg_sku, org_a)

        await set_session_org_id(pg_session, str(org_a.id))
        await pg_session.commit()

        # A fresh transaction on the same connection, with no organisation
        # set, must not see the previous tenant's rows.
        async with pg_session.bind.connect() as conn:  # type: ignore[union-attr]
            await conn.execute(text("SELECT 1"))
            result = await conn.execute(select(Unit))
            assert result.scalars().all() == []
