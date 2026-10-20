"""
Tests for the calibration report (Phase 4 - F4.6).
"""

import json
from datetime import date, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.analytics.calibration import (
    CalibrationPoint,
    CalibrationService,
    expected_calibration_error,
    fit_isotonic,
    reliability_curve,
)
from secondroute.analytics.models import CalibrationVersion
from secondroute.decision.models import Decision
from secondroute.feedback.models import Outcome
from secondroute.identity.models import SKU
from secondroute.intake.models import Inspection, OrderChannel, ReturnReasonCode, Unit


class TestReliabilityCurve:
    """Tests for the reliability curve."""

    @pytest.mark.asyncio
    async def test_empty_curve(self) -> None:
        """Test that no observations give an empty curve."""
        curve = reliability_curve([])

        assert curve == []
        assert expected_calibration_error(curve) == 0.0

    @pytest.mark.asyncio
    async def test_bins_are_equal_width(self) -> None:
        """Test that the bins cover [0, 1] in equal steps."""
        observations = [CalibrationPoint(predicted=0.05, observed=True)]
        curve = reliability_curve(observations, bins=10)

        assert len(curve) == 1
        assert curve[0].lower == pytest.approx(0.0)
        assert curve[0].upper == pytest.approx(0.1)
        assert curve[0].count == 1

    @pytest.mark.asyncio
    async def test_the_last_bin_covers_one(self) -> None:
        """Test that a prediction of one lands in the last bin."""
        observations = [CalibrationPoint(predicted=1.0, observed=False)]
        curve = reliability_curve(observations, bins=10)

        assert curve[0].lower == pytest.approx(0.9)
        assert curve[0].upper == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_the_bin_mean_and_frequency(self) -> None:
        """Test the mean prediction and the observed frequency of a bin."""
        observations = [
            CalibrationPoint(predicted=0.25, observed=True),
            CalibrationPoint(predicted=0.28, observed=True),
            CalibrationPoint(predicted=0.29, observed=False),
        ]
        curve = reliability_curve(observations, bins=10)

        assert len(curve) == 1
        assert curve[0].count == 3
        assert curve[0].mean_predicted == pytest.approx((0.25 + 0.28 + 0.29) / 3, abs=1e-6)
        assert curve[0].observed_frequency == pytest.approx(2 / 3)

    @pytest.mark.asyncio
    async def test_a_bad_bin_count_is_rejected(self) -> None:
        """Test that fewer than one bin is rejected."""
        with pytest.raises(ValueError, match="bins"):
            reliability_curve([], bins=0)


class TestExpectedCalibrationError:
    """Tests for the expected calibration error."""

    @pytest.mark.asyncio
    async def test_matches_the_reference_implementation(self) -> None:
        """Test the ECE against a hand-computed reference.

        Two bins: 8 observations predicted at 0.9, of which 6 were right,
        and 2 observations predicted at 0.1, of which 1 was right.

        ECE = 8/10 * |0.75 - 0.9| + 2/10 * |0.5 - 0.1| = 0.12 + 0.08 = 0.20
        """
        observations = [CalibrationPoint(predicted=0.9, observed=True) for _ in range(6)]
        observations += [CalibrationPoint(predicted=0.9, observed=False) for _ in range(2)]
        observations += [CalibrationPoint(predicted=0.1, observed=True)]
        observations += [CalibrationPoint(predicted=0.1, observed=False)]

        curve = reliability_curve(observations, bins=10)
        ece = expected_calibration_error(curve)

        assert ece == pytest.approx(0.20)

    @pytest.mark.asyncio
    async def test_a_perfect_model_has_no_error(self) -> None:
        """Test that a perfectly calibrated model has an ECE of zero."""
        observations = [CalibrationPoint(predicted=1.0, observed=True) for _ in range(10)]
        observations += [CalibrationPoint(predicted=0.0, observed=False) for _ in range(10)]

        curve = reliability_curve(observations, bins=10)

        assert expected_calibration_error(curve) == pytest.approx(0.0)


class TestIsotonic:
    """Tests for the isotonic recalibration."""

    @pytest.mark.asyncio
    async def test_an_overconfident_model_is_pulled_back(self) -> None:
        """Test that the mapping lowers an overconfident prediction."""
        observations = [CalibrationPoint(predicted=0.9, observed=False) for _ in range(10)]

        mapping = fit_isotonic(observations)

        assert mapping.apply(0.9) < 0.9
        assert mapping.apply(0.9) == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_the_mapping_is_non_decreasing(self) -> None:
        """Test that the fitted values never go down."""
        observations = [
            CalibrationPoint(predicted=0.2, observed=False),
            CalibrationPoint(predicted=0.4, observed=True),
            CalibrationPoint(predicted=0.6, observed=False),
            CalibrationPoint(predicted=0.8, observed=True),
        ]

        mapping = fit_isotonic(observations)
        values = [mapping.apply(point / 10) for point in range(11)]

        assert values == sorted(values)

    @pytest.mark.asyncio
    async def test_the_mapping_round_trips(self) -> None:
        """Test that a stored mapping reads back the same."""
        observations = [CalibrationPoint(predicted=0.5, observed=True)]

        mapping = fit_isotonic(observations)
        restored = type(mapping).from_json(mapping.to_json())

        assert restored.points == mapping.points

    @pytest.mark.asyncio
    async def test_an_empty_mapping_is_the_identity(self) -> None:
        """Test that a mapping with no knots changes nothing."""
        mapping = fit_isotonic([])

        assert mapping.apply(0.42) == 0.42


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
        serial=f"CAL{suffix}",
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
    confidence: float = 0.8,
    channel: str = "RESELL_OPEN_BOX",
) -> Decision:
    """Create a decision with a confidence."""
    decision = Decision(
        unit_id=unit.id,
        model_version="decision-v1",
        risk_profile="balanced",
        recommended_channel=channel,
        confidence=confidence,
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


class TestCalibrationService:
    """Tests for the calibration service."""

    @pytest.mark.asyncio
    async def test_a_correct_recommendation_is_observed(self, db_session: AsyncSession) -> None:
        """Test that a decision whose channel realized the best net counts."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit, confidence=0.9)
        await _make_outcome(db_session, unit, decision)

        service = CalibrationService()
        report = await service.report(db_session)

        assert report.sample_size == 1
        assert report.bins[0].observed_frequency == pytest.approx(1.0)
        assert report.ece == pytest.approx(0.1)

    @pytest.mark.asyncio
    async def test_a_wrong_recommendation_is_not_observed(self, db_session: AsyncSession) -> None:
        """Test that a decision whose channel lost is not counted as right."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit, confidence=0.9)
        # A second channel realized a better net.
        await _make_outcome(db_session, unit, decision, channel="RESELL_OPEN_BOX")
        await _make_outcome(db_session, unit, decision, channel="RECYCLE", sale_price=1000.0)

        service = CalibrationService()
        report = await service.report(db_session)

        assert report.sample_size == 2
        frequencies = [bin_.observed_frequency for bin_ in report.bins]
        assert sum(frequencies) / len(frequencies) == pytest.approx(0.5)

    @pytest.mark.asyncio
    async def test_a_decision_without_an_outcome_is_left_out(
        self, db_session: AsyncSession
    ) -> None:
        """Test that a decision with nothing to compare against is skipped."""
        unit = await _make_unit(db_session, suffix="1")
        await _make_decision(db_session, unit, confidence=0.9)

        service = CalibrationService()
        report = await service.report(db_session)

        assert report.sample_size == 0
        assert report.bins == []
        assert report.ece == 0.0


class TestRecalibration:
    """Tests for the versioned recalibration."""

    @pytest.mark.asyncio
    async def test_the_version_is_stored_and_activated(self, db_session: AsyncSession) -> None:
        """Test that a fitted version is stored and put in force."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit, confidence=0.9)
        await _make_outcome(db_session, unit, decision)

        service = CalibrationService()
        record = await service.recalibrate(db_session, version="calibration-v1")

        assert record.version == "calibration-v1"
        assert record.is_active is True
        assert record.sample_size == 1

        stored = (await db_session.execute(select(CalibrationVersion))).scalars().all()
        assert len(stored) == 1
        assert stored[0].version == "calibration-v1"

    @pytest.mark.asyncio
    async def test_only_one_version_is_in_force(self, db_session: AsyncSession) -> None:
        """Test that a new version deactivates the old one."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit, confidence=0.9)
        await _make_outcome(db_session, unit, decision)

        service = CalibrationService()
        await service.recalibrate(db_session, version="calibration-v1")
        await service.recalibrate(db_session, version="calibration-v2")

        stored = (await db_session.execute(select(CalibrationVersion))).scalars().all()
        assert len(stored) == 2
        active = [record for record in stored if record.is_active]
        assert len(active) == 1
        assert active[0].version == "calibration-v2"

    @pytest.mark.asyncio
    async def test_the_report_names_the_active_version(self, db_session: AsyncSession) -> None:
        """Test that the report says which version is in force."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit, confidence=0.9)
        await _make_outcome(db_session, unit, decision)

        service = CalibrationService()
        await service.recalibrate(db_session, version="calibration-v1")
        report = await service.report(db_session)

        assert report.active_version == "calibration-v1"


class TestCalibrationEndpoints:
    """Tests for the calibration API."""

    @pytest.mark.asyncio
    async def test_the_report_endpoint(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test that the report endpoint returns the curve and the ECE."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit, confidence=0.9)
        await _make_outcome(db_session, unit, decision)

        response = await client.get("/api/v1/analytics/calibration")

        assert response.status_code == 200
        data = response.json()
        assert data["sample_size"] == 1
        assert data["ece"] == pytest.approx(0.1)
        assert len(data["bins"]) == 1
        assert data["bins"][0]["observed_frequency"] == pytest.approx(1.0)
        assert data["active_version"] is None

    @pytest.mark.asyncio
    async def test_the_recalibrate_endpoint(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that the recalibrate endpoint stores a version."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit, confidence=0.9)
        await _make_outcome(db_session, unit, decision)

        response = await client.post(
            "/api/v1/analytics/calibration/recalibrate?version=calibration-v1"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "calibration-v1"
        assert data["is_active"] is True
        assert data["sample_size"] == 1

    @pytest.mark.asyncio
    async def test_the_report_endpoint_after_a_recalibration(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that the report names the version in force."""
        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit, confidence=0.9)
        await _make_outcome(db_session, unit, decision)

        await client.post("/api/v1/analytics/calibration/recalibrate?version=calibration-v1")
        response = await client.get("/api/v1/analytics/calibration")

        assert response.json()["active_version"] == "calibration-v1"

    @pytest.mark.asyncio
    async def test_the_report_endpoint_with_nothing_to_measure(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that an empty database gives an empty report."""
        response = await client.get("/api/v1/analytics/calibration")

        assert response.status_code == 200
        data = response.json()
        assert data["sample_size"] == 0
        assert data["bins"] == []
        assert data["ece"] == 0.0

    @pytest.mark.asyncio
    async def test_a_bad_bin_count_is_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that fewer than two bins is rejected."""
        response = await client.get("/api/v1/analytics/calibration?bins=1")

        assert response.status_code == 422
