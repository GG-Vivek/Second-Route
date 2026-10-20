"""
Tests for the time-to-sell model (Phase 4 - F4.4).
"""

import json
from datetime import date, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.analytics.time_to_sell import (
    Observation,
    TimeToSellService,
    is_sold,
    kaplan_meier,
    survival_median,
    survival_percentile,
)
from secondroute.costs.models import CostKind, CostTable
from secondroute.decision.models import Decision
from secondroute.feedback.models import Outcome
from secondroute.identity.models import SKU
from secondroute.intake.models import Inspection, OrderChannel, ReturnReasonCode, Unit


def _observation(
    duration: int,
    event: bool,
    channel: str = "RESELL_OPEN_BOX",
    grade: str = "A",
) -> Observation:
    """Build one observation."""
    return Observation(
        duration_days=duration,
        event=event,
        channel=channel,
        grade=grade,
    )


class TestKaplanMeier:
    """Tests for the Kaplan-Meier estimator."""

    @pytest.mark.asyncio
    async def test_empty_observations(self) -> None:
        """Test that an empty input gives an empty curve."""
        curve = kaplan_meier([])

        assert curve.is_empty
        assert curve.sample_size == 0
        assert curve.times == []
        assert curve.survival == []

    @pytest.mark.asyncio
    async def test_hand_computed_curve(self) -> None:
        """Test the curve against a hand-computed example.

        Five units, all sold, at 2, 3, 4, 5 and 6 days. The survival
        probability after each day is 4/5, 3/5, 2/5, 1/5 and 0.
        """
        observations = [_observation(day, True) for day in (2, 3, 4, 5, 6)]

        curve = kaplan_meier(observations)

        assert curve.times == [2, 3, 4, 5, 6]
        assert curve.survival == pytest.approx([0.8, 0.6, 0.4, 0.2, 0.0])
        assert curve.at_risk == [5, 4, 3, 2, 1]
        assert curve.events == [1, 1, 1, 1, 1]
        assert curve.censored == [0, 0, 0, 0, 0]
        assert curve.sample_size == 5

    @pytest.mark.asyncio
    async def test_censored_observation_leaves_the_risk_set(self) -> None:
        """Test that a censored unit leaves the risk set without an event."""
        observations = [
            _observation(2, True),
            _observation(3, False),
            _observation(5, True),
        ]

        curve = kaplan_meier(observations)

        assert curve.times == [2, 3, 5]
        assert curve.survival[0] == pytest.approx(2 / 3)
        # Censoring does not change the survival probability.
        assert curve.survival[1] == pytest.approx(2 / 3)
        assert curve.survival[2] == pytest.approx(0.0)
        assert curve.at_risk == [3, 2, 1]
        assert curve.events == [1, 0, 1]
        assert curve.censored == [0, 1, 0]

    @pytest.mark.asyncio
    async def test_tied_events_are_pooled(self) -> None:
        """Test that two events at the same time are handled together."""
        observations = [
            _observation(2, True),
            _observation(2, True),
            _observation(4, True),
        ]

        curve = kaplan_meier(observations)

        assert curve.times == [2, 4]
        assert curve.events == [2, 1]
        assert curve.survival[0] == pytest.approx(1 / 3)
        assert curve.survival[1] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_median_and_percentiles(self) -> None:
        """Test the median and the quartile read off the curve."""
        observations = [_observation(day, True) for day in (2, 3, 4, 5, 6)]

        curve = kaplan_meier(observations)

        assert survival_median(curve) == 4
        assert survival_percentile(curve, 0.25) == 5
        assert survival_percentile(curve, 0.75) == 3

    @pytest.mark.asyncio
    async def test_percentile_out_of_range_raises(self) -> None:
        """Test that a percentile outside 0..1 is rejected."""
        with pytest.raises(ValueError, match="percentile"):
            survival_percentile(kaplan_meier([]), 1.5)

    @pytest.mark.asyncio
    async def test_no_median_when_the_curve_never_drops(self) -> None:
        """Test that a curve with no events has no median."""
        curve = kaplan_meier([_observation(4, False)])

        assert survival_median(curve) is None


class TestSoldStatus:
    """Tests for the event classification."""

    @pytest.mark.asyncio
    async def test_sold_is_an_event(self) -> None:
        """Test that a sold outcome is the event."""
        assert is_sold("sold") is True
        assert is_sold("SOLD") is True
        assert is_sold(" sold ") is True

    @pytest.mark.asyncio
    async def test_other_statuses_are_censored(self) -> None:
        """Test that any other status is censored."""
        assert is_sold("recycled") is False
        assert is_sold("donated") is False
        assert is_sold("held") is False


async def _make_unit(
    db_session: AsyncSession,
    *,
    suffix: str = "",
    grade: str = "A",
) -> Unit:
    """Create a unit with an inspection of the given grade."""
    sku = SKU(
        family="Test",
        model_name=f"Model{suffix}",
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
        serial=f"TTS{suffix}",
        return_reason_code=ReturnReasonCode.BUYER_REMORSE,
        order_channel=OrderChannel.ONLINE,
    )
    db_session.add(unit)
    await db_session.commit()
    await db_session.refresh(unit)

    inspection = Inspection(
        unit_id=unit.id,
        battery_health_pct="95",
        cosmetic_grade=grade,
        functional_tests_json={},
        activation_lock="none",
        accessories_json={},
    )
    db_session.add(inspection)
    await db_session.commit()

    return unit


async def _make_decision(db_session: AsyncSession, unit: Unit) -> Decision:
    """Create a decision for a unit."""
    decision = Decision(
        unit_id=unit.id,
        model_version="decision-v1",
        risk_profile="balanced",
        recommended_channel="RESELL_OPEN_BOX",
        confidence=0.85,
        fallback_used=False,
        candidates_json=json.dumps([]),
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


async def _make_outcome(  # noqa: PLR0913
    db_session: AsyncSession,
    unit: Unit,
    decision: Decision,
    *,
    channel: str = "RESELL_OPEN_BOX",
    days: int = 7,
    status: str = "sold",
) -> Outcome:
    """Create an outcome for a decision."""
    outcome = Outcome(
        unit_id=unit.id,
        decision_id=decision.id,
        channel_taken=channel,
        sale_price=900.0,
        fees_actual=100.0,
        repair_cost_actual=0.0,
        logistics_actual=0.0,
        days_to_disposition=days,
        final_status=status,
    )
    db_session.add(outcome)
    await db_session.commit()
    await db_session.refresh(outcome)
    return outcome


async def _make_prior(
    db_session: AsyncSession,
    *,
    channel: str = "RESELL_OPEN_BOX",
    grade: str = "A",
    days: float = 14.0,
) -> CostTable:
    """Seed the Phase 3 prior of expected days to sell."""
    row = CostTable(
        kind=CostKind.EXPECTED_DAYS_TO_SELL,
        key=f"{channel}:{grade}",
        value=days,
        currency="USD",
        source="phase3-prior",
        as_of=date(2024, 1, 15),
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


class TestTimeToSellService:
    """Tests for the service that builds the cells."""

    @pytest.mark.asyncio
    async def test_cell_uses_the_channel_actually_taken(self, db_session: AsyncSession) -> None:
        """Test that the cell is keyed on the channel the unit went to."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit)
        await _make_outcome(db_session, unit, decision, channel="RECYCLE")

        service = TimeToSellService()
        cells = await service.curves(db_session, min_sample=1)

        assert len(cells) == 1
        assert cells[0].channel == "RECYCLE"
        assert cells[0].grade == "A"

    @pytest.mark.asyncio
    async def test_fallback_below_the_minimum_sample(self, db_session: AsyncSession) -> None:
        """Test that a small cell falls back to the prior."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit)
        await _make_outcome(db_session, unit, decision)
        await _make_prior(db_session, days=14.0)

        service = TimeToSellService()
        cells = await service.curves(db_session, min_sample=10)

        assert len(cells) == 1
        cell = cells[0]
        assert cell.used_fallback is True
        assert cell.sample_size == 1
        assert cell.expected_days == pytest.approx(14.0)
        assert cell.source == "cost_tables"
        assert cell.as_of == date(2024, 1, 15)
        assert cell.curve.is_empty
        assert cell.median_days is None

    @pytest.mark.asyncio
    async def test_curve_used_at_or_above_the_minimum_sample(
        self, db_session: AsyncSession
    ) -> None:
        """Test that a big enough cell uses the curve."""
        for index in range(3):
            unit = await _make_unit(db_session, suffix=str(index))
            decision = await _make_decision(db_session, unit)
            await _make_outcome(db_session, unit, decision, days=index + 1)
        await _make_prior(db_session, days=14.0)

        service = TimeToSellService()
        cells = await service.curves(db_session, min_sample=3)

        assert len(cells) == 1
        cell = cells[0]
        assert cell.used_fallback is False
        assert cell.sample_size == 3
        assert cell.source == "outcomes"
        assert cell.expected_days is None
        assert cell.curve.times == [1, 2, 3]
        assert cell.median_days == 2

    @pytest.mark.asyncio
    async def test_channel_and_grade_filters(self, db_session: AsyncSession) -> None:
        """Test that the filters narrow the cells down."""
        unit_a = await _make_unit(db_session, suffix="1", grade="A")
        decision_a = await _make_decision(db_session, unit_a)
        await _make_outcome(db_session, unit_a, decision_a, channel="RESELL_OPEN_BOX")

        unit_b = await _make_unit(db_session, suffix="2", grade="B")
        decision_b = await _make_decision(db_session, unit_b)
        await _make_outcome(db_session, unit_b, decision_b, channel="RECYCLE")

        service = TimeToSellService()

        by_channel = await service.curves(db_session, channel="RECYCLE", min_sample=1)
        assert len(by_channel) == 1
        assert by_channel[0].channel == "RECYCLE"

        by_grade = await service.curves(db_session, grade="A", min_sample=1)
        assert len(by_grade) == 1
        assert by_grade[0].grade == "A"

    @pytest.mark.asyncio
    async def test_no_outcomes_gives_no_cells(self, db_session: AsyncSession) -> None:
        """Test that a database with no outcomes has no cells."""
        service = TimeToSellService()
        cells = await service.curves(db_session, min_sample=1)

        assert cells == []


class TestTimeToSellEndpoint:
    """Tests for the time-to-sell API."""

    @pytest.mark.asyncio
    async def test_endpoint_returns_the_cells(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that the endpoint returns the cells and the summary."""
        for index in range(3):
            unit = await _make_unit(db_session, suffix=str(index))
            decision = await _make_decision(db_session, unit)
            await _make_outcome(db_session, unit, decision, days=index + 1)

        response = await client.get("/api/v1/analytics/time-to-sell?min_sample=3")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["min_sample"] == 3
        assert data["fallback_count"] == 0
        cell = data["items"][0]
        assert cell["channel"] == "RESELL_OPEN_BOX"
        assert cell["grade"] == "A"
        assert cell["sample_size"] == 3
        assert cell["used_fallback"] is False
        assert cell["source"] == "outcomes"
        assert cell["median_days"] == 2
        assert cell["curve"]["times"] == [1, 2, 3]
        assert cell["curve"]["survival"] == pytest.approx([2 / 3, 1 / 3, 0.0])

    @pytest.mark.asyncio
    async def test_endpoint_reports_the_fallback(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that the endpoint says when the prior was used."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit)
        await _make_outcome(db_session, unit, decision)
        await _make_prior(db_session, days=21.0)

        response = await client.get("/api/v1/analytics/time-to-sell?min_sample=10")

        assert response.status_code == 200
        data = response.json()
        assert data["fallback_count"] == 1
        cell = data["items"][0]
        assert cell["used_fallback"] is True
        assert cell["expected_days"] == pytest.approx(21.0)
        assert cell["source"] == "cost_tables"
        assert cell["as_of"] == "2024-01-15"

    @pytest.mark.asyncio
    async def test_endpoint_with_no_outcomes(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that an empty database returns an empty report."""
        response = await client.get("/api/v1/analytics/time-to-sell")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["fallback_count"] == 0

    @pytest.mark.asyncio
    async def test_endpoint_rejects_a_bad_min_sample(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that min_sample below one is rejected."""
        response = await client.get("/api/v1/analytics/time-to-sell?min_sample=0")

        assert response.status_code == 422
