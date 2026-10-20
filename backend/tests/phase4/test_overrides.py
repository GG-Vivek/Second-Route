"""
Tests for override with reason (Phase 4 - F4.1).
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
from secondroute.feedback.models import Override


async def _make_decision(db_session: AsyncSession) -> Decision:
    """Create a unit, inspection and decision to override."""
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

    return decision


class TestCreateOverride:
    """Tests for POST /decisions/{id}/override."""

    @pytest.mark.asyncio
    async def test_create_override(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test creating an override with a reason."""
        decision = await _make_decision(db_session)

        response = await client.post(
            f"/api/v1/decisions/{decision.id}/override",
            json={
                "chosen_channel": "RESELL_REFURB",
                "reason_text": "Buyer asked for refurb unit",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["decision_id"] == str(decision.id)
        assert data["chosen_channel"] == "RESELL_REFURB"
        assert data["reason_text"] == "Buyer asked for refurb unit"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_override_without_reason_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that an override without a reason is rejected."""
        decision = await _make_decision(db_session)

        response = await client.post(
            f"/api/v1/decisions/{decision.id}/override",
            json={"chosen_channel": "RESELL_REFURB"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_override_with_blank_reason_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that a whitespace-only reason is rejected."""
        decision = await _make_decision(db_session)

        response = await client.post(
            f"/api/v1/decisions/{decision.id}/override",
            json={"chosen_channel": "RESELL_REFURB", "reason_text": "   "},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_override_without_channel_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that an override without a channel is rejected."""
        decision = await _make_decision(db_session)

        response = await client.post(
            f"/api/v1/decisions/{decision.id}/override",
            json={"reason_text": "Some reason"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_override_nonexistent_decision_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that overriding a non-existent decision returns 404."""
        response = await client.post(
            f"/api/v1/decisions/{uuid4()}/override",
            json={"chosen_channel": "RESELL_REFURB", "reason_text": "Some reason"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_override_is_stored(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that the override is persisted."""
        decision = await _make_decision(db_session)

        await client.post(
            f"/api/v1/decisions/{decision.id}/override",
            json={"chosen_channel": "RESELL_REFURB", "reason_text": "Some reason"},
        )

        result = await db_session.execute(
            select(Override).where(Override.decision_id == decision.id)
        )
        overrides = result.scalars().all()
        assert len(overrides) == 1
        assert overrides[0].chosen_channel == "RESELL_REFURB"
        assert overrides[0].reason_text == "Some reason"

    @pytest.mark.asyncio
    async def test_multiple_overrides_are_appended(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that multiple overrides for one decision are all kept."""
        decision = await _make_decision(db_session)

        await client.post(
            f"/api/v1/decisions/{decision.id}/override",
            json={"chosen_channel": "RESELL_REFURB", "reason_text": "First reason"},
        )
        await client.post(
            f"/api/v1/decisions/{decision.id}/override",
            json={"chosen_channel": "RECYCLE", "reason_text": "Second reason"},
        )

        result = await db_session.execute(
            select(Override).where(Override.decision_id == decision.id)
        )
        overrides = result.scalars().all()
        assert len(overrides) == 2


class TestListOverrides:
    """Tests for listing overrides."""

    @pytest.mark.asyncio
    async def test_list_overrides_for_decision(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test listing the overrides for a decision."""
        decision = await _make_decision(db_session)

        await client.post(
            f"/api/v1/decisions/{decision.id}/override",
            json={"chosen_channel": "RESELL_REFURB", "reason_text": "Some reason"},
        )

        response = await client.get(f"/api/v1/decisions/{decision.id}/overrides")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["chosen_channel"] == "RESELL_REFURB"

    @pytest.mark.asyncio
    async def test_list_overrides_for_unit(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test listing the overrides for a unit."""
        decision = await _make_decision(db_session)

        await client.post(
            f"/api/v1/decisions/{decision.id}/override",
            json={"chosen_channel": "RESELL_REFURB", "reason_text": "Some reason"},
        )

        response = await client.get(f"/api/v1/units/{decision.unit_id}/overrides")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_list_overrides_empty(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test listing overrides when there are none."""
        decision = await _make_decision(db_session)

        response = await client.get(f"/api/v1/decisions/{decision.id}/overrides")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_get_override_by_id(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting one override by ID."""
        decision = await _make_decision(db_session)

        create_response = await client.post(
            f"/api/v1/decisions/{decision.id}/override",
            json={"chosen_channel": "RESELL_REFURB", "reason_text": "Some reason"},
        )
        override_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/overrides/{override_id}")
        assert response.status_code == 200
        assert response.json()["id"] == override_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_override_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting a non-existent override returns 404."""
        response = await client.get(f"/api/v1/overrides/{uuid4()}")
        assert response.status_code == 404


class TestOverrideImmutability:
    """Tests that overrides cannot be edited or deleted through the API."""

    @pytest.mark.asyncio
    async def test_override_cannot_be_updated(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test there is no endpoint to update an override."""
        decision = await _make_decision(db_session)

        create_response = await client.post(
            f"/api/v1/decisions/{decision.id}/override",
            json={"chosen_channel": "RESELL_REFURB", "reason_text": "Some reason"},
        )
        override_id = create_response.json()["id"]

        # PATCH and PUT must not be allowed
        assert (await client.patch(f"/api/v1/overrides/{override_id}", json={})).status_code == 405
        assert (await client.put(f"/api/v1/overrides/{override_id}", json={})).status_code == 405

    @pytest.mark.asyncio
    async def test_override_cannot_be_deleted(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test there is no endpoint to delete an override."""
        decision = await _make_decision(db_session)

        create_response = await client.post(
            f"/api/v1/decisions/{decision.id}/override",
            json={"chosen_channel": "RESELL_REFURB", "reason_text": "Some reason"},
        )
        override_id = create_response.json()["id"]

        assert (await client.delete(f"/api/v1/overrides/{override_id}")).status_code == 405
