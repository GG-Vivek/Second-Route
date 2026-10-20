"""
Tests for the regret calculation (Phase 4 - F4.5).
"""

import json
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.analytics.models import RegretKind, RegretMeasurement
from secondroute.analytics.regret import RegretService
from secondroute.decision.models import Decision
from secondroute.feedback.models import Outcome
from secondroute.identity.models import SKU
from secondroute.intake.models import Inspection, OrderChannel, ReturnReasonCode, Unit


def _candidates(*entries: tuple[str, float, bool]) -> str:
    """Build a candidates_json payload.

    Each entry is a channel, its predicted p50 net and whether it is
    eligible.
    """
    payload = []
    for channel, p50, eligible in entries:
        payload.append(
            {
                "channel": channel,
                "eligible": eligible,
                "mean": p50,
                "stddev": 50.0,
                "p10": p50 - 100.0,
                "p50": p50,
                "p90": p50 + 100.0,
                "probability_best": 0.5,
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
        )
    return json.dumps(payload)


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
        as_of=date(2024, 1, 15),
    )
    db_session.add(sku)
    await db_session.commit()
    await db_session.refresh(sku)

    unit = Unit(
        sku_id=sku.id,
        serial=f"REG{suffix}",
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


async def _make_decision(
    db_session: AsyncSession,
    unit: Unit,
    *,
    candidates: str,
    recommended: str = "RESELL_OPEN_BOX",
) -> Decision:
    """Create a decision for a unit."""
    decision = Decision(
        unit_id=unit.id,
        model_version="decision-v1",
        risk_profile="balanced",
        recommended_channel=recommended,
        confidence=0.85,
        fallback_used=False,
        candidates_json=candidates,
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
) -> Outcome:
    """Create an outcome for a decision."""
    outcome = Outcome(
        unit_id=unit.id,
        decision_id=decision.id,
        channel_taken=channel,
        sale_price=sale_price,
        fees_actual=fees,
        repair_cost_actual=0.0,
        logistics_actual=0.0,
        days_to_disposition=7,
        final_status="sold",
    )
    db_session.add(outcome)
    await db_session.commit()
    await db_session.refresh(outcome)
    return outcome


class TestObservedRegret:
    """Tests for the regret when more than one channel was tried."""

    @pytest.mark.asyncio
    async def test_regret_is_the_gap_to_the_best_channel(self, db_session: AsyncSession) -> None:
        """Test that the observed regret is the gap to the best outcome."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(
            db_session,
            unit,
            candidates=_candidates(("RESELL_OPEN_BOX", 900.0, True), ("RECYCLE", 50.0, True)),
        )
        # Realized nets: RESELL_OPEN_BOX 800, RECYCLE 850.
        await _make_outcome(db_session, unit, decision, channel="RESELL_OPEN_BOX", sale_price=900.0)
        await _make_outcome(db_session, unit, decision, channel="RECYCLE", sale_price=950.0)

        service = RegretService()
        estimates = await service.measure_unit(db_session, unit.id)

        assert len(estimates) == 2
        by_channel = {estimate.channel_taken: estimate for estimate in estimates}

        resell = by_channel["RESELL_OPEN_BOX"]
        assert resell.regret_kind == RegretKind.OBSERVED
        assert resell.realized_net == pytest.approx(800.0)
        assert resell.best_net == pytest.approx(850.0)
        assert resell.regret == pytest.approx(50.0)
        assert resell.best_channel == "RECYCLE"

        recycle = by_channel["RECYCLE"]
        assert recycle.regret_kind == RegretKind.OBSERVED
        assert recycle.regret == pytest.approx(0.0)
        assert recycle.best_channel == "RECYCLE"

    @pytest.mark.asyncio
    async def test_regret_is_never_negative(self, db_session: AsyncSession) -> None:
        """Test that the regret of the best channel is zero, not negative."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(
            db_session,
            unit,
            candidates=_candidates(("RESELL_OPEN_BOX", 900.0, True), ("RECYCLE", 50.0, True)),
        )
        await _make_outcome(db_session, unit, decision, channel="RESELL_OPEN_BOX", sale_price=900.0)
        await _make_outcome(db_session, unit, decision, channel="RECYCLE", sale_price=100.0)

        service = RegretService()
        estimates = await service.measure_unit(db_session, unit.id)

        assert all(estimate.regret >= 0.0 for estimate in estimates)


class TestEstimatedRegret:
    """Tests for the regret when only one channel was tried."""

    @pytest.mark.asyncio
    async def test_single_outcome_is_estimated(self, db_session: AsyncSession) -> None:
        """Test that a single outcome produces an estimated regret."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(
            db_session,
            unit,
            candidates=_candidates(("RESELL_OPEN_BOX", 900.0, True), ("RECYCLE", 1000.0, True)),
        )
        # Realized net 800; the model expected 1000 from RECYCLE.
        await _make_outcome(db_session, unit, decision, channel="RESELL_OPEN_BOX")

        service = RegretService()
        estimates = await service.measure_unit(db_session, unit.id)

        assert len(estimates) == 1
        estimate = estimates[0]
        assert estimate.regret_kind == RegretKind.ESTIMATED
        assert estimate.method == "estimated-best-predicted-net"
        assert estimate.best_channel == "RECYCLE"
        assert estimate.best_net == pytest.approx(1000.0)
        assert estimate.realized_net == pytest.approx(800.0)
        assert estimate.regret == pytest.approx(200.0)

    @pytest.mark.asyncio
    async def test_ineligible_candidates_are_ignored(self, db_session: AsyncSession) -> None:
        """Test that an ineligible channel is not treated as an alternative."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(
            db_session,
            unit,
            candidates=_candidates(("RESELL_OPEN_BOX", 900.0, True), ("RECYCLE", 5000.0, False)),
        )
        await _make_outcome(db_session, unit, decision, channel="RESELL_OPEN_BOX")

        service = RegretService()
        estimates = await service.measure_unit(db_session, unit.id)

        assert len(estimates) == 1
        assert estimates[0].regret == pytest.approx(0.0)
        assert estimates[0].best_channel == "RESELL_OPEN_BOX"

    @pytest.mark.asyncio
    async def test_no_candidates_gives_zero_regret(self, db_session: AsyncSession) -> None:
        """Test that a decision with no candidates has nothing to regret."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit, candidates=_candidates())
        await _make_outcome(db_session, unit, decision, channel="RESELL_OPEN_BOX")

        service = RegretService()
        estimates = await service.measure_unit(db_session, unit.id)

        assert len(estimates) == 1
        assert estimates[0].regret == pytest.approx(0.0)
        assert estimates[0].regret_kind == RegretKind.ESTIMATED


class TestRegretSummary:
    """Tests for the summary that keeps the two kinds apart."""

    @pytest.mark.asyncio
    async def test_observed_and_estimated_are_separate(self, db_session: AsyncSession) -> None:
        """Test that the summary never adds the two kinds silently."""
        observed_unit = await _make_unit(db_session, suffix="1")
        observed_decision = await _make_decision(
            db_session,
            observed_unit,
            candidates=_candidates(("RESELL_OPEN_BOX", 900.0, True), ("RECYCLE", 50.0, True)),
        )
        await _make_outcome(db_session, observed_unit, observed_decision, channel="RESELL_OPEN_BOX")
        await _make_outcome(
            db_session,
            observed_unit,
            observed_decision,
            channel="RECYCLE",
            sale_price=1000.0,
        )

        estimated_unit = await _make_unit(db_session, suffix="2")
        estimated_decision = await _make_decision(
            db_session,
            estimated_unit,
            candidates=_candidates(("RESELL_OPEN_BOX", 900.0, True), ("RECYCLE", 1000.0, True)),
        )
        await _make_outcome(
            db_session, estimated_unit, estimated_decision, channel="RESELL_OPEN_BOX"
        )

        service = RegretService()
        estimates = await service.measure_all(db_session)
        summary = service.summarize(estimates)

        assert summary.observed_count == 2
        assert summary.estimated_count == 1
        assert summary.is_mixed is True

        rendered = summary.to_dict()
        assert rendered["observed"]["count"] == 2
        assert rendered["estimated"]["count"] == 1
        assert rendered["combined"]["is_mixed"] is True
        assert rendered["combined"]["label"] == "observed + estimated"
        # The observed total is the sum of the two observed regrets.
        assert rendered["observed"]["total_regret"] == pytest.approx(
            rendered["combined"]["total_regret"] - rendered["estimated"]["total_regret"]
        )

    @pytest.mark.asyncio
    async def test_empty_summary(self) -> None:
        """Test that an empty summary has zeroed values."""
        service = RegretService()
        summary = service.summarize([])

        assert summary.observed_count == 0
        assert summary.estimated_count == 0
        assert summary.is_mixed is False
        assert summary.to_dict()["combined"]["label"] == "none"


class TestRegretEndpoint:
    """Tests for the regret API."""

    @pytest.mark.asyncio
    async def test_report_endpoint(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test that the report endpoint returns the estimates."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(
            db_session,
            unit,
            candidates=_candidates(("RESELL_OPEN_BOX", 900.0, True), ("RECYCLE", 1000.0, True)),
        )
        await _make_outcome(db_session, unit, decision, channel="RESELL_OPEN_BOX")

        response = await client.get("/api/v1/analytics/regret")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["regret_kind"] == "estimated"
        assert item["regret"] == pytest.approx(200.0)
        assert data["summary"]["estimated"]["count"] == 1
        assert data["summary"]["observed"]["count"] == 0

    @pytest.mark.asyncio
    async def test_record_endpoint_stores_the_measurement(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that recording the regret appends a row."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(
            db_session,
            unit,
            candidates=_candidates(("RESELL_OPEN_BOX", 900.0, True), ("RECYCLE", 1000.0, True)),
        )
        await _make_outcome(db_session, unit, decision, channel="RESELL_OPEN_BOX")

        response = await client.post(f"/api/v1/analytics/units/{unit.id}/regret")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["regret_kind"] == "estimated"

        stored = (await db_session.execute(select(RegretMeasurement))).scalars().all()
        assert len(stored) == 1
        assert stored[0].regret_kind == RegretKind.ESTIMATED
        assert stored[0].regret == pytest.approx(200.0)

    @pytest.mark.asyncio
    async def test_record_endpoint_is_append_only(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that recording twice adds a second row."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(
            db_session,
            unit,
            candidates=_candidates(("RESELL_OPEN_BOX", 900.0, True), ("RECYCLE", 1000.0, True)),
        )
        await _make_outcome(db_session, unit, decision, channel="RESELL_OPEN_BOX")

        await client.post(f"/api/v1/analytics/units/{unit.id}/regret")
        await client.post(f"/api/v1/analytics/units/{unit.id}/regret")

        stored = (await db_session.execute(select(RegretMeasurement))).scalars().all()
        assert len(stored) == 2

    @pytest.mark.asyncio
    async def test_record_endpoint_with_no_outcomes(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that a unit with no outcomes records nothing."""
        unit = await _make_unit(db_session, suffix="1")

        response = await client.post(f"/api/v1/analytics/units/{unit.id}/regret")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
