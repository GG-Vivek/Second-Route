"""
Tests for the analytics reports (Phase 4 - F4.7).
"""

import json
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.analytics.reports import AnalyticsReportService, decision_is_synthetic
from secondroute.decision.models import Decision
from secondroute.feedback.models import Outcome, Override
from secondroute.identity.models import SKU
from secondroute.intake.models import Inspection, OrderChannel, ReturnReasonCode, Unit


def _candidates(*entries: tuple[str, float]) -> str:
    """Build a candidates_json payload with the given channels and p50 nets."""
    payload = []
    for channel, p50 in entries:
        payload.append(
            {
                "channel": channel,
                "eligible": True,
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
        serial=f"NST{suffix}",
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
    synthetic: bool = True,
    confidence: float = 0.8,
    candidates: str | None = None,
) -> Decision:
    """Create a decision, synthetic or real."""
    decision = Decision(
        unit_id=unit.id,
        model_version="decision-v1",
        risk_profile="balanced",
        recommended_channel="RESELL_OPEN_BOX",
        confidence=confidence,
        fallback_used=False,
        candidates_json=candidates
        if candidates is not None
        else _candidates(("RESELL_OPEN_BOX", 900.0), ("RECYCLE", 100.0)),
        reasons_json="[]",
        flip_conditions_json="[]",
        data_freshness_json=json.dumps({"is_synthetic": synthetic}),
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


async def _make_override(
    db_session: AsyncSession,
    decision: Decision,
    *,
    reason: str = "Customer wanted a faster sale",
    channel: str = "RECYCLE",
) -> Override:
    """Create an override of a decision."""
    override = Override(
        decision_id=decision.id,
        chosen_channel=channel,
        reason_text=reason,
    )
    db_session.add(override)
    await db_session.commit()
    await db_session.refresh(override)
    return override


class TestSyntheticSeparation:
    """Tests that the synthetic and the real data are kept apart."""

    @pytest.mark.asyncio
    async def test_the_decision_is_flagged(self, db_session: AsyncSession) -> None:
        """Test that the synthetic flag comes from the data freshness."""
        unit = await _make_unit(db_session, suffix="1")
        synthetic = await _make_decision(db_session, unit, synthetic=True)
        real = await _make_decision(db_session, unit, synthetic=False)

        assert decision_is_synthetic(synthetic) is True
        assert decision_is_synthetic(real) is False

    @pytest.mark.asyncio
    async def test_the_north_star_is_split(self, db_session: AsyncSession) -> None:
        """Test that a synthetic and a real return land in different sections."""
        unit_a = await _make_unit(db_session, suffix="1")
        decision_a = await _make_decision(db_session, unit_a, synthetic=True)
        await _make_outcome(db_session, unit_a, decision_a, sale_price=900.0, fees=100.0)

        unit_b = await _make_unit(db_session, suffix="2")
        decision_b = await _make_decision(db_session, unit_b, synthetic=False)
        await _make_outcome(db_session, unit_b, decision_b, sale_price=700.0, fees=100.0)

        service = AnalyticsReportService()
        sections = await service.north_star(db_session)

        assert sections["synthetic"].returns_count == 1
        assert sections["real"].returns_count == 1


class TestNorthStar:
    """Tests for the north star."""

    @pytest.mark.asyncio
    async def test_the_observed_baseline_is_used_when_the_channel_was_tried(
        self, db_session: AsyncSession
    ) -> None:
        """Test that the baseline is the realized net when it was tried."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit)
        await _make_outcome(
            db_session, unit, decision, channel="RESELL_OPEN_BOX", sale_price=900.0, fees=100.0
        )
        await _make_outcome(
            db_session, unit, decision, channel="RECYCLE", sale_price=300.0, fees=0.0
        )

        service = AnalyticsReportService()
        sections = await service.north_star(db_session)
        synthetic = sections["synthetic"]

        # Two returns: the resell and the recycle of the same unit.
        assert synthetic.returns_count == 2
        assert synthetic.observed_baseline_count == 2
        assert synthetic.estimated_baseline_count == 0
        assert synthetic.net_recovered_total == pytest.approx(800.0 + 300.0)

    @pytest.mark.asyncio
    async def test_the_estimated_baseline_is_used_when_it_was_not_tried(
        self, db_session: AsyncSession
    ) -> None:
        """Test that the model's prediction is used when the baseline was
        not tried."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit)
        await _make_outcome(
            db_session, unit, decision, channel="RESELL_OPEN_BOX", sale_price=900.0, fees=100.0
        )

        service = AnalyticsReportService()
        sections = await service.north_star(db_session)
        synthetic = sections["synthetic"]

        assert synthetic.returns_count == 1
        assert synthetic.estimated_baseline_count == 1
        assert synthetic.observed_baseline_count == 0
        # The predicted p50 of RECYCLE is 100.
        assert synthetic.baseline_total == pytest.approx(100.0)
        assert synthetic.above_baseline_per_return == pytest.approx(700.0)

    @pytest.mark.asyncio
    async def test_a_return_without_a_baseline_is_left_out(self, db_session: AsyncSession) -> None:
        """Test that a decision with no baseline candidate is not counted."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(
            db_session, unit, candidates=_candidates(("RESELL_OPEN_BOX", 900.0))
        )
        await _make_outcome(db_session, unit, decision)

        service = AnalyticsReportService()
        sections = await service.north_star(db_session)

        assert sections["synthetic"].returns_count == 0


class TestOverrideRate:
    """Tests for the override rate by reason."""

    @pytest.mark.asyncio
    async def test_the_rate_and_the_reasons(self, db_session: AsyncSession) -> None:
        """Test that the override rate and the reasons are right."""
        unit_a = await _make_unit(db_session, suffix="1")
        decision_a = await _make_decision(db_session, unit_a)
        await _make_override(db_session, decision_a, reason="Too risky")

        unit_b = await _make_unit(db_session, suffix="2")
        decision_b = await _make_decision(db_session, unit_b)
        await _make_override(db_session, decision_b, reason="Too risky")

        unit_c = await _make_unit(db_session, suffix="3")
        decision_c = await _make_decision(db_session, unit_c)
        await _make_override(db_session, decision_c, reason="Faster sale")

        service = AnalyticsReportService()
        sections = await service.override_rate(db_session)
        synthetic = sections["synthetic"]

        assert synthetic.decisions_count == 3
        assert synthetic.overrides_count == 3
        assert synthetic.override_rate == pytest.approx(1.0)
        reasons = {entry.reason: entry for entry in synthetic.by_reason}
        assert reasons["Too risky"].count == 2
        assert reasons["Too risky"].share == pytest.approx(2 / 3, abs=1e-4)
        assert reasons["Faster sale"].count == 1

    @pytest.mark.asyncio
    async def test_a_decision_without_an_override_is_counted(
        self, db_session: AsyncSession
    ) -> None:
        """Test that a decision that was not overridden lowers the rate."""
        unit_a = await _make_unit(db_session, suffix="1")
        decision_a = await _make_decision(db_session, unit_a)
        await _make_override(db_session, decision_a)

        unit_b = await _make_unit(db_session, suffix="2")
        await _make_decision(db_session, unit_b)

        service = AnalyticsReportService()
        sections = await service.override_rate(db_session)
        synthetic = sections["synthetic"]

        assert synthetic.decisions_count == 2
        assert synthetic.overrides_count == 1
        assert synthetic.override_rate == pytest.approx(0.5)


class TestAnalyticsEndpoints:
    """Tests for the analytics API."""

    @pytest.mark.asyncio
    async def test_the_north_star_endpoint(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that the north star endpoint returns both sections."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit)
        await _make_outcome(db_session, unit, decision)

        response = await client.get("/api/v1/analytics/north-star")

        assert response.status_code == 200
        data = response.json()
        assert data["baseline_channel"] == "RECYCLE"
        assert data["synthetic"]["returns_count"] == 1
        assert data["real"]["returns_count"] == 0

    @pytest.mark.asyncio
    async def test_the_regret_over_time_endpoint(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that the regret over time endpoint returns the buckets."""
        response = await client.get("/api/v1/analytics/regret-over-time")

        assert response.status_code == 200
        data = response.json()
        assert data["bucket"] == "month"
        assert data["synthetic"] == []
        assert data["real"] == []

    @pytest.mark.asyncio
    async def test_the_regret_over_time_endpoint_rejects_a_bad_bucket(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that an unknown bucket is rejected."""
        response = await client.get("/api/v1/analytics/regret-over-time?bucket=decade")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_the_override_rate_endpoint(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that the override rate endpoint returns both sections."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit)
        await _make_override(db_session, decision)

        response = await client.get("/api/v1/analytics/override-rate")

        assert response.status_code == 200
        data = response.json()
        assert data["synthetic"]["overrides_count"] == 1
        assert data["synthetic"]["by_reason"][0]["reason"] == "Customer wanted a faster sale"
        assert data["real"]["overrides_count"] == 0
