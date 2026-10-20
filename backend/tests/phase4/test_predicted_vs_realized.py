"""
Tests for the predicted vs realized view (Phase 4 - F4.3).
"""

import json
import pytest
from datetime import datetime
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.identity.models import SKU
from secondroute.intake.models import Unit, Inspection, ReturnReasonCode, OrderChannel
from secondroute.decision.models import Decision
from secondroute.feedback.models import Outcome
from secondroute.analytics.predicted_vs_realized import PredictedVsRealizedService


def _candidates(channel: str, p10: float, p50: float, p90: float) -> str:
    """Build a candidates_json payload with one evaluated channel."""
    return json.dumps(
        [
            {
                "channel": channel,
                "eligible": True,
                "mean": p50,
                "stddev": (p90 - p10) / 4,
                "p10": p10,
                "p50": p50,
                "p90": p90,
                "probability_best": 1.0,
                "certainty_equivalent": p50,
                "breakdown": {
                    "sale_price": p50,
                    "fees": 0,
                    "logistics": 0,
                    "handling": 0,
                    "repair": 0,
                    "holding": 0,
                    "total_cost": 0,
                    "net": p50,
                },
            }
        ]
    )


async def _make_unit(db_session: AsyncSession, *, suffix: str = "") -> Unit:
    """Create a unit with an inspection."""
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
        serial=f"TEST{suffix}",
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

    return unit


async def _make_decision(  # noqa: PLR0913
    db_session: AsyncSession,
    unit: Unit,
    *,
    channel: str = "RESELL_OPEN_BOX",
    p10: float = 800.0,
    p50: float = 900.0,
    p90: float = 1000.0,
) -> Decision:
    """Create a decision with a predicted net range."""
    decision = Decision(
        unit_id=unit.id,
        model_version="decision-v1",
        risk_profile="balanced",
        recommended_channel=channel,
        confidence=0.85,
        fallback_used=False,
        candidates_json=_candidates(channel, p10, p50, p90),
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
    sale_price: float = 900.0,
    fees: float = 100.0,
    repair: float = 0.0,
    logistics: float = 0.0,
) -> Outcome:
    """Create an outcome for a decision."""
    outcome = Outcome(
        unit_id=unit.id,
        decision_id=decision.id,
        channel_taken=channel,
        sale_price=sale_price,
        fees_actual=fees,
        repair_cost_actual=repair,
        logistics_actual=logistics,
        days_to_disposition=7,
        final_status="sold",
    )
    db_session.add(outcome)
    await db_session.commit()
    await db_session.refresh(outcome)
    return outcome


class TestPredictedVsRealized:
    """Tests for the predicted vs realized comparison."""

    @pytest.mark.asyncio
    async def test_residual_is_realized_minus_p50(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that the residual is realized net minus predicted p50."""
        unit = await _make_unit(db_session)
        decision = await _make_decision(db_session, unit, p10=800.0, p50=900.0, p90=1000.0)
        # realized net = 900 - 100 = 800; p50 = 900; residual = -100
        await _make_outcome(db_session, unit, decision, sale_price=900.0, fees=100.0)

        response = await client.get(f"/api/v1/analytics/units/{unit.id}/predicted-vs-realized")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["realized_net"] == pytest.approx(800.0)
        assert item["predicted"]["p50"] == pytest.approx(900.0)
        assert item["residual"] == pytest.approx(-100.0)
        assert item["absolute_residual"] == pytest.approx(100.0)

    @pytest.mark.asyncio
    async def test_in_range_when_realized_inside_band(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that a realized net inside [p10, p90] is flagged in range."""
        unit = await _make_unit(db_session)
        decision = await _make_decision(db_session, unit, p10=800.0, p50=900.0, p90=1000.0)
        # realized net = 950
        await _make_outcome(db_session, unit, decision, sale_price=1050.0, fees=100.0)

        response = await client.get(f"/api/v1/analytics/units/{unit.id}/predicted-vs-realized")
        data = response.json()
        item = data["items"][0]

        assert item["in_range"] is True
        assert item["within_p10_p90"] is True
        assert item["below_p10"] is False
        assert item["above_p90"] is False

    @pytest.mark.asyncio
    async def test_below_p10_flag(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test that a realized net below p10 is flagged."""
        unit = await _make_unit(db_session)
        decision = await _make_decision(db_session, unit, p10=800.0, p50=900.0, p90=1000.0)
        # realized net = 500, below p10 of 800
        await _make_outcome(db_session, unit, decision, sale_price=600.0, fees=100.0)

        response = await client.get(f"/api/v1/analytics/units/{unit.id}/predicted-vs-realized")
        item = response.json()["items"][0]

        assert item["in_range"] is False
        assert item["below_p10"] is True
        assert item["above_p90"] is False
        assert item["residual"] == pytest.approx(-400.0)

    @pytest.mark.asyncio
    async def test_above_p90_flag(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test that a realized net above p90 is flagged."""
        unit = await _make_unit(db_session)
        decision = await _make_decision(db_session, unit, p10=800.0, p50=900.0, p90=1000.0)
        # realized net = 1200, above p90 of 1000
        await _make_outcome(db_session, unit, decision, sale_price=1200.0, fees=0.0)

        response = await client.get(f"/api/v1/analytics/units/{unit.id}/predicted-vs-realized")
        item = response.json()["items"][0]

        assert item["in_range"] is False
        assert item["below_p10"] is False
        assert item["above_p90"] is True
        assert item["residual"] == pytest.approx(300.0)

    @pytest.mark.asyncio
    async def test_used_recommended_flag(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that the used_recommended flag is correct."""
        unit = await _make_unit(db_session)
        decision = await _make_decision(db_session, unit, channel="RESELL_OPEN_BOX")
        await _make_outcome(db_session, unit, decision, channel="RESELL_OPEN_BOX")

        response = await client.get(f"/api/v1/analytics/units/{unit.id}/predicted-vs-realized")
        item = response.json()["items"][0]

        assert item["used_recommended"] is True
        assert item["recommended_channel"] == "RESELL_OPEN_BOX"
        assert item["channel"] == "RESELL_OPEN_BOX"

    @pytest.mark.asyncio
    async def test_overridden_channel_has_no_prediction(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that a channel the decision never evaluated has no comparison."""
        unit = await _make_unit(db_session)
        decision = await _make_decision(db_session, unit, channel="RESELL_OPEN_BOX")
        # The operator used a channel the engine never evaluated
        await _make_outcome(db_session, unit, decision, channel="RECYCLE")

        response = await client.get(f"/api/v1/analytics/units/{unit.id}/predicted-vs-realized")
        data = response.json()

        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_unit_with_no_outcomes(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test a unit with no outcomes returns an empty comparison."""
        unit = await _make_unit(db_session)
        await _make_decision(db_session, unit)

        response = await client.get(f"/api/v1/analytics/units/{unit.id}/predicted-vs-realized")
        data = response.json()

        assert data["total"] == 0
        assert data["items"] == []
        assert data["summary"]["total"] == 0

    @pytest.mark.asyncio
    async def test_multiple_outcomes_each_get_a_comparison(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that every recorded outcome gets its own comparison."""
        unit = await _make_unit(db_session)
        decision = await _make_decision(db_session, unit)
        await _make_outcome(db_session, unit, decision, sale_price=900.0, fees=100.0)
        await _make_outcome(db_session, unit, decision, sale_price=800.0, fees=100.0)

        response = await client.get(f"/api/v1/analytics/units/{unit.id}/predicted-vs-realized")
        data = response.json()

        assert data["total"] == 2
        assert len(data["items"]) == 2


class TestPredictedVsRealizedSummary:
    """Tests for the summary statistics."""

    @pytest.mark.asyncio
    async def test_summary_counts(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test that the summary counts are correct."""
        # Unit 1: in range
        unit1 = await _make_unit(db_session, suffix="1")
        decision1 = await _make_decision(db_session, unit1, p10=800.0, p50=900.0, p90=1000.0)
        await _make_outcome(db_session, unit1, decision1, sale_price=1000.0, fees=100.0)

        # Unit 2: below p10
        unit2 = await _make_unit(db_session, suffix="2")
        decision2 = await _make_decision(db_session, unit2, p10=800.0, p50=900.0, p90=1000.0)
        await _make_outcome(db_session, unit2, decision2, sale_price=600.0, fees=100.0)

        response = await client.get("/api/v1/analytics/predicted-vs-realized")
        data = response.json()
        summary = data["summary"]

        assert summary["total"] == 2
        assert summary["in_range_count"] == 1
        assert summary["in_range_rate"] == pytest.approx(0.5)
        assert summary["below_p10_count"] == 1
        assert summary["above_p90_count"] == 0
        assert summary["used_recommended_count"] == 2
        assert summary["mean_absolute_residual"] == pytest.approx(200.0)

    @pytest.mark.asyncio
    async def test_summary_empty(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test that an empty summary has zeroed values."""
        response = await client.get("/api/v1/analytics/predicted-vs-realized")
        data = response.json()

        assert data["total"] == 0
        assert data["items"] == []
        assert data["summary"]["total"] == 0
        assert data["summary"]["in_range_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_summary_service_direct(self, db_session: AsyncSession) -> None:
        """Test the service summary method directly."""
        service = PredictedVsRealizedService()
        summary = service.summarize([])

        assert summary["total"] == 0
        assert summary["mean_residual"] == 0.0
        assert summary["mean_absolute_residual"] == 0.0


class TestPredictedVsRealizedCompareAll:
    """Tests for comparing across all units."""

    @pytest.mark.asyncio
    async def test_compare_all_units(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test that comparisons span every unit."""
        unit1 = await _make_unit(db_session, suffix="1")
        decision1 = await _make_decision(db_session, unit1)
        await _make_outcome(db_session, unit1, decision1)

        unit2 = await _make_unit(db_session, suffix="2")
        decision2 = await _make_decision(db_session, unit2)
        await _make_outcome(db_session, unit2, decision2)

        response = await client.get("/api/v1/analytics/predicted-vs-realized")
        data = response.json()

        assert data["total"] == 2
        assert data["summary"]["total"] == 2
        unit_ids = {item["unit_id"] for item in data["items"]}
        assert len(unit_ids) == 2
