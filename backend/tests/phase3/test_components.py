"""
Tests for the component prices and the FRED adapter (F3.5).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.config import settings
from secondroute.ingest.components import (
    age_in_days,
    import_component_prices_csv,
    is_stale,
    list_component_prices,
    upsert_component_price,
)
from secondroute.ingest.fred import (
    FredSeriesClient,
    FredSeriesError,
    parse_component_csv,
    pull_component_prices,
)
from secondroute.ingest.models import ComponentPrice

TODAY = date(2025, 6, 1)


def make_transport(responses: list[httpx.Response]) -> httpx.MockTransport:
    """Build a transport that replays a list of responses."""
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        if not queue:
            raise AssertionError("the transport ran out of responses")
        return queue.pop(0)

    return httpx.MockTransport(handler)


class TestStaleness:
    """The freshness limit."""

    def test_a_fresh_price_is_not_stale(self) -> None:
        """A recent price is fine."""
        assert is_stale(TODAY - timedelta(days=10), today=TODAY) is False

    def test_a_price_past_the_limit_is_stale(self) -> None:
        """The acceptance criterion: an old price is flagged stale."""
        limit = settings.COMPONENT_PRICE_FRESHNESS_DAYS
        assert is_stale(TODAY - timedelta(days=limit + 1), today=TODAY) is True

    def test_the_limit_is_configurable(self) -> None:
        """The limit can be overridden per call."""
        assert is_stale(TODAY - timedelta(days=40), today=TODAY, max_age_days=30) is True
        assert is_stale(TODAY - timedelta(days=40), today=TODAY, max_age_days=60) is False

    def test_age_is_reported(self) -> None:
        """The age comes back in days."""
        assert age_in_days(TODAY - timedelta(days=12), today=TODAY) == 12


class TestComponentPriceService:
    """Storing and reading component prices."""

    @pytest.mark.asyncio
    async def test_manual_entry(self, db_session: AsyncSession) -> None:
        """A price can be entered by hand."""
        await upsert_component_price(
            db_session,
            component_type="display",
            price_per_unit=320.0,
            source="partner_quote",
            as_of=TODAY,
        )
        views = await list_component_prices(db_session, today=TODAY)
        assert len(views) == 1
        assert views[0].price_per_unit == 320.0
        assert views[0].source == "partner_quote"
        assert views[0].is_stale is False

    @pytest.mark.asyncio
    async def test_stale_price_is_flagged(self, db_session: AsyncSession) -> None:
        """The acceptance criterion: an old price is flagged in the response."""
        await upsert_component_price(
            db_session,
            component_type="battery",
            price_per_unit=85.0,
            source="partner_quote",
            as_of=TODAY - timedelta(days=400),
        )
        views = await list_component_prices(db_session, today=TODAY)
        assert views[0].is_stale is True
        assert views[0].age_days == 400

    @pytest.mark.asyncio
    async def test_entering_the_same_price_twice_updates_it(self, db_session: AsyncSession) -> None:
        """The same component, source and date is updated, not duplicated."""
        for price in (100.0, 120.0):
            await upsert_component_price(
                db_session,
                component_type="display",
                price_per_unit=price,
                source="partner_quote",
                as_of=TODAY,
            )
        views = await list_component_prices(db_session, today=TODAY)
        assert len(views) == 1
        assert views[0].price_per_unit == 120.0

    @pytest.mark.asyncio
    async def test_filter_by_component(self, db_session: AsyncSession) -> None:
        """The list can be restricted to one component."""
        await upsert_component_price(
            db_session,
            component_type="display",
            price_per_unit=320.0,
            source="s",
            as_of=TODAY,
        )
        await upsert_component_price(
            db_session,
            component_type="battery",
            price_per_unit=85.0,
            source="s",
            as_of=TODAY,
        )
        views = await list_component_prices(db_session, component_type="battery", today=TODAY)
        assert len(views) == 1
        assert views[0].component_type == "battery"


class TestComponentCsvImport:
    """The partner CSV import."""

    def test_csv_is_parsed(self) -> None:
        """The rows come out as dictionaries."""
        content = b"component_type,price_per_unit,as_of\ndisplay,320.00,2025-05-01\n"
        rows = parse_component_csv(content)
        assert len(rows) == 1
        assert rows[0]["component_type"] == "display"

    @pytest.mark.asyncio
    async def test_import_writes_the_prices(self, db_session: AsyncSession) -> None:
        """A good file imports cleanly."""
        content = (
            b"component_type,price_per_unit,as_of\n"
            b"display,320.00,2025-05-01\n"
            b"battery,85.00,2025-05-01\n"
        )
        imported, errors = await import_component_prices_csv(db_session, content, source="partner")
        assert imported == 2
        assert errors == []

    @pytest.mark.asyncio
    async def test_bad_rows_are_reported(self, db_session: AsyncSession) -> None:
        """A bad row is reported, not silently dropped."""
        content = (
            b"component_type,price_per_unit,as_of\n"
            b"display,not-a-number,2025-05-01\n"
            b",50.00,2025-05-01\n"
            b"battery,85.00,not-a-date\n"
        )
        imported, errors = await import_component_prices_csv(db_session, content, source="partner")
        assert imported == 0
        assert len(errors) == 3
        assert any("not a number" in error for error in errors)
        assert any("not a date" in error for error in errors)


class TestFredClient:
    """The FRED adapter."""

    def test_without_a_key_the_client_is_not_configured(self) -> None:
        """No key means no work."""
        client = FredSeriesClient(api_key=None)
        assert client.is_configured is False

    @pytest.mark.asyncio
    async def test_without_a_key_fetching_fails(self) -> None:
        """Fetching without a key is an error, not a silent empty result."""
        client = FredSeriesClient(api_key=None)
        with pytest.raises(FredSeriesError, match="no FRED API key"):
            await client.fetch_series("WPU117")

    @pytest.mark.asyncio
    async def test_observations_are_parsed(self) -> None:
        """The observations come back oldest first."""
        payload = {
            "observations": [
                {"date": "2025-05-01", "value": "121.4"},
                {"date": "2025-04-01", "value": "120.9"},
                {"date": "2025-03-01", "value": "."},
            ]
        }
        transport = make_transport([httpx.Response(200, json=payload)])
        http_client = httpx.AsyncClient(transport=transport)
        client = FredSeriesClient(api_key="key", client=http_client, retry_base_delay=0.0)

        observations = await client.fetch_series("WPU117")
        assert len(observations) == 2
        assert observations[0].date == date(2025, 4, 1)
        assert observations[1].value == pytest.approx(121.4)

    @pytest.mark.asyncio
    async def test_a_rate_limit_is_retried(self) -> None:
        """A 429 is retried and then succeeds."""
        payload = {"observations": [{"date": "2025-05-01", "value": "121.4"}]}
        transport = make_transport(
            [httpx.Response(429, headers={"Retry-After": "0"}), httpx.Response(200, json=payload)]
        )
        http_client = httpx.AsyncClient(transport=transport)
        client = FredSeriesClient(api_key="key", client=http_client, retry_base_delay=0.0)

        observations = await client.fetch_series("WPU117")
        assert len(observations) == 1

    @pytest.mark.asyncio
    async def test_a_missing_series_fails_fast(self) -> None:
        """A 404 is reported immediately; retrying would not help."""
        transport = make_transport([httpx.Response(404)])
        http_client = httpx.AsyncClient(transport=transport)
        client = FredSeriesClient(api_key="key", client=http_client, retry_base_delay=0.0)

        with pytest.raises(FredSeriesError, match="does not exist"):
            await client.fetch_series("NOT_A_SERIES")

    @pytest.mark.asyncio
    async def test_persistent_failure_is_reported(self) -> None:
        """When FRED keeps failing, the error says so."""
        transport = make_transport([httpx.Response(500) for _ in range(6)])
        http_client = httpx.AsyncClient(transport=transport)
        client = FredSeriesClient(api_key="key", client=http_client, retry_base_delay=0.0)

        with pytest.raises(FredSeriesError, match="did not answer"):
            await client.fetch_series("WPU117")

    @pytest.mark.asyncio
    async def test_series_can_be_verified(self) -> None:
        """A series id can be checked."""
        transport = make_transport([httpx.Response(200, json={"series": {}})])
        http_client = httpx.AsyncClient(transport=transport)
        client = FredSeriesClient(api_key="key", client=http_client, retry_base_delay=0.0)
        assert await client.verify_series("WPU117") is True


class TestFredPull:
    """Pulling FRED into the component price table."""

    @pytest.mark.asyncio
    async def test_pull_without_a_key_writes_nothing(self, db_session: AsyncSession) -> None:
        """Without a key the pull is a no-op."""
        client = FredSeriesClient(api_key=None)
        written = await pull_component_prices(db_session, client)
        assert written == 0

    @pytest.mark.asyncio
    async def test_pull_writes_the_prices(self, db_session: AsyncSession) -> None:
        """The series are stored, scaled and tagged with their confidence."""
        payload = {
            "observations": [{"date": "2025-05-01", "value": "100.0"}],
        }
        transport = make_transport(
            [httpx.Response(200, json=payload) for _ in range(len(settings.FRED_SERIES_IDS))]
        )
        http_client = httpx.AsyncClient(transport=transport)
        client = FredSeriesClient(api_key="key", client=http_client, retry_base_delay=0.0)

        written = await pull_component_prices(db_session, client, max_observations=1)
        assert written > 0

        rows = (await db_session.execute(select(ComponentPrice))).scalars().all()
        assert rows
        for row in rows:
            assert row.source.startswith("fred:")
            assert row.confidence_weight < 1.0
            assert row.as_of == date(2025, 5, 1)
