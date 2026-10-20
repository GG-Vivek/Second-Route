"""
Tests for the Wikimedia demand signal (F3.7).
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.config import settings
from secondroute.ingest.demand import (
    WikimediaPageviewsClient,
    WikimediaPageviewsError,
    list_demand_signals,
    pull_demand_signals,
)
from secondroute.ingest.models import DemandSignal

TODAY = date(2025, 6, 1)


def make_transport(responses: list[httpx.Response]) -> httpx.MockTransport:
    """Build a transport that replays a list of responses."""
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        if not queue:
            raise AssertionError("the transport ran out of responses")
        return queue.pop(0)

    return httpx.MockTransport(handler)


def weekly_payload(weeks: int = 3) -> dict:
    """Build a weekly pageview payload."""
    return {
        "items": [
            {
                "timestamp": f"{2025 - (weeks - index) * 1:04d}010100",
                "views": 1000 + index * 10,
            }
            for index in range(weeks)
        ]
    }


class TestWikimediaClient:
    """The pageview client."""

    def test_the_user_agent_is_set(self) -> None:
        """Wikimedia's policy requires a User-Agent that identifies us."""
        client = WikimediaPageviewsClient()
        assert client.user_agent
        assert "SecondRoute" in client.user_agent

    def test_the_user_agent_is_configurable(self) -> None:
        """The User-Agent can be overridden."""
        client = WikimediaPageviewsClient(user_agent="my-agent/1.0")
        assert client.user_agent == "my-agent/1.0"

    @pytest.mark.asyncio
    async def test_the_series_is_parsed(self) -> None:
        """The weekly counts come back oldest first."""
        transport = make_transport([httpx.Response(200, json=weekly_payload(3))])
        http_client = httpx.AsyncClient(transport=transport)
        client = WikimediaPageviewsClient(client=http_client, retry_base_delay=0.0)

        series = await client.fetch_weekly("MacBook_Pro", end=TODAY)
        assert len(series.points) == 3
        assert series.points[0][0] < series.points[-1][0]
        assert series.points[0][1] == 1000

    @pytest.mark.asyncio
    async def test_a_rate_limit_backs_off_and_retries(self) -> None:
        """The acceptance criterion: a 429 is retried."""
        transport = make_transport(
            [
                httpx.Response(429, headers={"Retry-After": "0"}),
                httpx.Response(200, json=weekly_payload(2)),
            ]
        )
        http_client = httpx.AsyncClient(transport=transport)
        client = WikimediaPageviewsClient(client=http_client, retry_base_delay=0.0)

        series = await client.fetch_weekly("MacBook_Pro", end=TODAY)
        assert len(series.points) == 2

    @pytest.mark.asyncio
    async def test_persistent_rate_limiting_is_reported(self) -> None:
        """When it keeps rate limiting, the error says so."""
        transport = make_transport([httpx.Response(429) for _ in range(6)])
        http_client = httpx.AsyncClient(transport=transport)
        client = WikimediaPageviewsClient(client=http_client, retry_base_delay=0.0)

        with pytest.raises(WikimediaPageviewsError, match="did not answer"):
            await client.fetch_weekly("MacBook_Pro", end=TODAY)

    @pytest.mark.asyncio
    async def test_a_missing_article_fails_fast(self) -> None:
        """A 404 is reported immediately."""
        transport = make_transport([httpx.Response(404)])
        http_client = httpx.AsyncClient(transport=transport)
        client = WikimediaPageviewsClient(client=http_client, retry_base_delay=0.0)

        with pytest.raises(WikimediaPageviewsError, match="does not exist"):
            await client.fetch_weekly("Not_An_Article", end=TODAY)

    @pytest.mark.asyncio
    async def test_the_request_carries_the_user_agent(self) -> None:
        """The User-Agent actually goes out on the wire."""
        seen: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request.headers.get("user-agent", ""))
            return httpx.Response(200, json=weekly_payload(1))

        transport = httpx.MockTransport(handler)
        http_client = httpx.AsyncClient(transport=transport)
        client = WikimediaPageviewsClient(
            user_agent="probe-agent/2.0", client=http_client, retry_base_delay=0.0
        )

        await client.fetch_weekly("MacBook_Pro", end=TODAY)
        assert seen
        assert seen[0] == "probe-agent/2.0"

    @pytest.mark.asyncio
    async def test_responses_are_cached(self) -> None:
        """A second call for the same series does not hit the network again."""
        calls: list[int] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(1)
            return httpx.Response(200, json=weekly_payload(2))

        transport = httpx.MockTransport(handler)
        http_client = httpx.AsyncClient(transport=transport)
        client = WikimediaPageviewsClient(client=http_client, retry_base_delay=0.0)

        await client.fetch_weekly("MacBook_Pro", end=TODAY)
        await client.fetch_weekly("MacBook_Pro", end=TODAY)
        assert len(calls) == 1


class TestDemandSignals:
    """Storing the demand series."""

    @pytest.mark.asyncio
    async def test_the_series_is_stored(self, db_session: AsyncSession) -> None:
        """The weekly counts land in the table."""
        transport = make_transport([httpx.Response(200, json=weekly_payload(3))])
        http_client = httpx.AsyncClient(transport=transport)
        client = WikimediaPageviewsClient(client=http_client, retry_base_delay=0.0)

        written = await pull_demand_signals(
            db_session,
            client,
            articles={"MacBook Pro": "MacBook_Pro"},
            end=TODAY,
        )
        assert written == 3

        rows = (await db_session.execute(select(DemandSignal))).scalars().all()
        assert len(rows) == 3
        assert all(row.sku_family == "MacBook Pro" for row in rows)
        assert all(row.source == "wikimedia_pageviews" for row in rows)

    @pytest.mark.asyncio
    async def test_the_query_parameters_are_stored(self, db_session: AsyncSession) -> None:
        """The acceptance criterion: the query parameters are stored."""
        transport = make_transport([httpx.Response(200, json=weekly_payload(2))])
        http_client = httpx.AsyncClient(transport=transport)
        client = WikimediaPageviewsClient(client=http_client, retry_base_delay=0.0)

        await pull_demand_signals(
            db_session,
            client,
            articles={"MacBook Pro": "MacBook_Pro"},
            end=TODAY,
        )

        rows = (await db_session.execute(select(DemandSignal))).scalars().all()
        assert rows
        for row in rows:
            params = json.loads(row.query_params)
            assert params["article"] == "MacBook_Pro"
            assert params["end"] == TODAY.isoformat()
            assert "weeks" in params

    @pytest.mark.asyncio
    async def test_pulling_twice_does_not_duplicate(self, db_session: AsyncSession) -> None:
        """The same week is updated, not added again."""
        transport = make_transport([httpx.Response(200, json=weekly_payload(2)) for _ in range(2)])
        http_client = httpx.AsyncClient(transport=transport)
        client = WikimediaPageviewsClient(client=http_client, retry_base_delay=0.0)

        await pull_demand_signals(
            db_session, client, articles={"MacBook Pro": "MacBook_Pro"}, end=TODAY
        )
        await pull_demand_signals(
            db_session, client, articles={"MacBook Pro": "MacBook_Pro"}, end=TODAY
        )

        rows = (await db_session.execute(select(DemandSignal))).scalars().all()
        assert len(rows) == 2

    @pytest.mark.asyncio
    async def test_a_failed_series_is_skipped(self, db_session: AsyncSession) -> None:
        """One family failing does not stop the others."""
        transport = make_transport(
            [
                httpx.Response(404),
                httpx.Response(200, json=weekly_payload(2)),
            ]
        )
        http_client = httpx.AsyncClient(transport=transport)
        client = WikimediaPageviewsClient(client=http_client, retry_base_delay=0.0)

        written = await pull_demand_signals(
            db_session,
            client,
            articles={"Broken": "Not_An_Article", "Working": "MacBook_Pro"},
            end=TODAY,
        )
        assert written == 2

        rows = await list_demand_signals(db_session)
        assert {row.sku_family for row in rows} == {"Working"}

    def test_the_articles_are_configured(self) -> None:
        """There is an article per family by default."""
        assert settings.WIKIMEDIA_ARTICLES
        assert "MacBook Pro" in settings.WIKIMEDIA_ARTICLES
