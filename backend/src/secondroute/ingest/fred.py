"""
FRED adapter (Phase 3 - F3.5).

FRED (Federal Reserve Economic Data) publishes free economic series. Two of
them are useful as component-price signals: producer price indices for
electronic components and for semiconductors.

A producer price index is an *index*, not a per-unit quote. It tells you the
direction and the rough magnitude of a component's price, not the price
itself. So the value is scaled by a configured factor and stored with a
reduced confidence weight. A decision that leans on a FRED-derived component
price should be trusted less than one that leans on a partner quote, and the
card says so.

No API key means the adapter does nothing rather than failing: the rest of
the system has to work without it.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone, UTC
from typing import Any, Final, Sequence

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.config import settings
from secondroute.core.logging import get_logger
from secondroute.ingest.models import ComponentPrice

logger = get_logger(__name__)

__all__ = [
    "FRED_SERIES_URL",
    "FRED_SERIES_URL_V3",
    "FredObservation",
    "FredSeriesClient",
    "FredSeriesError",
    "pull_component_prices",
]

#: The FRED series endpoint.
FRED_SERIES_URL = "https://api.stlouisfed.org/fred/series/observations"

#: The FRED series metadata endpoint, used to verify a series id.
FRED_SERIES_URL_V3 = "https://api.stlouisfed.org/fred/series"

#: How many times a rate-limited request is retried.
MAX_ATTEMPTS: Final[int] = 4

#: The base delay between retries, in seconds.
RETRY_BASE_DELAY: Final[float] = 1.0


class FredSeriesError(RuntimeError):
    """Raised when FRED cannot answer."""


@dataclass(frozen=True, slots=True)
class FredObservation:
    """One observation of a FRED series.

    Attributes:
        date: The day the observation is for.
        value: The value of the index.
    """

    date: date
    value: float


class FredSeriesClient:
    """A small client for the FRED series endpoints.

    Attributes:
        api_key: The FRED API key.
        base_url: The series observations endpoint.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = FRED_SERIES_URL,
        client: httpx.AsyncClient | None = None,
        retry_base_delay: float = RETRY_BASE_DELAY,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.FRED_API_KEY
        self.base_url = base_url
        self._client = client
        self.retry_base_delay = retry_base_delay

    @property
    def is_configured(self) -> bool:
        """Whether an API key is available."""
        return bool(self.api_key)

    async def fetch_series(
        self,
        series_id: str,
        *,
        start: date | None = None,
        end: date | None = None,
        max_observations: int = 24,
    ) -> list[FredObservation]:
        """Fetch the observations of a series.

        Rate-limited and temporarily failing requests are retried with an
        exponential back-off. A 404 means the series does not exist, which is
        reported straight away - retrying will not help.

        Args:
            series_id: The FRED series id.
            start: The first day to fetch.
            end: The last day to fetch.
            max_observations: How many observations to keep.

        Returns:
            The observations, oldest first.

        Raises:
            FredSeriesError: If the series does not exist or FRED keeps
                failing.
        """
        if not self.is_configured:
            raise FredSeriesError("no FRED API key is configured")

        params: dict[str, Any] = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": "desc",
        }
        if start:
            params["observation_start"] = start.isoformat()
        if end:
            params["observation_end"] = end.isoformat()

        delay = self.retry_base_delay
        last_error: Exception | None = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = await self._get(params)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 404:
                    raise FredSeriesError(f"FRED series {series_id!r} does not exist") from exc
                if status == 429 or status >= 500:
                    last_error = exc
                    logger.warning(
                        "fred_request_retry",
                        series_id=series_id,
                        status=status,
                        attempt=attempt,
                    )
                    await asyncio_sleep(delay)
                    delay *= 2
                    continue
                raise FredSeriesError(f"FRED returned {status} for series {series_id!r}") from exc
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(
                    "fred_request_retry",
                    series_id=series_id,
                    attempt=attempt,
                    error=type(exc).__name__,
                )
                await asyncio_sleep(delay)
                delay *= 2
                continue

            payload = response.json()
            observations = payload.get("observations", [])
            parsed: list[FredObservation] = []
            for item in observations:
                raw_value = item.get("value")
                if raw_value in (None, "."):
                    continue
                try:
                    observed_date = datetime.strptime(item["date"], "%Y-%m-%d").date()
                    value = float(raw_value)
                except (KeyError, TypeError, ValueError):
                    continue
                parsed.append(FredObservation(date=observed_date, value=value))

            parsed.sort(key=lambda observation: observation.date)
            return parsed[-max_observations:]

        raise FredSeriesError(
            f"FRED did not answer for series {series_id!r} after "
            f"{MAX_ATTEMPTS} attempts: {last_error}"
        )

    async def verify_series(self, series_id: str) -> bool:
        """Check that a series id exists.

        Args:
            series_id: The FRED series id.

        Returns:
            True when the series exists.
        """
        if not self.is_configured:
            return False

        params = {"series_id": series_id, "api_key": self.api_key, "file_type": "json"}
        try:
            response = await self._get(params, url=FRED_SERIES_URL_V3)
        except (httpx.HTTPError, FredSeriesError):
            return False
        return response.status_code == 200

    async def _get(self, params: dict[str, Any], url: str | None = None) -> httpx.Response:
        """Perform a GET against FRED."""
        client = self._client or httpx.AsyncClient(timeout=30.0)
        try:
            response = await client.get(url or self.base_url, params=params)
            response.raise_for_status()
            return response
        finally:
            if self._client is None:
                await client.aclose()


async def asyncio_sleep(seconds: float) -> None:
    """Sleep, in a way that is easy to patch in tests."""
    import asyncio

    await asyncio.sleep(seconds)


async def pull_component_prices(
    session: AsyncSession,
    client: FredSeriesClient | None = None,
    *,
    as_of: date | None = None,
    max_observations: int = 4,
) -> int:
    """Pull the configured FRED series into the component price table.

    Args:
        session: Database session.
        client: The FRED client. Built from the configuration when omitted.
        as_of: The date the pulled prices are dated. Defaults to today.
        max_observations: How many observations of each series to store.

    Returns:
        How many rows were written.
    """
    fred = client or FredSeriesClient()
    if not fred.is_configured:
        logger.info("fred_skipped_no_api_key")
        return 0

    as_of = as_of or datetime.now(UTC).date()
    written = 0

    for component_type, series_id in settings.FRED_SERIES_IDS.items():
        scale = settings.FRED_SERIES_SCALE.get(component_type, 1.0)
        confidence = settings.FRED_SERIES_CONFIDENCE.get(component_type, 0.3)

        try:
            observations = await fred.fetch_series(series_id, max_observations=max_observations)
        except FredSeriesError as exc:
            logger.warning("fred_series_failed", series_id=series_id, error=str(exc))
            continue

        for observation in observations:
            price = round(observation.value * scale, 2)
            existing = await session.execute(
                select(ComponentPrice).where(
                    ComponentPrice.component_type == component_type,
                    ComponentPrice.source == f"fred:{series_id}",
                    ComponentPrice.as_of == observation.date,
                )
            )
            row = existing.scalars().first()
            if row is None:
                row = ComponentPrice(
                    component_type=component_type,
                    price_per_unit=price,
                    unit="USD",
                    source=f"fred:{series_id}",
                    as_of=observation.date,
                    confidence_weight=confidence,
                )
                session.add(row)
            else:
                row.price_per_unit = price
                row.confidence_weight = confidence
            written += 1

    await session.flush()
    logger.info("fred_component_prices_pulled", rows=written, as_of=as_of.isoformat())
    return written


def parse_component_csv(content: bytes) -> list[dict[str, Any]]:
    """Parse a partner component price CSV.

    The expected columns are ``component_type``, ``price_per_unit`` and
    ``as_of``. ``unit``, ``source`` and ``confidence_weight`` are optional.

    Args:
        content: The raw file content.

    Returns:
        One dictionary per row.

    Raises:
        ValueError: When the file has no header row.
    """
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("the file has no header row")

    rows: list[dict[str, Any]] = []
    for raw in reader:
        row = {key: (value or "").strip() for key, value in raw.items() if key is not None}
        if not any(row.values()):
            continue
        rows.append(row)
    return rows
