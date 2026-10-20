"""
Tests for the tenant context (Phase 5 - F5.2).

Two things have to hold for a request to be able to write tenant data:

- the request has to name an organisation, and
- the application has to know which one.

The first is a policy question - a request with no token names no
organisation, and outside production a developer may name one with a
header. The second is a wiring question, and it is the one that was
wrong: the audit listeners were only registered by the test suite, so a
running application recorded no audit rows at all.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from secondroute.api.main import app
from secondroute.feedback import audit
from secondroute.feedback.models import AuditLog
from secondroute.identity.models import SKU
from secondroute.intake.models import Unit


@pytest.fixture
async def sku(db_session) -> SKU:
    """A SKU to hang the units off."""
    from datetime import date

    item = SKU(
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
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


class TestAuditListenersAreRegistered:
    """The running application has to write the audit log."""

    @pytest.mark.asyncio
    async def test_the_startup_registers_them(self, db_session) -> None:
        """Test that the application's startup attaches the listeners.

        The test suite registers them itself, so a test that only checked
        for a row would pass even with the application broken. This one
        takes them off and asks the application to put them back.
        """
        if event.contains(Session, "before_flush", audit._capture_audits):
            event.remove(Session, "before_flush", audit._capture_audits)
        if event.contains(Session, "after_flush", audit._write_audits):
            event.remove(Session, "after_flush", audit._write_audits)
        assert not event.contains(Session, "before_flush", audit._capture_audits)
        async with app.router.lifespan_context(app):
            assert event.contains(Session, "before_flush", audit._capture_audits)
            assert event.contains(Session, "after_flush", audit._write_audits)


class TestOrganisationContext:
    """Which organisation a request acts for."""

    @pytest.mark.asyncio
    async def test_the_header_names_the_organisation(
        self, client: AsyncClient, db_session: AsyncSession, sku: SKU
    ) -> None:
        """Test that the header sets the organisation on the row."""
        from uuid import uuid4

        org_id = str(uuid4())
        response = await client.post(
            "/api/v1/units",
            headers={"X-Org-Id": org_id},
            json={
                "sku_id": str(sku.id),
                "serial": "CTX-1",
                "return_reason_code": "buyer_remorse",
                "order_channel": "online",
            },
        )

        assert response.status_code == 201, response.text
        assert response.json()["org_id"] == org_id

    @pytest.mark.asyncio
    async def test_without_the_header_there_is_no_organisation(
        self, client: AsyncClient, db_session: AsyncSession, sku: SKU
    ) -> None:
        """Test that a request with no tenant owns no rows."""
        response = await client.post(
            "/api/v1/units",
            json={
                "sku_id": str(sku.id),
                "serial": "CTX-2",
                "return_reason_code": "buyer_remorse",
                "order_channel": "online",
            },
        )

        # On SQLite the row is written with no organisation; on PostgreSQL
        # the policies refuse it. Either way the row does not belong to
        # a tenant.
        if response.status_code == 201:
            assert response.json()["org_id"] is None
        else:
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_the_header_is_ignored_in_production(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sku: SKU,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that a production deployment cannot be told its tenant.

        Outside production the header is a convenience. In production it
        has to mean nothing, or a caller could choose a tenant.
        """
        from uuid import uuid4

        from secondroute.core.config import settings

        monkeypatch.setattr(settings, "ENVIRONMENT", "production")

        response = await client.post(
            "/api/v1/units",
            headers={"X-Org-Id": str(uuid4())},
            json={
                "sku_id": str(sku.id),
                "serial": "CTX-3",
                "return_reason_code": "buyer_remorse",
                "order_channel": "online",
            },
        )

        if response.status_code == 201:
            assert response.json()["org_id"] is None
        else:
            assert response.status_code == 403


class TestTheAuditLogIsWritten:
    """A mutation leaves a row behind."""

    @pytest.mark.asyncio
    async def test_a_unit_leaves_a_row(
        self, client: AsyncClient, db_session: AsyncSession, sku: SKU
    ) -> None:
        """Test that creating a unit writes an audit row."""
        from sqlalchemy import select

        response = await client.post(
            "/api/v1/units",
            json={
                "sku_id": str(sku.id),
                "serial": "CTX-4",
                "return_reason_code": "buyer_remorse",
                "order_channel": "online",
            },
        )
        assert response.status_code == 201, response.text
        unit_id = response.json()["id"]

        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity == "units",
                AuditLog.entity_id == unit_id,
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].action == "create"
