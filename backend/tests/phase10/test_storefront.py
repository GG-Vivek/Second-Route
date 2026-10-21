"""
The public storefront (F10.1).

The shop window shows what is for sale and nothing else. These tests are
mostly about what is *not* on it: the serial number, the reason the
device came back, the notes the operator wrote, the cost of handling it
and the engine's confidence are all the business's own business.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.phase10.conftest import (
    make_decision,
    make_inspection,
    make_photo,
    make_sku,
    make_unit,
)


@pytest.fixture
def org_id(monkeypatch: Any) -> Any:
    """The organisation the storefront shows.

    The deployment names it. A test that wants a different one says so.
    """
    from secondroute.core.config import settings

    org = uuid4()
    monkeypatch.setattr(settings, "PUBLIC_ORG_ID", str(org))
    return org


@pytest.fixture
async def on_sale(db_session: AsyncSession, org_id: Any) -> dict[str, Any]:
    """A device that is for sale."""
    sku = await make_sku(db_session)
    unit = await make_unit(db_session, org_id, sku)
    inspection = await make_inspection(db_session, unit, grade="B", battery="92")
    await make_photo(db_session, unit, inspection)
    await make_decision(db_session, org_id, unit, recommended="RESELL_OPEN_BOX")
    await db_session.commit()
    return {"unit": unit, "sku": sku, "org_id": org_id}


class TestTheWindow:
    """What is on the window."""

    @pytest.mark.asyncio
    async def test_a_device_for_sale_is_listed(
        self, client: AsyncClient, on_sale: dict[str, Any]
    ) -> None:
        """A device the engine said to sell is on the window."""
        response = await client.get("/api/v1/public/listings")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_a_device_for_recycling_is_not(
        self, client: AsyncClient, db_session: AsyncSession, org_id: Any
    ) -> None:
        """A device that is not for sale is not on the window."""
        sku = await make_sku(db_session)
        unit = await make_unit(db_session, org_id, sku)
        await make_decision(db_session, org_id, unit, recommended="RECYCLE")
        await db_session.commit()

        response = await client.get("/api/v1/public/listings")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_the_latest_decision_is_the_one_that_counts(
        self, client: AsyncClient, db_session: AsyncSession, org_id: Any
    ) -> None:
        """A device that was taken off the shelf is not on the window.

        The first decision said to sell it and the second said to
        recycle it. What the business is doing with it now is the
        second one.
        """
        sku = await make_sku(db_session)
        unit = await make_unit(db_session, org_id, sku)
        await make_decision(db_session, org_id, unit, recommended="RESELL_OPEN_BOX", minutes=0)
        await make_decision(db_session, org_id, unit, recommended="RECYCLE", minutes=10)
        await db_session.commit()

        response = await client.get("/api/v1/public/listings")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_a_device_that_has_been_sold_is_not(
        self, client: AsyncClient, db_session: AsyncSession, org_id: Any
    ) -> None:
        """A device that has gone is not on the window."""
        sku = await make_sku(db_session)
        unit = await make_unit(db_session, org_id, sku, status="sold")
        await make_decision(db_session, org_id, unit, recommended="RESELL_OPEN_BOX")
        await db_session.commit()

        response = await client.get("/api/v1/public/listings")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_a_refurbished_device_is_listed(
        self, client: AsyncClient, db_session: AsyncSession, org_id: Any
    ) -> None:
        """Both resale channels put a device on the window."""
        sku = await make_sku(db_session)
        unit = await make_unit(db_session, org_id, sku)
        await make_decision(db_session, org_id, unit, recommended="RESELL_REFURB")
        await db_session.commit()

        response = await client.get("/api/v1/public/listings")
        assert response.status_code == 200
        assert response.json()["total"] == 1


class TestWhatTheWindowDoesNotShow:
    """The business's own business stays inside."""

    @pytest.mark.asyncio
    async def test_the_serial_number_is_not_on_the_window(
        self, client: AsyncClient, on_sale: dict[str, Any]
    ) -> None:
        """The serial number is not for sale, and it is not for reading."""
        response = await client.get("/api/v1/public/listings")
        body = response.text
        assert "SERIAL-SECRET" not in body
        assert "serial" not in body.lower()

    @pytest.mark.asyncio
    async def test_the_notes_and_the_reason_are_not_on_the_window(
        self, client: AsyncClient, on_sale: dict[str, Any]
    ) -> None:
        """Why the device came back is not the buyer's business."""
        response = await client.get("/api/v1/public/listings")
        body = response.text
        assert "The customer said it was slow." not in body
        assert "notes" not in body.lower()
        assert "return_reason" not in body.lower()

    @pytest.mark.asyncio
    async def test_the_costs_are_not_on_the_window(
        self, client: AsyncClient, on_sale: dict[str, Any]
    ) -> None:
        """The margin is the business's own business."""
        response = await client.get("/api/v1/public/listings")
        body = response.text
        assert "net" not in body.lower()
        assert "certainty_equivalent" not in body.lower()
        assert "fees" not in body.lower()
        assert "612.16" not in body  # the net
        assert "790.84" in body  # the sale price

    @pytest.mark.asyncio
    async def test_the_confidence_is_not_on_the_window(
        self, client: AsyncClient, on_sale: dict[str, Any]
    ) -> None:
        """How sure the engine is is not the buyer's business."""
        response = await client.get("/api/v1/public/listings")
        assert "confidence" not in response.text.lower()

    @pytest.mark.asyncio
    async def test_the_organisation_is_not_on_the_window(
        self, client: AsyncClient, on_sale: dict[str, Any]
    ) -> None:
        """Which tenant the stock belongs to is not the buyer's business."""
        response = await client.get("/api/v1/public/listings")
        assert "org_id" not in response.text.lower()


class TestThePrice:
    """What the device is offered at."""

    @pytest.mark.asyncio
    async def test_the_price_is_the_sale_price(
        self, client: AsyncClient, on_sale: dict[str, Any]
    ) -> None:
        """The buyer pays the sale price, not the net."""
        response = await client.get("/api/v1/public/listings")
        item = response.json()["items"][0]
        assert item["price"]["amount"] == 790.84
        assert item["price"]["currency"] == "USD"

    @pytest.mark.asyncio
    async def test_the_price_says_where_it_came_from(
        self, client: AsyncClient, on_sale: dict[str, Any]
    ) -> None:
        """A modelled price is a modelled price, and says so."""
        response = await client.get("/api/v1/public/listings")
        item = response.json()["items"][0]
        assert item["price"]["source"] == "synthetic"
        assert item["price"]["is_estimate"] is True
        assert item["price"]["as_of"]

    @pytest.mark.asyncio
    async def test_the_page_says_the_prices_are_modelled(
        self, client: AsyncClient, on_sale: dict[str, Any]
    ) -> None:
        """Synthetic and real are never mixed without saying so."""
        response = await client.get("/api/v1/public/listings")
        assert response.json()["synthetic"] is True

    @pytest.mark.asyncio
    async def test_a_malformed_decision_is_not_listed(
        self, client: AsyncClient, db_session: AsyncSession, org_id: Any
    ) -> None:
        """A decision that recommends a channel it did not evaluate is not a listing.

        The engine cannot produce one. A hand-written decision can, and a
        device with one has no price to show.
        """
        from secondroute.decision.models import Decision

        sku = await make_sku(db_session)
        unit = await make_unit(db_session, org_id, sku)
        decision = Decision(
            org_id=org_id,
            unit_id=unit.id,
            recommended_channel="RESELL_OPEN_BOX",
            confidence=0.8,
            candidates_json=json.dumps([{"channel": "RECYCLE", "mean": 1.0}]),
            reasons_json="[]",
            flip_conditions_json="[]",
            data_freshness_json="{}",
            action_steps_json="[]",
            input_snapshot_hash="abc123",
            input_snapshot_json="{}",
        )
        db_session.add(decision)
        await db_session.commit()

        response = await client.get("/api/v1/public/listings")
        assert response.status_code == 200
        assert response.json()["total"] == 0
        assert response.json()["items"] == []


class TestTheTenant:
    """Whose stock this is."""

    @pytest.mark.asyncio
    async def test_the_organisation_is_the_one_the_deployment_names(
        self, client: AsyncClient, on_sale: dict[str, Any], monkeypatch: Any
    ) -> None:
        """The deployment chooses the tenant, not the caller."""
        from secondroute.core.config import settings

        other = uuid4()
        monkeypatch.setattr(settings, "PUBLIC_ORG_ID", str(other))

        response = await client.get("/api/v1/public/listings")
        assert response.status_code == 200
        # The stock belongs to another organisation, so there is nothing
        # here.
        assert response.json()["total"] == 0
        assert response.json()["items"] == []

    @pytest.mark.asyncio
    async def test_the_deployment_wins_over_the_caller(
        self, client: AsyncClient, on_sale: dict[str, Any]
    ) -> None:
        """A caller cannot ask for somebody else's stock.

        The shop window shows the stock the deployment pointed it at,
        whatever the caller says. The tenant-isolation policies do the
        rest: a caller cannot see a row that is not theirs, and the
        storefront does not expose anything private in any case.
        """
        other = uuid4()
        response = await client.get(
            "/api/v1/public/listings",
            headers={"X-Org-Id": str(other)},
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_another_tenants_stock_is_not_shown(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch: Any
    ) -> None:
        """One tenant's window does not show another tenant's stock."""
        from secondroute.core.config import settings

        mine = uuid4()
        theirs = uuid4()
        monkeypatch.setattr(settings, "PUBLIC_ORG_ID", str(mine))

        sku = await make_sku(db_session)
        unit = await make_unit(db_session, theirs, sku)
        await make_decision(db_session, theirs, unit, recommended="RESELL_OPEN_BOX")
        await db_session.commit()

        response = await client.get("/api/v1/public/listings")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_the_window_is_empty_without_an_organisation(
        self, client: AsyncClient, monkeypatch: Any
    ) -> None:
        """With nothing to show, the window says so."""
        from secondroute.core.config import settings

        monkeypatch.setattr(settings, "PUBLIC_ORG_ID", "")
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")

        response = await client.get("/api/v1/public/listings")
        assert response.status_code == 404


class TestOneDevice:
    """The page for one device."""

    @pytest.mark.asyncio
    async def test_it_carries_the_photographs(
        self, client: AsyncClient, on_sale: dict[str, Any]
    ) -> None:
        """The photographs are the page."""
        response = await client.get(f"/api/v1/public/listings/{on_sale['unit'].id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["photos"]) == 1
        assert data["photos"][0]["url"].startswith("/uploads/")
        assert data["photos"][0]["alt"]

    @pytest.mark.asyncio
    async def test_it_carries_the_tests_and_the_accessories(
        self, client: AsyncClient, on_sale: dict[str, Any]
    ) -> None:
        """What was tested, and what is in the box."""
        response = await client.get(f"/api/v1/public/listings/{on_sale['unit'].id}")
        data = response.json()
        names = {check["name"] for check in data["checks"]}
        assert names == {"display", "battery"}
        assert [check["passed"] for check in data["checks"]] == [True, False]
        assert data["accessories"] == ["charger"]

    @pytest.mark.asyncio
    async def test_the_grade_is_in_words(
        self, client: AsyncClient, on_sale: dict[str, Any]
    ) -> None:
        """A buyer understands "Good", and not "B"."""
        response = await client.get(f"/api/v1/public/listings/{on_sale['unit'].id}")
        data = response.json()
        assert data["grade"] == "B"
        assert data["condition"] == "Good"

    @pytest.mark.asyncio
    async def test_a_device_that_does_not_exist_is_not_found(
        self, client: AsyncClient, on_sale: dict[str, Any]
    ) -> None:
        """There is no such device."""
        response = await client.get(f"/api/v1/public/listings/{uuid4()}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_a_device_that_is_not_on_sale_is_not_found(
        self, client: AsyncClient, db_session: AsyncSession, org_id: Any
    ) -> None:
        """A device that is not for sale has no page."""
        sku = await make_sku(db_session)
        unit = await make_unit(db_session, org_id, sku)
        await make_decision(db_session, org_id, unit, recommended="RECYCLE")
        await db_session.commit()

        response = await client.get(f"/api/v1/public/listings/{unit.id}")
        assert response.status_code == 404


class TestTheFilters:
    """Finding a device."""

    @pytest.mark.asyncio
    async def test_the_families_are_listed(
        self, client: AsyncClient, on_sale: dict[str, Any]
    ) -> None:
        """The filter says what is on the window."""
        response = await client.get("/api/v1/public/listings")
        assert "MacBook Pro" in response.json()["families"]

    @pytest.mark.asyncio
    async def test_a_family_can_be_asked_for(
        self, client: AsyncClient, on_sale: dict[str, Any]
    ) -> None:
        """Only that family comes back."""
        response = await client.get("/api/v1/public/listings?family=Dell%20XPS%2013")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_a_search_finds_the_model(
        self, client: AsyncClient, on_sale: dict[str, Any]
    ) -> None:
        """The search matches the model."""
        response = await client.get("/api/v1/public/listings?search=M3")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_a_search_that_matches_nothing_finds_nothing(
        self, client: AsyncClient, on_sale: dict[str, Any]
    ) -> None:
        """The search is not a suggestion."""
        response = await client.get("/api/v1/public/listings?search=ThinkPad")
        assert response.status_code == 200
        assert response.json()["total"] == 0
