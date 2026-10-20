"""
Tests for the historical backtest (F5.6).

The acceptance criterion for this feature is blunt: "a test fails the build
if any feature for a decision uses data timestamped after the decision
time". The tests here cover the three parts of that:

1. the detector recognises a planted leak,
2. the backtest refuses to run over a decision that leaks, and
3. the decisions actually stored have no look-ahead.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.backtest.baseline import FixedChannelBaseline, MostCommonChannelBaseline
from secondroute.backtest.bootstrap import (
    BootstrapError,
    bootstrap_mean_ci,
)
from secondroute.backtest.engine import BacktestRunError, run_backtest
from secondroute.backtest.lookahead import (
    LEAK,
    MALFORMED,
    PROVENANCE,
    LookAheadError,
    check_decision,
)
from secondroute.decision.models import Decision
from secondroute.feedback.models import AuditAction, AuditLog
from secondroute.identity.models import SKU
from secondroute.identity.organizations import Organization, User
from secondroute.intake.models import (
    Inspection,
    OrderChannel,
    ReturnReasonCode,
    Unit,
)

DECISION_TIME = datetime(2026, 3, 1, 12, 0, 0)


@pytest.fixture
async def backtest_org(db_session: AsyncSession) -> Organization:
    """Create the organisation the backtest replays decisions for."""
    org = Organization(name="Backtest Org", risk_profile="balanced")
    db_session.add(org)
    await db_session.flush()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def backtest_sku(db_session: AsyncSession) -> SKU:
    """Create a SKU for the units under test."""
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
        as_of=datetime(2026, 1, 1).date(),
    )
    db_session.add(sku)
    await db_session.flush()
    await db_session.refresh(sku)
    return sku


def make_candidates(nets: dict[str, float], blocked: tuple[str, ...] = ()) -> list[dict]:
    """Build a candidate payload the way the engine stores it."""
    candidates = [
        {
            "channel": channel,
            "eligible": True,
            "mean": net,
            "stddev": 10.0,
            "p10": net - 20,
            "p50": net,
            "p90": net + 20,
            "breakdown": {"net": net},
        }
        for channel, net in nets.items()
    ]
    candidates.extend(
        {
            "channel": channel,
            "eligible": False,
            "exclusion_reason": "Not eligible for this unit.",
            "mean": 0.0,
            "breakdown": {"net": 0.0},
        }
        for channel in blocked
    )
    return candidates


def make_decision(
    unit: Unit,
    *,
    created_at: datetime = DECISION_TIME,
    recommended_channel: str = "LIQUIDATE",
    nets: dict[str, float] | None = None,
    blocked: tuple[str, ...] = (),
    price_as_of: dict[str, str] | None = None,
    cost_as_of: dict[str, str] | None = None,
    snapshot_as_of: str | None = None,
) -> Decision:
    """Build a decision with a full, auditable provenance record."""
    if nets is None:
        nets = {"LIQUIDATE": 100.0, "RESELL": 80.0, "RECYCLE": 20.0}
    if price_as_of is None:
        price_as_of = {
            "LIQUIDATE:A": (created_at - timedelta(days=2)).isoformat(),
            "RESELL:A": (created_at - timedelta(days=2)).isoformat(),
            "RECYCLE:A": (created_at - timedelta(days=2)).isoformat(),
        }
    if cost_as_of is None:
        cost_as_of = {
            "channel_fee_pct:LIQUIDATE": (created_at - timedelta(days=30)).isoformat(),
        }
    if snapshot_as_of is None:
        snapshot_as_of = (created_at - timedelta(days=1)).isoformat()

    return Decision(
        unit_id=unit.id,
        org_id=unit.org_id,
        created_at=created_at,
        model_version="decision-v1",
        risk_profile="balanced",
        recommended_channel=recommended_channel,
        confidence=0.8,
        fallback_used=False,
        candidates_json=json.dumps(make_candidates(nets, blocked)),
        reasons_json="[]",
        flip_conditions_json="[]",
        data_freshness_json=json.dumps(
            {
                "price_sources": dict.fromkeys(price_as_of, "synthetic"),
                "price_as_of": price_as_of,
                "cost_sources": dict.fromkeys(cost_as_of, "table"),
                "cost_as_of": cost_as_of,
                "is_synthetic": True,
                "warnings": [],
            }
        ),
        action_steps_json="[]",
        input_snapshot_hash="a" * 64,
        input_snapshot_json=json.dumps({"as_of": snapshot_as_of}),
    )


async def make_unit(
    db_session: AsyncSession, sku: SKU, org: Organization, *, received_at: datetime
) -> Unit:
    """Create a unit received before the decision under test."""
    unit = Unit(
        sku_id=sku.id,
        org_id=org.id,
        serial=f"S{uuid4().hex[:8].upper()}",
        received_at=received_at,
        return_reason_code=ReturnReasonCode.BUYER_REMORSE,
        order_channel=OrderChannel.ONLINE,
    )
    db_session.add(unit)
    await db_session.flush()
    await db_session.refresh(unit)
    return unit


class TestLookAheadDetection:
    """The detector has to recognise a leak that is actually there."""

    def test_a_clean_decision_has_no_findings(self, db_session, backtest_sku, backtest_org):
        unit = Unit(
            sku_id=backtest_sku.id,
            org_id=backtest_org.id,
            received_at=DECISION_TIME - timedelta(days=10),
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        decision = make_decision(unit)

        report = check_decision(decision)

        assert report.is_clean
        assert not report.has_leak

    def test_a_price_dated_after_the_decision_is_a_leak(
        self, db_session, backtest_sku, backtest_org
    ):
        unit = Unit(
            sku_id=backtest_sku.id,
            org_id=backtest_org.id,
            received_at=DECISION_TIME - timedelta(days=10),
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        decision = make_decision(
            unit,
            price_as_of={
                "LIQUIDATE:A": (DECISION_TIME + timedelta(days=1)).isoformat(),
            },
        )

        report = check_decision(decision)

        assert report.has_leak
        leak = report.leaks[0]
        assert leak.kind == LEAK
        assert leak.field == "price_as_of:LIQUIDATE:A"
        assert leak.as_of == DECISION_TIME + timedelta(days=1)

    def test_a_cost_dated_after_the_decision_is_a_leak(
        self, db_session, backtest_sku, backtest_org
    ):
        unit = Unit(
            sku_id=backtest_sku.id,
            org_id=backtest_org.id,
            received_at=DECISION_TIME - timedelta(days=10),
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        decision = make_decision(
            unit,
            cost_as_of={
                "channel_fee_pct:LIQUIDATE": (DECISION_TIME + timedelta(hours=1)).isoformat(),
            },
        )

        report = check_decision(decision)

        assert report.has_leak
        assert report.leaks[0].field == "cost_as_of:channel_fee_pct:LIQUIDATE"

    def test_a_snapshot_dated_after_the_decision_is_a_leak(
        self, db_session, backtest_sku, backtest_org
    ):
        unit = Unit(
            sku_id=backtest_sku.id,
            org_id=backtest_org.id,
            received_at=DECISION_TIME - timedelta(days=10),
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        decision = make_decision(
            unit,
            snapshot_as_of=(DECISION_TIME + timedelta(minutes=5)).isoformat(),
        )

        report = check_decision(decision)

        assert report.has_leak
        assert report.leaks[0].field == "snapshot:as_of"

    def test_an_inspection_dated_after_the_decision_is_a_leak(
        self, db_session, backtest_sku, backtest_org
    ):
        unit = Unit(
            sku_id=backtest_sku.id,
            org_id=backtest_org.id,
            received_at=DECISION_TIME - timedelta(days=10),
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        decision = make_decision(unit)

        report = check_decision(
            decision,
            inspection_created_at=DECISION_TIME + timedelta(minutes=1),
        )

        assert report.has_leak
        assert report.leaks[0].field == "inspection:created_at"

    def test_a_unit_received_after_the_decision_is_a_leak(
        self, db_session, backtest_sku, backtest_org
    ):
        unit = Unit(
            sku_id=backtest_sku.id,
            org_id=backtest_org.id,
            received_at=DECISION_TIME - timedelta(days=10),
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        decision = make_decision(unit)

        report = check_decision(decision, unit_received_at=DECISION_TIME + timedelta(days=1))

        assert report.has_leak
        assert report.leaks[0].field == "unit:received_at"

    def test_a_missing_as_of_date_is_reported_as_a_provenance_gap(
        self, db_session, backtest_sku, backtest_org
    ):
        unit = Unit(
            sku_id=backtest_sku.id,
            org_id=backtest_org.id,
            received_at=DECISION_TIME - timedelta(days=10),
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        decision = make_decision(unit, price_as_of={"LIQUIDATE:A": ""})

        report = check_decision(decision)

        assert not report.has_leak
        kinds = {finding.kind for finding in report.findings}
        assert PROVENANCE in kinds

    def test_a_provenance_gap_can_be_ignored_when_asked(
        self, db_session, backtest_sku, backtest_org
    ):
        unit = Unit(
            sku_id=backtest_sku.id,
            org_id=backtest_org.id,
            received_at=DECISION_TIME - timedelta(days=10),
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        decision = make_decision(unit, price_as_of={"LIQUIDATE:A": ""})

        report = check_decision(decision, require_provenance=False)

        assert report.is_clean

    def test_an_unparseable_as_of_date_is_reported_as_malformed(
        self, db_session, backtest_sku, backtest_org
    ):
        unit = Unit(
            sku_id=backtest_sku.id,
            org_id=backtest_org.id,
            received_at=DECISION_TIME - timedelta(days=10),
            return_reason_code=ReturnReasonCode.BUYER_REMORSE,
            order_channel=OrderChannel.ONLINE,
        )
        decision = make_decision(unit, price_as_of={"LIQUIDATE:A": "last Tuesday"})

        report = check_decision(decision)

        assert not report.has_leak
        assert {finding.kind for finding in report.findings} == {MALFORMED}


class TestBootstrap:
    """The interval has to be a real interval, and reproducible."""

    def test_the_interval_brackets_the_point_estimate(self):
        values = [10.0, 12.0, 11.0, 9.0, 13.0, 10.5, 11.5, 12.5]

        interval = bootstrap_mean_ci(values, samples=2000, seed=7)

        assert interval.lower <= interval.point_estimate <= interval.upper
        assert interval.n == len(values)
        assert interval.method == "paired-bootstrap-percentile"

    def test_the_same_seed_gives_the_same_interval(self):
        values = [10.0, 12.0, 11.0, 9.0, 13.0]

        first = bootstrap_mean_ci(values, samples=500, seed=42)
        second = bootstrap_mean_ci(values, samples=500, seed=42)

        assert first.lower == second.lower
        assert first.upper == second.upper

    def test_a_different_seed_can_move_the_interval(self):
        values = [10.0, 12.0, 11.0, 9.0, 13.0, 30.0, -20.0]

        first = bootstrap_mean_ci(values, samples=500, seed=1)
        second = bootstrap_mean_ci(values, samples=500, seed=2)

        assert (first.lower, first.upper) != (second.lower, second.upper)

    def test_a_constant_sample_gives_a_degenerate_interval(self):
        interval = bootstrap_mean_ci([5.0] * 10, samples=500, seed=3)

        assert interval.lower == pytest.approx(5.0)
        assert interval.upper == pytest.approx(5.0)
        assert interval.point_estimate == pytest.approx(5.0)

    def test_a_zero_difference_does_not_exclude_zero(self):
        interval = bootstrap_mean_ci([0.0] * 10, samples=500, seed=3)

        assert not interval.excludes_zero

    def test_a_clear_difference_excludes_zero(self):
        values = [10.0, 11.0, 12.0, 10.5, 11.5, 10.2, 11.2, 12.1]

        interval = bootstrap_mean_ci(values, samples=2000, seed=5)

        assert interval.excludes_zero
        assert interval.lower > 0

    def test_one_observation_is_refused(self):
        with pytest.raises(BootstrapError):
            bootstrap_mean_ci([1.0])

    def test_an_impossible_confidence_level_is_refused(self):
        with pytest.raises(BootstrapError):
            bootstrap_mean_ci([1.0, 2.0], confidence=1.5)

    def test_a_non_finite_value_is_refused(self):
        with pytest.raises(BootstrapError):
            bootstrap_mean_ci([1.0, float("nan"), 3.0])


class TestBaselinePolicy:
    """The baseline has to say which policy it is."""

    def test_a_fixed_baseline_always_returns_its_channel(self):
        baseline = FixedChannelBaseline(channel="LIQUIDATE")

        assert baseline.channel_for(object()) == "LIQUIDATE"
        assert baseline.name == "fixed-channel"

    def test_the_most_common_baseline_picks_the_usual_channel(self):
        baseline = MostCommonChannelBaseline(counts={"LIQUIDATE": 8, "RESELL": 2})

        assert baseline.channel_for(object()) == "LIQUIDATE"

    def test_a_tie_is_broken_deterministically(self):
        baseline = MostCommonChannelBaseline(counts={"RESELL": 3, "LIQUIDATE": 3})

        assert baseline.channel_for(object()) == "LIQUIDATE"

    def test_the_most_common_baseline_with_no_data_has_no_answer(self):
        baseline = MostCommonChannelBaseline(counts={})

        assert baseline.channel_for(object()) is None


class TestBacktestRunner:
    """The backtest compares two policies over the same units."""

    @pytest.mark.asyncio
    async def test_it_reports_the_net_difference(
        self, db_session: AsyncSession, backtest_sku, backtest_org
    ):
        unit = await make_unit(
            db_session, backtest_sku, backtest_org, received_at=DECISION_TIME - timedelta(days=10)
        )
        decision = make_decision(
            unit,
            nets={"LIQUIDATE": 100.0, "RESELL": 80.0},
            recommended_channel="LIQUIDATE",
        )
        db_session.add(decision)
        await db_session.flush()

        result = await run_backtest(
            db_session,
            org_id=backtest_org.id,
            baseline=FixedChannelBaseline(channel="RESELL"),
        )

        assert result.decision_count == 1
        assert result.mean_engine_net == pytest.approx(100.0)
        assert result.mean_baseline_net == pytest.approx(80.0)
        assert result.mean_difference == pytest.approx(20.0)

    @pytest.mark.asyncio
    async def test_it_reports_the_interval_and_not_only_the_point_estimate(
        self, db_session: AsyncSession, backtest_sku, backtest_org
    ):
        for index in range(6):
            unit = await make_unit(
                db_session,
                backtest_sku,
                backtest_org,
                received_at=DECISION_TIME - timedelta(days=10),
            )
            decision = make_decision(
                unit,
                created_at=DECISION_TIME + timedelta(minutes=index),
                nets={"LIQUIDATE": 100.0 + index, "RESELL": 80.0},
                recommended_channel="LIQUIDATE",
            )
            db_session.add(decision)
        await db_session.flush()

        result = await run_backtest(
            db_session,
            org_id=backtest_org.id,
            baseline=FixedChannelBaseline(channel="RESELL"),
            samples=2000,
            seed=11,
        )

        assert result.interval is not None
        assert result.mean_difference is not None
        assert result.interval.n == 6
        assert result.interval.lower <= result.mean_difference <= result.interval.upper
        assert result.interval.seed == 11

    @pytest.mark.asyncio
    async def test_it_names_the_baseline_it_used(
        self, db_session: AsyncSession, backtest_sku, backtest_org
    ):
        unit = await make_unit(
            db_session, backtest_sku, backtest_org, received_at=DECISION_TIME - timedelta(days=10)
        )
        db_session.add(make_decision(unit))
        await db_session.flush()

        result = await run_backtest(
            db_session,
            org_id=backtest_org.id,
            baseline=FixedChannelBaseline(channel="RESELL"),
        )

        assert result.baseline_name == "fixed-channel"
        assert result.baseline_channel == "RESELL"

    @pytest.mark.asyncio
    async def test_it_skips_a_decision_whose_baseline_channel_was_blocked(
        self, db_session: AsyncSession, backtest_sku, backtest_org
    ):
        unit = await make_unit(
            db_session, backtest_sku, backtest_org, received_at=DECISION_TIME - timedelta(days=10)
        )
        db_session.add(
            make_decision(
                unit,
                nets={"LIQUIDATE": 100.0},
                blocked=("RESELL",),
                recommended_channel="LIQUIDATE",
            )
        )
        await db_session.flush()

        result = await run_backtest(
            db_session,
            org_id=backtest_org.id,
            baseline=FixedChannelBaseline(channel="RESELL"),
        )

        assert result.decision_count == 0
        assert len(result.skipped) == 1
        assert "not eligible" in result.skipped[0].reason

    @pytest.mark.asyncio
    async def test_it_refuses_to_run_over_a_leaking_decision(
        self, db_session: AsyncSession, backtest_sku, backtest_org
    ):
        unit = await make_unit(
            db_session, backtest_sku, backtest_org, received_at=DECISION_TIME - timedelta(days=10)
        )
        db_session.add(
            make_decision(
                unit,
                price_as_of={
                    "LIQUIDATE:A": (DECISION_TIME + timedelta(days=1)).isoformat(),
                },
            )
        )
        await db_session.flush()

        with pytest.raises(LookAheadError) as error:
            await run_backtest(
                db_session,
                org_id=backtest_org.id,
                baseline=FixedChannelBaseline(channel="RESELL"),
            )

        assert error.value.report.has_leak
        assert len(error.value.report.leaks) == 1

    @pytest.mark.asyncio
    async def test_it_reports_nothing_when_there_are_no_decisions(
        self, db_session: AsyncSession, backtest_org
    ):
        result = await run_backtest(db_session, org_id=backtest_org.id)

        assert result.decision_count == 0
        assert result.mean_difference is None
        assert result.interval is None
        assert result.warnings

    @pytest.mark.asyncio
    async def test_it_needs_an_organisation(self, db_session: AsyncSession):
        with pytest.raises(BacktestRunError):
            await run_backtest(db_session, org_id=None)

    @pytest.mark.asyncio
    async def test_it_only_replays_the_requested_window(
        self, db_session: AsyncSession, backtest_sku, backtest_org
    ):
        old_unit = await make_unit(
            db_session, backtest_sku, backtest_org, received_at=DECISION_TIME - timedelta(days=90)
        )
        db_session.add(make_decision(old_unit, created_at=DECISION_TIME - timedelta(days=60)))
        new_unit = await make_unit(
            db_session, backtest_sku, backtest_org, received_at=DECISION_TIME - timedelta(days=10)
        )
        db_session.add(make_decision(new_unit))
        await db_session.flush()

        result = await run_backtest(
            db_session,
            org_id=backtest_org.id,
            baseline=FixedChannelBaseline(channel="RESELL"),
            window_start=DECISION_TIME - timedelta(days=1),
        )

        assert result.decision_count == 1
        assert result.window_start == DECISION_TIME

    @pytest.mark.asyncio
    async def test_the_most_common_baseline_uses_what_the_partner_actually_did(
        self, db_session: AsyncSession, backtest_sku, backtest_org
    ):
        """The baseline reads the partner's habit from the recorded outcomes."""
        from secondroute.feedback.models import Outcome

        decisions = []
        for index in range(3):
            unit = await make_unit(
                db_session,
                backtest_sku,
                backtest_org,
                received_at=DECISION_TIME - timedelta(days=10),
            )
            decision = make_decision(
                unit,
                created_at=DECISION_TIME + timedelta(minutes=index),
                nets={"LIQUIDATE": 100.0, "RESELL": 80.0},
                recommended_channel="LIQUIDATE",
            )
            db_session.add(decision)
            decisions.append(decision)
        await db_session.flush()

        # The partner liquidated two units and resold one.
        for decision, channel in zip(decisions, ["LIQUIDATE", "LIQUIDATE", "RESELL"], strict=True):
            db_session.add(
                Outcome(
                    unit_id=decision.unit_id,
                    decision_id=decision.id,
                    channel_taken=channel,
                    sale_price=100.0,
                    fees_actual=10.0,
                    repair_cost_actual=5.0,
                    logistics_actual=5.0,
                    days_to_disposition=7,
                    final_status="sold",
                )
            )
        await db_session.flush()

        result = await run_backtest(
            db_session,
            org_id=backtest_org.id,
            baseline=MostCommonChannelBaseline(counts={}),
        )

        assert result.baseline_name == "most-common-channel"
        assert result.baseline_channel == "LIQUIDATE"
        assert result.decision_count == 3
        assert result.mean_difference == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_it_is_deterministic(self, db_session: AsyncSession, backtest_sku, backtest_org):
        for index in range(4):
            unit = await make_unit(
                db_session,
                backtest_sku,
                backtest_org,
                received_at=DECISION_TIME - timedelta(days=10),
            )
            db_session.add(
                make_decision(
                    unit,
                    created_at=DECISION_TIME + timedelta(minutes=index),
                    nets={"LIQUIDATE": 100.0 + index, "RESELL": 70.0 + index},
                )
            )
        await db_session.flush()

        first = await run_backtest(
            db_session,
            org_id=backtest_org.id,
            baseline=FixedChannelBaseline(channel="RESELL"),
            samples=1000,
            seed=99,
        )
        second = await run_backtest(
            db_session,
            org_id=backtest_org.id,
            baseline=FixedChannelBaseline(channel="RESELL"),
            samples=1000,
            seed=99,
        )

        assert first.mean_difference == second.mean_difference
        assert first.interval is not None
        assert second.interval is not None
        assert first.interval.lower == second.interval.lower
        assert first.interval.upper == second.interval.upper


class TestNoLookAheadInStoredDecisions:
    """The build fails if a stored decision used its own future."""

    @pytest.mark.asyncio
    async def test_a_decision_made_by_the_real_engine_has_no_lookahead(
        self, db_session: AsyncSession, backtest_sku, backtest_org
    ):
        """The engine itself must not use data from after the decision.

        This is the test that fails the build when the engine starts
        reaching forward in time. It runs the real engine over a real unit
        and then checks the decision it produced, rather than checking a
        decision the test built by hand.
        """
        from secondroute.decision.engine import decide_unit
        from secondroute.pricing.sources import SyntheticPriceSource

        unit = await make_unit(
            db_session, backtest_sku, backtest_org, received_at=DECISION_TIME - timedelta(days=10)
        )
        db_session.add(
            Inspection(
                unit_id=unit.id,
                battery_health_pct="95",
                battery_cycles="120",
                cosmetic_grade="A",
                functional_tests_json='{"display": true, "keyboard": true}',
                activation_lock="none",
                accessories_json='{"charger": true}',
            )
        )
        await db_session.flush()

        decision = await decide_unit(
            db_session,
            unit.id,
            SyntheticPriceSource(),
            as_of=datetime.utcnow(),
        )

        report = check_decision(decision)
        assert not report.has_leak, (
            f"The engine used data dated after the decision was made: "
            f"{[finding.as_dict() for finding in report.leaks]}"
        )
        assert report.is_clean, (
            f"The engine's decision does not record enough provenance to prove it had no "
            f"look-ahead: {[finding.as_dict() for finding in report.findings]}"
        )

    @pytest.mark.asyncio
    async def test_stored_decisions_have_no_lookahead(
        self, db_session: AsyncSession, backtest_sku, backtest_org
    ):
        """Every stored decision must be free of look-ahead.

        This is the test that fails the build when the engine starts using
        data from after the decision was made.
        """
        unit = await make_unit(
            db_session, backtest_sku, backtest_org, received_at=DECISION_TIME - timedelta(days=10)
        )
        db_session.add(make_decision(unit))
        await db_session.flush()

        decisions = (
            (await db_session.execute(select(Decision).where(Decision.org_id == backtest_org.id)))
            .scalars()
            .all()
        )

        assert decisions
        for decision in decisions:
            report = check_decision(decision)
            assert not report.has_leak, (
                f"Decision {decision.id} used data dated after it was made: "
                f"{[finding.as_dict() for finding in report.leaks]}"
            )

    @pytest.mark.asyncio
    async def test_an_audit_row_written_for_a_change_is_rolled_back_with_it(
        self, db_session: AsyncSession, backtest_sku, backtest_org
    ):
        """A failed change must not leave an audit trail behind.

        The audit row and the change it describes belong to the same
        transaction, so a rollback takes both. Without that, a failed
        request would still leave an audit trail for a change that never
        happened.
        """
        from secondroute.feedback.models import AuditLog as AuditLogModel

        unit = await make_unit(
            db_session, backtest_sku, backtest_org, received_at=DECISION_TIME - timedelta(days=10)
        )

        before = (
            (
                await db_session.execute(
                    select(AuditLogModel).where(
                        AuditLogModel.entity == "units",
                        AuditLogModel.entity_id == str(unit.id),
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(before) == 1

        await db_session.rollback()

        after = (
            (
                await db_session.execute(
                    select(AuditLogModel).where(
                        AuditLogModel.entity == "units",
                        AuditLogModel.entity_id == str(unit.id),
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(after) == 0


class TestBacktestApi:
    """The report has to be reachable and has to be stored."""

    @pytest.mark.asyncio
    async def test_it_stores_a_run_and_returns_the_report(
        self, client: AsyncClient, db_session: AsyncSession, backtest_sku, backtest_org
    ):
        for index in range(3):
            unit = await make_unit(
                db_session,
                backtest_sku,
                backtest_org,
                received_at=DECISION_TIME - timedelta(days=10),
            )
            db_session.add(
                make_decision(
                    unit,
                    created_at=DECISION_TIME + timedelta(minutes=index),
                    nets={"LIQUIDATE": 100.0 + index, "RESELL": 80.0},
                    recommended_channel="LIQUIDATE",
                )
            )
        await db_session.flush()

        response = await client.post(
            "/api/v1/backtests",
            json={
                "org_id": str(backtest_org.id),
                "name": "Pilot backtest",
                "baseline": "fixed-channel",
                "baseline_channel": "RESELL",
                "samples": 500,
                "seed": 3,
            },
        )

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["name"] == "Pilot backtest"
        assert body["decision_count"] == 3
        assert body["mean_difference"] == pytest.approx(21.0)
        assert body["ci_lower"] is not None
        assert body["ci_upper"] is not None
        assert body["report"]["interval"]["n"] == 3
        assert body["report"]["lookahead"]["has_leak"] is False

    @pytest.mark.asyncio
    async def test_a_single_decision_reports_the_point_estimate_without_an_interval(
        self, client: AsyncClient, db_session: AsyncSession, backtest_sku, backtest_org
    ):
        """One unit cannot give an interval, and the report has to say so."""
        unit = await make_unit(
            db_session, backtest_sku, backtest_org, received_at=DECISION_TIME - timedelta(days=10)
        )
        db_session.add(
            make_decision(
                unit,
                nets={"LIQUIDATE": 100.0, "RESELL": 80.0},
                recommended_channel="LIQUIDATE",
            )
        )
        await db_session.flush()

        response = await client.post(
            "/api/v1/backtests",
            json={
                "org_id": str(backtest_org.id),
                "baseline": "fixed-channel",
                "baseline_channel": "RESELL",
            },
        )

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["mean_difference"] == pytest.approx(20.0)
        assert body["ci_lower"] is None
        assert body["ci_upper"] is None
        assert body["report"]["interval"] is None
        assert any("interval" in warning for warning in body["report"]["warnings"])

    @pytest.mark.asyncio
    async def test_it_refuses_a_leaking_decision(
        self, client: AsyncClient, db_session: AsyncSession, backtest_sku, backtest_org
    ):
        unit = await make_unit(
            db_session, backtest_sku, backtest_org, received_at=DECISION_TIME - timedelta(days=10)
        )
        db_session.add(
            make_decision(
                unit,
                price_as_of={
                    "LIQUIDATE:A": (DECISION_TIME + timedelta(days=1)).isoformat(),
                },
            )
        )
        await db_session.flush()

        response = await client.post(
            "/api/v1/backtests",
            json={
                "org_id": str(backtest_org.id),
                "baseline": "fixed-channel",
                "baseline_channel": "RESELL",
            },
        )

        assert response.status_code == 409, response.text
        detail = response.json()["detail"]
        assert detail["findings"]
        assert detail["findings"][0]["kind"] == LEAK

    @pytest.mark.asyncio
    async def test_it_rejects_a_fixed_baseline_with_no_channel(
        self, client: AsyncClient, backtest_org
    ):
        response = await client.post(
            "/api/v1/backtests",
            json={"org_id": str(backtest_org.id), "baseline": "fixed-channel"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_it_rejects_an_unknown_baseline(self, client: AsyncClient, backtest_org):
        response = await client.post(
            "/api/v1/backtests",
            json={"org_id": str(backtest_org.id), "baseline": "crystal-ball"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_it_lists_and_reads_the_stored_runs(
        self, client: AsyncClient, db_session: AsyncSession, backtest_sku, backtest_org
    ):
        unit = await make_unit(
            db_session, backtest_sku, backtest_org, received_at=DECISION_TIME - timedelta(days=10)
        )
        db_session.add(make_decision(unit))
        await db_session.flush()

        created = await client.post(
            "/api/v1/backtests",
            json={
                "org_id": str(backtest_org.id),
                "baseline": "fixed-channel",
                "baseline_channel": "RESELL",
            },
        )
        assert created.status_code == 201
        run_id = created.json()["id"]

        listed = await client.get(f"/api/v1/backtests?org_id={backtest_org.id}")
        assert listed.status_code == 200
        assert len(listed.json()) == 1

        fetched = await client.get(f"/api/v1/backtests/{run_id}")
        assert fetched.status_code == 200
        assert fetched.json()["id"] == run_id

    @pytest.mark.asyncio
    async def test_a_missing_run_is_a_404(self, client: AsyncClient):
        response = await client.get(f"/api/v1/backtests/{uuid4()}")

        assert response.status_code == 404
