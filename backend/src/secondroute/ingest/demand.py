"""
Demand signal from Wikipedia pageviews (Phase 3 - F3.7).

The Wikimedia REST API publishes how many people read each article every
week. It needs no key, but it does require a User-Agent that identifies the
caller - their policy is that anonymous traffic is not welcome.

The count is a *proxy* for demand, not demand itself. It is stored, it is
available to the model, and it is **not** applied to the price in this phase.
The plan is explicit about that: the signal becomes a feature, and a feature
becomes a price only once there is outcome data to prove it should.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone, UTC
from typing import Any, Final, Sequence

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.config import settings
from secondroute.core.logging import get_logger
from secondroute.ingest.models import DemandSignal

logger = get_logger(__name__)

__all__ = [
    "PAGEVIEWS_URL",
    "DemandSeries",
    "WikimediaPageviewsClient",
    "WikimediaPageviewsError",
    "pull_demand_signals",
]

#: The per-article pageview endpoint.
PAGEVIEWS_URL = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
    "en.wikipedia/all-access/user/{article}/weekly"
)

#: How many times a rate-limited request is retried.
MAX_ATTEMPTS: Final[int] = 4

#: The base delay between retries, in seconds.
RETRY_BASE_DELAY: Final[float] = 2.0


class WikimediaPageviewsError(RuntimeError):
    """Raised when the pageview API cannot answer."""


@dataclass(frozen=True, slots=True)
class DemandSeries:
    """A weekly demand series for one article.

    Attributes:
        article: The article the counts are for.
        points: The ``(week_start, views)`` points, oldest first.
        query_params: The parameters that produced the series.
    """

    article: str
    points: tuple[tuple[date, int], ...]
    query_params: dict[str, str]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of the series."""
        return {
            "article": self.article,
            "points": [
                {"week_start": week.isoformat(), "views": views} for week, views in self.points
            ],
            "query_params": dict(self.query_params),
        }


class WikimediaPageviewsClient:
    """A client for the Wikimedia pageview API.

    Attributes:
        user_agent: The User-Agent sent with every request.
        base_url: The per-article endpoint.
    """

    def __init__(
        self,
        user_agent: str | None = None,
        base_url: str = PAGEVIEWS_URL,
        client: httpx.AsyncClient | None = None,
        retry_base_delay: float = RETRY_BASE_DELAY,
    ) -> None:
        self.user_agent = user_agent or settings.WIKIMEDIA_USER_AGENT
        self.base_url = base_url
        self._client = client
        self.retry_base_delay = retry_base_delay
        self._cache: dict[str, tuple[DemandSeries, datetime]] = {}

    async def fetch_weekly(
        self,
        article: str,
        *,
        weeks: int | None = None,
        end: date | None = None,
    ) -> DemandSeries:
        """Fetch the weekly pageview counts for an article.

        Args:
            article: The article title, with underscores.
            weeks: How many weeks to fetch.
            end: The last week to fetch.

        Returns:
            The demand series, oldest first.

        Raises:
            WikimediaPageviewsError: If the API cannot answer.
        """
        weeks = weeks or settings.WIKIMEDIA_WEEKS
        end = end or datetime.now(UTC).date()

        cache_key = f"{article}:{weeks}:{end.isoformat()}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            series, cached_at = cached
            if datetime.now(UTC) - cached_at < timedelta(
                seconds=settings.WIKIMEDIA_CACHE_TTL_SECONDS
            ):
                return series

        params = {
            "per_page": str(min(weeks, 100)),
        }

        client = self._client or httpx.AsyncClient(timeout=30.0)
        delay = self.retry_base_delay
        last_error: Exception | None = None

        try:
            for attempt in range(1, MAX_ATTEMPTS + 1):
                url = self.base_url.format(article=article) + f"/{end.isoformat()}"
                try:
                    response = await client.get(
                        url,
                        params=params,
                        headers={
                            "User-Agent": self.user_agent,
                            "Accept": "application/json",
                        },
                    )
                except httpx.HTTPError as exc:
                    last_error = exc
                    logger.warning("wikimedia_request_retry", article=article, attempt=attempt)
                    await _sleep(delay)
                    delay *= 2
                    continue

                if response.status_code == 429:
                    last_error = WikimediaPageviewsError("rate limited")
                    logger.warning("wikimedia_rate_limited", article=article, attempt=attempt)
                    await _sleep(delay)
                    delay *= 2
                    continue

                if response.status_code >= 500:
                    last_error = WikimediaPageviewsError(str(response.status_code))
                    logger.warning(
                        "wikimedia_server_error",
                        article=article,
                        status=response.status_code,
                        attempt=attempt,
                    )
                    await _sleep(delay)
                    delay *= 2
                    continue

                if response.status_code == 404:
                    raise WikimediaPageviewsError(f"the article {article!r} does not exist")

                response.raise_for_status()
                payload = response.json()

                points: list[tuple[date, int]] = []
                for item in payload.get("items", []):
                    raw_date = item.get("timestamp", "")
                    views = item.get("views")
                    if not raw_date or views is None:
                        continue
                    try:
                        week_start = datetime.strptime(raw_date[:8], "%Y%m%d").date()
                    except ValueError:
                        continue
                    points.append((week_start, int(views)))

                points.sort()
                series = DemandSeries(
                    article=article,
                    points=tuple(points),
                    query_params={
                        "article": article,
                        "weeks": str(weeks),
                        "end": end.isoformat(),
                    },
                )
                self._cache[cache_key] = (series, datetime.now(UTC))
                return series

            raise WikimediaPageviewsError(
                f"the pageview API did not answer for {article!r} after "
                f"{MAX_ATTEMPTS} attempts: {last_error}"
            )
        finally:
            if self._client is None:
                await client.aclose()


async def _sleep(seconds: float) -> None:
    """Sleep, in a way that is easy to patch in tests."""
    import asyncio

    await asyncio.sleep(seconds)


async def pull_demand_signals(
    session: AsyncSession,
    client: WikimediaPageviewsClient | None = None,
    *,
    articles: dict[str, str] | None = None,
    weeks: int | None = None,
    end: date | None = None,
) -> int:
    """Pull the demand series for the configured SKU families.

    The series are stored with the query parameters that produced them, so a
    number on the card can always be traced back to the exact request.

    Args:
        session: Database session.
        client: The pageview client. Built from the configuration when omitted.
        articles: The article per SKU family. Defaults to the configuration.
        weeks: How many weeks to pull.
        end: The last week to pull.

    Returns:
        How many rows were written.
    """
    wikimedia = client or WikimediaPageviewsClient()
    mapping = articles if articles is not None else settings.WIKIMEDIA_ARTICLES
    weeks = weeks or settings.WIKIMEDIA_WEEKS
    end = end or datetime.now(UTC).date()

    written = 0

    for family, article in mapping.items():
        try:
            series = await wikimedia.fetch_weekly(article, weeks=weeks, end=end)
        except WikimediaPageviewsError as exc:
            logger.warning("wikimedia_series_failed", article=article, error=str(exc))
            continue

        for week_start, views in series.points:
            week_end = week_start + timedelta(days=6)
            existing = await session.execute(
                select(DemandSignal).where(
                    DemandSignal.sku_family == family,
                    DemandSignal.period_start == week_start,
                    DemandSignal.period_end == week_end,
                    DemandSignal.source == "wikimedia_pageviews",
                )
            )
            row = existing.scalars().first()
            if row is None:
                row = DemandSignal(
                    sku_family=family,
                    period_start=week_start,
                    period_end=week_end,
                    views=views,
                    source="wikimedia_pageviews",
                    query_params=json.dumps(series.query_params, sort_keys=True),
                )
                session.add(row)
            else:
                row.views = views
                row.query_params = json.dumps(series.query_params, sort_keys=True)
            written += 1

    await session.flush()
    logger.info("demand_signals_pulled", rows=written, families=len(mapping))
    return written


async def list_demand_signals(
    session: AsyncSession, *, sku_family: str | None = None
) -> list[DemandSignal]:
    """List the stored demand signals.

    Args:
        session: Database session.
        sku_family: Restrict to one family.

    Returns:
        The demand signals, oldest first.
    """
    query = select(DemandSignal)
    if sku_family:
        query = query.where(DemandSignal.sku_family == sku_family)
    result = await session.execute(query.order_by(DemandSignal.period_start))
    return list(result.scalars().all())
