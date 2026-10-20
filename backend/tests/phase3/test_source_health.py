"""
Tests for the source health and the confidence downgrade (F3.9).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone, UTC

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.admin.health import (
    FRESH,
    MISSING,
    STALE,
    collect_source_health,
    record_source_error,
    record_source_success,
    stale_sources,
)
from secondroute.core.config import settings
from secondroute.ingest.models import SourceHealth
from secondroute.pricing.models import PriceObservation

NOW = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)


class TestSourceHealth:
    """Collecting the health of the sources."""

    @pytest.mark.asyncio
    async def test_a_fresh_source_is_fresh(self, db_session: AsyncSession) -> None:
        """A source that just spoke is fresh."""
        from secondroute.identity.models import SKU

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
            as_of=date(2025, 1, 1),
        )
        db_session.add(sku)
        await db_session.flush()

        db_session.add(
            PriceObservation(
                sku_id=sku.id,
                grade="B",
                channel="RESELL_OPEN_BOX",
                price=1000.0,
                currency="USD",
                source="partner_a",
                observed_at=NOW - timedelta(hours=1),
                weight=1.0,
                is_synthetic=False,
            )
        )
        await db_session.flush()

        statuses = await collect_source_health(db_session, now=NOW)
        partner = next(s for s in statuses if s.source == "partner_a")
        assert partner.status == FRESH
        assert partner.kind == "price"
        assert partner.age_hours == pytest.approx(1.0)
        assert partner.error_count == 0

    @pytest.mark.asyncio
    async def test_an_old_source_is_stale(self, db_session: AsyncSession) -> None:
        """A source that has not spoken for too long is stale."""
        from secondroute.identity.models import SKU

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
            as_of=date(2025, 1, 1),
        )
        db_session.add(sku)
        await db_session.flush()

        db_session.add(
            PriceObservation(
                sku_id=sku.id,
                grade="B",
                channel="RESELL_OPEN_BOX",
                price=1000.0,
                currency="USD",
                source="partner_old",
                observed_at=NOW - timedelta(hours=200),
                weight=1.0,
                is_synthetic=False,
            )
        )
        await db_session.flush()

        statuses = await collect_source_health(db_session, now=NOW)
        old = next(s for s in statuses if s.source == "partner_old")
        assert old.status == STALE
        assert old.is_stale is True
        assert "partner_old" in stale_sources(statuses)

    @pytest.mark.asyncio
    async def test_the_error_count_is_reported(self, db_session: AsyncSession) -> None:
        """A source that has been failing says so."""
        await record_source_error(db_session, "flaky_source", "timeout")
        await record_source_error(db_session, "flaky_source", "timeout again")

        # The source has never produced data, so it is not in the health list
        # yet - but the error is recorded.
        rows = (
            (
                await db_session.execute(
                    select(SourceHealth).where(SourceHealth.source == "flaky_source")
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].error_count == 2
        assert rows[0].last_error_at is not None

    @pytest.mark.asyncio
    async def test_a_success_is_recorded(self, db_session: AsyncSession) -> None:
        """A source that answers has its success recorded."""
        await record_source_success(db_session, "good_source")
        rows = (
            (
                await db_session.execute(
                    select(SourceHealth).where(SourceHealth.source == "good_source")
                )
            )
            .scalars()
            .all()
        )
        assert rows[0].last_success_at is not None
        assert rows[0].error_count == 0

    @pytest.mark.asyncio
    async def test_no_sources_gives_an_empty_list(self, db_session: AsyncSession) -> None:
        """A system with no data has no sources."""
        statuses = await collect_source_health(db_session, now=NOW)
        assert all(status.source for status in statuses)


class TestSourceHealthApi:
    """The health endpoint."""

    @pytest.mark.asyncio
    async def test_the_endpoint_returns_the_sources(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The endpoint reports the sources and a summary."""
        response = await client.get("/api/v1/sources/health")
        assert response.status_code == 200
        data = response.json()
        assert "sources" in data
        assert "summary" in data
        assert data["summary"]["total"] == len(data["sources"])

    @pytest.mark.asyncio
    async def test_the_endpoint_reports_a_stale_source(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """A stale source shows up as stale."""
        from secondroute.identity.models import SKU

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
            as_of=date(2025, 1, 1),
        )
        db_session.add(sku)
        await db_session.flush()
        db_session.add(
            PriceObservation(
                sku_id=sku.id,
                grade="B",
                channel="RESELL_OPEN_BOX",
                price=1000.0,
                currency="USD",
                source="ancient_source",
                observed_at=datetime.now(UTC) - timedelta(days=365),
                weight=1.0,
                is_synthetic=False,
            )
        )
        await db_session.flush()

        response = await client.get("/api/v1/sources/health")
        data = response.json()
        stale = [s for s in data["sources"] if s["source"] == "ancient_source"]
        assert stale
        assert stale[0]["status"] == STALE
        assert data["summary"]["stale"] >= 1


class TestConfidenceDowngrade:
    """A stale source lowers the confidence."""

    @pytest.mark.asyncio
    async def test_a_stale_source_lowers_the_confidence(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The acceptance criterion: a stale source lowers the confidence."""
        from secondroute.identity.models import SKU
        from secondroute.intake.models import Inspection, OrderChannel, ReturnReasonCode, Unit

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
            as_of=date(2025, 1, 1),
        )
        db_session.add(sku)
        await db_session.flush()

        unit = Unit(
            sku_id=sku.id,
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        db_session.add(unit)
        await db_session.flush()
        db_session.add(
            Inspection(
                unit_id=unit.id,
                battery_health_pct="95",
                battery_cycles="120",
                cosmetic_grade="A",
                functional_tests_json='{"display": true}',
                activation_lock="none",
                accessories_json='{"charger": true}',
            )
        )

        # The decision needs prices. These are the observations the database
        # price source serves. Each channel has its own price: open-box
        # sells for the most, recycling recovers very little, donating
        # recovers nothing.
        channel_prices = {
            "RESELL_OPEN_BOX": 1200.0,
            "RESELL_REFURB": 900.0,
            "RECYCLE": 60.0,
            "DONATE": 0.0,
        }
        for grade in ("A", "B", "C", "D"):
            for channel, price in channel_prices.items():
                db_session.add(
                    PriceObservation(
                        sku_id=sku.id,
                        grade=grade,
                        channel=channel,
                        price=price,
                        currency="USD",
                        source="synthetic",
                        observed_at=datetime.now(UTC),
                        weight=1.0,
                        is_synthetic=True,
                    )
                )
        await db_session.flush()

        fresh = await client.post(f"/api/v1/units/{unit.id}/decide")
        assert fresh.status_code == 201
        fresh_data = fresh.json()

        # Now make the price source stale by ageing every observation.
        stale_at = datetime.now(UTC) - timedelta(days=365)
        observations = (await db_session.execute(select(PriceObservation))).scalars().all()
        for observation in observations:
            observation.observed_at = stale_at
        await db_session.flush()

        stale = await client.post(f"/api/v1/units/{unit.id}/decide")
        assert stale.status_code == 201
        stale_data = stale.json()

        assert stale_data["confidence"] < fresh_data["confidence"]
        assert any(
            "stale" in warning.lower() for warning in stale_data["data_freshness"]["warnings"]
        )

    def test_the_degradation_factor_is_configured(self) -> None:
        """The factor is configuration driven."""
        assert 0.0 < settings.CONFIDENCE_DEGRADATION_FACTOR < 1.0
