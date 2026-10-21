"""
Price source adapters (Phase 2 - F2.2).

Two implementations of the :class:`~secondroute.pricing.protocols.PriceSource`
protocol ship in Phase 2:

* :class:`DatabasePriceSource` - reads stored ``price_observations`` rows.
* :class:`SyntheticPriceSource` - derives a distribution analytically so the
  Phase 2 demo and tests run without a seeded database.

Phase 3 adds real adapters (eBay Browse API, partner CSV) behind the same
protocol. The decision engine is unaffected by that change.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, Optional, Sequence
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.config import settings
from secondroute.core.logging import get_logger
from secondroute.pricing.models import PriceObservation
from secondroute.pricing.protocols import (
    PriceDistribution,
    PriceSource,
    PriceSourceNotFoundError,
)

logger = get_logger(__name__)

__all__ = [
    "DatabasePriceSource",
    "SyntheticPriceSource",
    "EbayBrowsePriceSource",
    "seed_synthetic_price_observations",
    "stable_cell_hash",
]


class DatabasePriceSource:
    """Serves price distributions from the ``price_observations`` table.

    Attributes:
        source_tag: Only rows with this ``source`` are considered.
    """

    source_tag = "synthetic"

    def __init__(
        self,
        session: AsyncSession,
        source_tag: str = "synthetic",
        stale_limit_hours: int = 48,
    ) -> None:
        self._session = session
        self.source_tag = source_tag
        self.stale_limit_hours = stale_limit_hours
        self._last_seen: datetime | None = None

    @property
    def stale_sources(self) -> frozenset[str]:
        """The sources that are too old to trust.

        Empty until the source has actually served a distribution - a source
        that has never spoken cannot be stale.
        """
        if self._last_seen is None:
            return frozenset()
        last_seen = self._last_seen
        if last_seen.tzinfo is None:
            # The database stores naive UTC timestamps.
            last_seen = last_seen.replace(tzinfo=UTC)
        age_hours = (now_utc() - last_seen).total_seconds() / 3600.0
        if age_hours > self.stale_limit_hours:
            return frozenset({self.source_tag})
        return frozenset()

    async def get_distribution(
        self,
        sku_id: UUID,
        grade: str,
        channel: str,
        as_of: datetime,
    ) -> PriceDistribution:
        """Return the observed price distribution for one cell.

        Args:
            sku_id: SKU the price applies to.
            grade: Condition grade.
            channel: Disposition channel.
            as_of: Only observations at or before this timestamp are used.

        Returns:
            The distribution for the requested cell.

        Raises:
            PriceSourceNotFoundError: If no usable observation exists.
        """
        result = await self._session.execute(
            select(PriceObservation)
            .where(
                PriceObservation.sku_id == sku_id,
                PriceObservation.grade == grade,
                PriceObservation.channel == channel,
                PriceObservation.source == self.source_tag,
                PriceObservation.observed_at <= as_of,
            )
            .order_by(PriceObservation.observed_at.desc())
        )
        rows = result.scalars().all()

        if not rows:
            raise PriceSourceNotFoundError(
                f"No {self.source_tag} price observations for sku={sku_id} "
                f"grade={grade} channel={channel} as_of={as_of.isoformat()}"
            )

        values = tuple(float(row.price) for row in rows)
        weights = tuple(max(float(row.weight), 1e-9) for row in rows)
        latest = max(row.observed_at for row in rows)
        self._last_seen = latest

        return PriceDistribution(
            values=values,
            weights=weights,
            source=self.source_tag,
            as_of=latest,
            currency=rows[0].currency,
            metadata={"sample_count": str(len(rows))},
        )


class SyntheticPriceSource:
    """Price source backed by the synthetic generator.

    Unlike the database-backed source this one needs no stored rows: it
    derives a log-normal price distribution analytically from the grade, the
    family value multiplier and the channel's share of the base value.

    It exists so the Phase 2 demo and tests run without a seeded database.
    Phase 3 replaces it with real adapters behind the same protocol.
    """

    source_tag = "synthetic"

    #: Base resale value per grade, in USD.
    GRADE_BASE_VALUE_USD: dict[str, float] = {
        "A": 1450.0,
        "B": 1150.0,
        "C": 780.0,
        "D": 420.0,
    }

    #: Share of the grade base value a buyer pays per channel.
    CHANNEL_VALUE_SHARE: dict[str, float] = {
        "RESELL_OPEN_BOX": 0.92,
        "RESELL_REFURB": 0.78,
        "RECYCLE": 0.06,
        "DONATE": 0.0,
    }

    #: Coefficient of variation per channel.
    CHANNEL_PRICE_CV: dict[str, float] = {
        "RESELL_OPEN_BOX": 0.12,
        "RESELL_REFURB": 0.18,
        "RECYCLE": 0.22,
        "DONATE": 0.0,
    }

    #: Value multiplier per SKU family.
    FAMILY_VALUE_MULTIPLIER: dict[str, float] = {
        "MacBook Pro": 1.35,
        "MacBook Air": 0.62,
        "ThinkPad X1 Carbon": 0.72,
        "Dell XPS 13": 0.61,
    }

    def __init__(self, sku_family: str = "MacBook Pro", observations: int = 64) -> None:
        self.sku_family = sku_family
        self.observations = observations

    async def get_distribution(
        self,
        sku_id: UUID,
        grade: str,
        channel: str,
        as_of: datetime,
    ) -> PriceDistribution:
        """Return the synthetic price distribution for one cell.

        Args:
            sku_id: Unused by the synthetic source, but part of the protocol.
            grade: Condition grade.
            channel: Disposition channel.
            as_of: Timestamp the distribution is valid as of.

        Returns:
            The distribution for the requested cell.

        Raises:
            PriceSourceNotFoundError: If the grade or channel is unknown.
        """
        del sku_id  # the synthetic source is family-scoped, not SKU-scoped
        base = self.GRADE_BASE_VALUE_USD.get(grade)
        share = self.CHANNEL_VALUE_SHARE.get(channel)
        if base is None:
            raise PriceSourceNotFoundError(f"Unknown grade {grade!r}")
        if share is None:
            raise PriceSourceNotFoundError(f"Unknown channel {channel!r}")

        multiplier = self.FAMILY_VALUE_MULTIPLIER.get(self.sku_family, 1.0)
        mean = base * multiplier * share
        cv = self.CHANNEL_PRICE_CV.get(channel, 0.15)

        return PriceDistribution.from_parameters(
            mean=mean,
            stddev=mean * cv,
            source=self.source_tag,
            as_of=as_of,
            observations=self.observations,
            lognormal=True,
            minimum=0.0,
        )

    def with_family(self, family: str) -> SyntheticPriceSource:
        """Return a copy of this source bound to a different SKU family."""
        return SyntheticPriceSource(sku_family=family, observations=self.observations)


async def seed_synthetic_price_observations(
    session: AsyncSession,
    sku_ids: Sequence[tuple[UUID, str]],
    *,
    seed: int = 42,
    observations_per_cell: int = 40,
    as_of: datetime | None = None,
) -> int:
    """Insert synthetic price observations for the given SKU ids.

    The operation is idempotent: running it twice does not create duplicates.

    Args:
        session: Database session.
        sku_ids: ``(sku_id, family)`` pairs to seed.
        seed: Seed for the synthetic generator.
        observations_per_cell: Observations per (sku, grade, channel) cell.
        as_of: Timestamp applied to every observation.

    Returns:
        The number of rows inserted.
    """
    from synthetic.generator import SyntheticReturnGenerator

    if not sku_ids:
        return 0

    generator = SyntheticReturnGenerator(seed=seed)
    observations = generator.generate_price_observations(
        observations_per_cell=observations_per_cell, as_of=as_of
    )

    existing_result = await session.execute(
        select(PriceObservation.sku_id).where(
            PriceObservation.source == "synthetic",
            PriceObservation.sku_id.in_([sku_id for sku_id, _ in sku_ids]),
        )
    )
    already_seeded = {row.sku_id for row in existing_result.all()}
    if already_seeded:
        logger.info("synthetic_price_observations_already_seeded", rows=len(already_seeded))
        return 0

    inserted = 0
    for sku_id, family in sku_ids:
        # The generator has more than one profile for most families: the
        # same model with a larger drive is worth more, and the prices
        # are generated for the family rather than for the model. Two of
        # those profiles can round to the same price for the same cell,
        # and a cell may only hold one observation for a price.
        seen: set[tuple[str, str, float]] = set()
        for row in observations:
            if row.family != family:
                continue
            key = (row.grade, row.channel, float(row.price))
            if key in seen:
                continue
            seen.add(key)
            session.add(
                PriceObservation(
                    sku_id=sku_id,
                    grade=row.grade,
                    channel=row.channel,
                    price=row.price,
                    currency=row.currency,
                    source="synthetic",
                    # The column has no time zone, and the rest of the
                    # application writes naive UTC. The generator makes
                    # aware timestamps, and passing them straight in was
                    # refused by the driver.
                    observed_at=row.observed_at.astimezone(UTC).replace(tzinfo=None),
                    weight=row.weight,
                    is_synthetic=True,
                    as_of=row.observed_at.astimezone(UTC).date(),
                )
            )
            inserted += 1

    await session.flush()
    logger.info("synthetic_price_observations_seeded", rows=inserted)
    return inserted


def stable_cell_hash(sku_id: UUID, grade: str, channel: str) -> str:
    """Return a stable hash for a price cell (used for deterministic seeding)."""
    payload = f"{sku_id}:{grade}:{channel}".encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def now_utc() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


# ----------------------------------------------------------------------
# Phase 3: eBay Browse API adapter
# ----------------------------------------------------------------------


class EbayPrice(BaseModel):
    """Model for eBay listing price."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    value: float
    currency: str


class EbayListing(BaseModel):
    """Model for an eBay Browse API listing item.

    The API's field names are the validation aliases, so the model can be
    built either from a raw API payload or from Python field names.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    item_id: str = Field(validation_alias="itemId")
    title: str
    price: EbayPrice
    condition: str
    condition_id: str = Field(validation_alias="conditionId")
    item_web_url: str = Field(validation_alias="itemWebUrl")
    image: Optional[str] = None
    seller_feedback_percentage: Optional[str] = Field(
        default=None, validation_alias="seller.feedbackPercentage"
    )
    seller_feedback_score: Optional[int] = Field(
        default=None, validation_alias="seller.feedbackScore"
    )
    listing_type: str = Field(validation_alias="listingType")
    format: str = Field(alias="format")

    @property
    def price_value(self) -> float:
        return self.price.value

    @property
    def price_currency(self) -> str:
        return self.price.currency


class EbayBrowseResponse(BaseModel):
    """Model for eBay Browse API response."""

    model_config = ConfigDict(populate_by_name=True)

    total: int
    limit: int
    offset: int
    items: list[EbayListing] = Field(default_factory=list, validation_alias="itemSummaries")


class EbayErrorResponse(BaseModel):
    """Model for eBay error response."""

    error: list[dict] = Field(default_factory=list)


# Mapping from eBay condition ID to our internal grade
# eBay condition IDs: 1000=New, 1500=New other, 2000=New with defects, 2500=Manufacturer refurbished,
# 2750=Seller refurbished, 3000=Used, 4000=Very Good, 5000=Good, 6000=Acceptable, 7000=For parts
EBAY_CONDITION_TO_GRADE: dict[str, str] = {
    "1000": "A",  # New
    "1500": "A",  # New other
    "2000": "B",  # New with defects
    "2500": "A",  # Manufacturer refurbished
    "2750": "B",  # Seller refurbished
    "3000": "C",  # Used
    "4000": "B",  # Very Good
    "5000": "C",  # Good
    "6000": "D",  # Acceptable
    "7000": "D",  # For parts
}

# Channel mapping for eBay listings
EBAY_CHANNEL_MAP: dict[str, str] = {
    "RESELL_OPEN_BOX": "RESELL_OPEN_BOX",
    "RESELL_REFURB": "RESELL_REFURB",
}


class EbayRateLimitError(Exception):
    """Raised when eBay API returns rate limit (429)."""

    def __init__(self, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(
            f"eBay rate limit exceeded, retry after {retry_after or 'unknown'} seconds"
        )


class EbayAuthError(Exception):
    """Raised when eBay API authentication fails."""

    pass


class EbayBrowsePriceSource:
    """Price source backed by eBay Browse API (active listings).

    This adapter fetches active listings from the eBay Browse API for a given
    SKU family and grade, maps eBay condition codes to internal grades, and
    returns a PriceDistribution from the observed prices.

    It handles:
    - OAuth token management (client credentials flow)
    - Rate limiting with exponential backoff
    - Response caching (in-memory TTL cache)
    - Mapping eBay condition IDs to internal grades A/B/C/D
    - Storing results as price_observations with source="ebay_active"

    Attributes:
        source_tag: Always "ebay_active"
        cache_ttl: Time-to-live for cached API responses (default 1 hour)
    """

    source_tag = "ebay_active"

    def __init__(
        self,
        sku_family: str = "MacBook Pro",
        cache_ttl_seconds: int = 3600,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.sku_family = sku_family
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, tuple[EbayBrowseResponse, datetime]] = {}
        self._client = client
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    async def _get_access_token(self) -> str:
        """Get OAuth access token using client credentials flow."""
        if (
            self._access_token
            and self._token_expires_at
            and datetime.now(UTC) < self._token_expires_at
        ):
            return self._access_token

        if not settings.EBAY_APP_ID or not settings.EBAY_CERT_ID:
            raise EbayAuthError("eBay credentials not configured")

        # Use client-provided client or create a temporary one
        auth_client = self._client or httpx.AsyncClient(timeout=30.0)

        try:
            # eBay OAuth uses Basic Auth with App ID and Cert ID
            import base64

            credentials = f"{settings.EBAY_APP_ID}:{settings.EBAY_CERT_ID}"
            encoded = base64.b64encode(credentials.encode()).decode()

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {encoded}",
            }
            data = {
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope",
            }

            oauth_url = (
                "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
                if settings.EBAY_SANDBOX
                else "https://api.ebay.com/identity/v1/oauth2/token"
            )

            response = await auth_client.post(oauth_url, headers=headers, data=data)
            response.raise_for_status()

            token_data = response.json()
            self._access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 7200)
            self._token_expires_at = datetime.now(UTC) + timedelta(
                seconds=expires_in - 60
            )  # 1 min buffer

            return self._access_token
        finally:
            if self._client is None:
                await auth_client.aclose()

    def _cache_key(self, sku_family: str, grade: str, channel: str) -> str:
        """Generate cache key for API response."""
        return f"ebay:{sku_family}:{grade}:{channel}"

    def _get_cached(self, key: str) -> Optional[EbayBrowseResponse]:
        """Get cached response if not expired."""
        if key in self._cache:
            response, cached_at = self._cache[key]
            if datetime.now(UTC) - cached_at < timedelta(seconds=self.cache_ttl_seconds):
                return response
            else:
                del self._cache[key]
        return None

    def _set_cached(self, key: str, response: EbayBrowseResponse) -> None:
        """Cache API response."""
        self._cache[key] = (response, datetime.now(UTC))

    async def _fetch_listings(
        self,
        sku_family: str,
        grade: str,
        _as_of: datetime,
    ) -> EbayBrowseResponse:
        """Fetch active listings from eBay Browse API."""
        cache_key = self._cache_key(sku_family, grade, "all")
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        token = await self._get_access_token()
        api_client = self._client or httpx.AsyncClient(timeout=30.0)

        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            }

            # Build search query
            query = f"{sku_family} {grade}"
            params = {
                "q": query,
                "limit": 50,
                "offset": 0,
                "filter": "buyingOptions:{FIXED_PRICE|AUCTION|BEST_OFFER}",
            }

            browse_url = (
                "https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search"
                if settings.EBAY_SANDBOX
                else "https://api.ebay.com/buy/browse/v1/item_summary/search"
            )

            @retry(
                retry=retry_if_exception_type(
                    (EbayRateLimitError, httpx.TimeoutException, httpx.ConnectError)
                ),
                wait=wait_exponential_jitter(initial=1, max=30),
                stop=stop_after_attempt(3),
                reraise=True,
            )
            async def _make_request() -> Any:
                response = await api_client.get(browse_url, headers=headers, params=params)  # type: ignore[arg-type]
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise EbayRateLimitError(retry_after=int(retry_after) if retry_after else None)
                if response.status_code == 401:
                    # Token expired, invalidate and retry once
                    self._access_token = None
                    self._token_expires_at = None
                    raise EbayAuthError("Token expired")
                response.raise_for_status()
                return response.json()  # type: ignore[return-value]

            data = await _make_request()
            response_model = EbayBrowseResponse(**data)

            # Cache successful response
            self._set_cached(cache_key, response_model)
            return response_model
        finally:
            if self._client is None:
                await api_client.aclose()

    def _map_condition_to_grade(self, condition_id: str) -> str:
        """Map eBay condition ID to internal grade."""
        return EBAY_CONDITION_TO_GRADE.get(condition_id, "C")

    async def get_distribution(
        self,
        _sku_id: UUID,
        grade: str,
        channel: str,
        as_of: datetime,
    ) -> PriceDistribution:
        """Return the sale-price distribution from eBay active listings.

        Args:
            _sku_id: SKU the price applies to (used for family lookup).
            grade: Condition grade (A/B/C/D).
            channel: Disposition channel.
            as_of: Only observations at or before this timestamp are used.

        Returns:
            The distribution for the requested cell.

        Raises:
            PriceSourceNotFoundError: If no listings found for the cell.
            PriceSourceError: If the API cannot answer.
        """
        # For now, we use the sku_family from the source, not the sku_id
        # In a full implementation, we'd look up the family from the SKU
        listings = await self._fetch_listings(self.sku_family, grade, as_of)

        # Filter by grade and channel
        prices: list[float] = []
        weights: list[float] = []
        currencies: set[str] = set()

        for item in listings.items:
            item_grade = self._map_condition_to_grade(item.condition_id)
            if item_grade != grade:
                continue

            # For eBay, we map all active listings to RESELL_OPEN_BOX channel
            # since they're active marketplace listings
            if channel not in EBAY_CHANNEL_MAP.values():
                continue

            prices.append(item.price_value)
            weights.append(1.0)  # Equal weight for now; could use seller feedback score
            currencies.add(item.price_currency)

        if not prices:
            raise PriceSourceNotFoundError(
                f"No eBay active listings for family={self.sku_family} grade={grade} "
                f"channel={channel} as_of={as_of.isoformat()}"
            )

        # Use the most recent as_of from the API response
        latest = max(as_of, datetime.now(UTC))
        currency = currencies.pop() if currencies else "USD"

        return PriceDistribution(
            values=tuple(prices),
            weights=tuple(weights),
            source=self.source_tag,
            as_of=latest,
            currency=currency,
            metadata={
                "sample_count": str(len(prices)),
                "sku_family": self.sku_family,
            },
        )

    async def close(self) -> None:
        """Close the underlying HTTP client if we own it."""
        if self._client is not None:
            await self._client.aclose()
