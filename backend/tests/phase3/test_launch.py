"""
Tests for the launch calendar and the HOLD channel (F3.8).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone, UTC
from uuid import uuid4

import numpy as np
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.ingest.launch import (
    DEFAULT_HOLD_WINDOW_DAYS,
    fit_decay_params,
    get_decay_param,
    hold_decision,
    launch_probability,
    list_launch_events,
    upsert_launch_event,
)
from secondroute.ingest.models import DecayParam, LaunchEvent

TODAY = date(2025, 6, 1)


def make_launch(
    family: str = "MacBook Pro", *, event_date: date, event_type: str = "successor"
) -> LaunchEvent:
    """Build a launch event for a test."""
    return LaunchEvent(
        sku_family=family,
        event_date=event_date,
        event_type=event_type,
        source_url="https://example.com/announcement",
    )


class TestLaunchProbability:
    """How likely a launch is inside the window."""

    def test_no_launch_means_no_probability(self) -> None:
        """Nothing known means zero probability."""
        assert launch_probability([], today=TODAY) == 0.0

    def test_a_launch_inside_the_window_is_certain(self) -> None:
        """A known launch inside the window is a probability of one."""
        launches = [make_launch(event_date=TODAY + timedelta(days=3))]
        assert launch_probability(launches, today=TODAY) == 1.0

    def test_a_launch_one_day_later_is_inside_the_window(self) -> None:
        """The acceptance criterion: a launch the day after today counts."""
        launches = [make_launch(event_date=TODAY + timedelta(days=1))]
        assert launch_probability(launches, today=TODAY) == 1.0

    def test_a_launch_after_the_window_does_not_count(self) -> None:
        """A launch beyond the window is not a risk."""
        launches = [make_launch(event_date=TODAY + timedelta(days=DEFAULT_HOLD_WINDOW_DAYS + 10))]
        assert launch_probability(launches, today=TODAY) == 0.0

    def test_a_launch_that_has_passed_does_not_count(self) -> None:
        """Yesterday's launch is history."""
        launches = [make_launch(event_date=TODAY - timedelta(days=1))]
        assert launch_probability(launches, today=TODAY) == 0.0


class TestHoldDecision:
    """When holding is on the table."""

    def test_a_launch_next_week_blocks_holding(self) -> None:
        """The acceptance criterion: no HOLD one day before a launch."""
        launches = [make_launch(event_date=TODAY + timedelta(days=1))]
        decision = hold_decision(
            rate_per_day=0.001,  # the price is rising
            launches=launches,
            today=TODAY,
        )
        assert decision.offered is False
        assert "launch" in decision.reason.lower()

    def test_a_rising_price_with_no_launch_offers_holding(self) -> None:
        """The acceptance criterion: HOLD is offered for a rising price."""
        decision = hold_decision(
            rate_per_day=0.002,  # the price is rising
            launches=[],
            today=TODAY,
        )
        assert decision.offered is True
        assert decision.expected_change_p50 > 0
        assert decision.launch_probability == 0.0

    def test_a_falling_price_does_not_offer_holding(self) -> None:
        """When the price is falling, holding is worse than selling."""
        decision = hold_decision(
            rate_per_day=-0.002,
            launches=[],
            today=TODAY,
        )
        assert decision.offered is False
        assert decision.expected_change_p50 < 0

    def test_a_flat_price_does_not_offer_holding(self) -> None:
        """A flat price is not a reason to hold."""
        decision = hold_decision(rate_per_day=0.0, launches=[], today=TODAY)
        assert decision.offered is False

    def test_the_expected_change_compounds(self) -> None:
        """The change over the window is the compounded daily rate."""
        decision = hold_decision(rate_per_day=0.01, launches=[], today=TODAY, window_days=10)
        expected = np.exp(0.1) - 1.0
        assert decision.expected_change_p50 == pytest.approx(expected, rel=1e-6)

    def test_the_decision_serialises(self) -> None:
        """The decision can be serialised."""
        decision = hold_decision(rate_per_day=0.001, launches=[], today=TODAY)
        payload = decision.as_dict()
        assert payload["offered"] is True
        assert "window_days" in payload


class TestDecayFitting:
    """Fitting the decay from the price observations."""

    @pytest.mark.asyncio
    async def test_a_rising_price_gives_a_positive_rate(self, db_session: AsyncSession) -> None:
        """A rising price has a negative decay rate."""
        from datetime import date as date_type

        from secondroute.identity.models import SKU
        from secondroute.pricing.models import PriceObservation

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
            as_of=date_type(2025, 1, 1),
        )
        db_session.add(sku)
        await db_session.flush()

        for index in range(12):
            db_session.add(
                PriceObservation(
                    sku_id=sku.id,
                    grade="B",
                    channel="RESELL_OPEN_BOX",
                    price=1000.0 + index * 20.0,
                    currency="USD",
                    source="partner_a",
                    observed_at=datetime(2025, 1, 1, tzinfo=UTC) + timedelta(days=index),
                    weight=1.0,
                    is_synthetic=False,
                )
            )
        await db_session.flush()

        fitted = await fit_decay_params(db_session, minimum_observations=5)
        assert fitted == 1

        param = await get_decay_param(db_session, sku_family="MacBook Pro", grade="B")
        assert param is not None
        # A rising price has a positive log-slope.
        assert param.rate_per_day > 0

    @pytest.mark.asyncio
    async def test_too_little_data_is_not_fitted(self, db_session: AsyncSession) -> None:
        """A cell with too few observations is left alone."""
        fitted = await fit_decay_params(db_session, minimum_observations=10)
        assert fitted == 0
        rows = (await db_session.execute(select(DecayParam))).scalars().all()
        assert not rows


class TestLaunchEvents:
    """Storing the launch calendar."""

    @pytest.mark.asyncio
    async def test_an_event_is_stored(self, db_session: AsyncSession) -> None:
        """A launch event can be recorded."""
        await upsert_launch_event(
            db_session,
            sku_family="MacBook Pro",
            event_date=TODAY + timedelta(days=30),
            event_type="successor",
            source_url="https://example.com/announcement",
        )
        events = await list_launch_events(db_session)
        assert len(events) == 1
        assert events[0].sku_family == "MacBook Pro"

    @pytest.mark.asyncio
    async def test_the_same_event_is_updated(self, db_session: AsyncSession) -> None:
        """Recording the same event twice does not duplicate it."""
        for _ in range(2):
            await upsert_launch_event(
                db_session,
                sku_family="MacBook Pro",
                event_date=TODAY + timedelta(days=30),
                event_type="successor",
                source_url="https://example.com/announcement",
            )
        events = await list_launch_events(db_session)
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_events_are_filtered_by_family(self, db_session: AsyncSession) -> None:
        """The list can be restricted to one family."""
        await upsert_launch_event(
            db_session,
            sku_family="MacBook Pro",
            event_date=TODAY,
            event_type="successor",
            source_url="https://example.com/a",
        )
        await upsert_launch_event(
            db_session,
            sku_family="MacBook Air",
            event_date=TODAY,
            event_type="successor",
            source_url="https://example.com/b",
        )
        events = await list_launch_events(db_session, sku_family="MacBook Air")
        assert len(events) == 1
        assert events[0].sku_family == "MacBook Air"


class TestHoldPriceSource:
    """The HOLD price source."""

    @pytest.mark.asyncio
    async def test_it_only_serves_the_hold_channel(self) -> None:
        """Another channel is an error."""
        from secondroute.decision.hold import HoldPriceSource
        from secondroute.pricing.sources import SyntheticPriceSource

        source = HoldPriceSource(SyntheticPriceSource(), 0.1, window_days=21)
        with pytest.raises(Exception, match="only serves HOLD"):
            await source.get_distribution(
                uuid4(), "B", "RESELL_OPEN_BOX", datetime(2025, 6, 1, tzinfo=UTC)
            )

    @pytest.mark.asyncio
    async def test_the_price_is_the_expected_future_price(self) -> None:
        """The price is today's price plus the expected change."""
        from secondroute.decision.hold import HoldPriceSource
        from secondroute.pricing.sources import SyntheticPriceSource

        base = SyntheticPriceSource()
        source = HoldPriceSource(base, 0.10, window_days=21)

        today = await base.get_distribution(
            uuid4(), "B", "RESELL_OPEN_BOX", datetime(2025, 6, 1, tzinfo=UTC)
        )
        held = await source.get_distribution(uuid4(), "B", "HOLD", datetime(2025, 6, 1, tzinfo=UTC))

        assert held.mean == pytest.approx(today.mean * 1.10, rel=0.01)
        assert held.metadata["expected_change"] == "0.100000"
