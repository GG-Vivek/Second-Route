"""
Tests for the decision distribution endpoint (F8.4).

The endpoint turns the engine's own Monte Carlo draws into a density
histogram on a shared axis, so that the overlap between two channels can
be seen rather than asserted. Two properties matter above all: the
histogram is built from the samples, and the same decision always returns
the same histogram.
"""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import numpy as np
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.decision.distribution import (
    DEFAULT_BIN_COUNT,
    build_distribution,
)
from secondroute.identity.models import SKU
from secondroute.intake.models import Inspection, OrderChannel, ReturnReasonCode, Unit


async def make_unit(db_session: AsyncSession) -> Unit:
    """Create a unit with one inspection, ready to be decided."""
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
        as_of=date(2024, 1, 15),
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

    inspection = Inspection(
        unit_id=unit.id,
        battery_health_pct="95",
        battery_cycles="120",
        cosmetic_grade="A",
        functional_tests_json='{"display": true, "keyboard": true}',
        activation_lock="none",
        accessories_json='{"charger": true}',
    )
    db_session.add(inspection)
    await db_session.flush()
    await db_session.refresh(unit)
    return unit


def _normal(seed: int, mean: float, stddev: float, size: int = 4000) -> np.ndarray:
    """Return a deterministic sample of the requested shape."""
    rng = np.random.default_rng(seed)
    return rng.normal(mean, stddev, size=size)


class TestBuildDistribution:
    """The histogram builder."""

    def test_the_axis_covers_every_draw(self) -> None:
        """The shared axis reaches past the smallest and largest draw."""
        draws = {
            "A": _normal(1, 100.0, 10.0),
            "B": _normal(2, 500.0, 50.0),
        }
        channels = [
            {"channel": "A", "eligible": True, "mean": 100.0, "stddev": 10.0},
            {"channel": "B", "eligible": True, "mean": 500.0, "stddev": 50.0},
        ]

        result = build_distribution(
            draws_by_channel=draws,
            channels=channels,
            probability_best={"A": 0.8, "B": 0.2},
        )

        assert result.axis_min < float(draws["A"].min())
        assert result.axis_max > float(draws["B"].max())

    def test_every_channel_shares_the_same_axis(self) -> None:
        """The bars of one channel line up with the bars of another."""
        draws = {"A": _normal(1, 100.0, 10.0), "B": _normal(2, 500.0, 50.0)}
        channels = [
            {"channel": "A", "eligible": True},
            {"channel": "B", "eligible": True},
        ]

        result = build_distribution(
            draws_by_channel=draws,
            channels=channels,
            probability_best={},
        )

        xs = [b.x for b in result.channels[0].bins]
        for channel in result.channels[1:]:
            assert [b.x for b in channel.bins] == xs

    def test_the_density_integrates_to_one(self) -> None:
        """The bars of a channel account for all of its probability."""
        draws = {"A": _normal(1, 100.0, 10.0)}
        channels = [{"channel": "A", "eligible": True}]

        result = build_distribution(
            draws_by_channel=draws,
            channels=channels,
            probability_best={},
            bin_count=200,
        )

        width = (result.axis_max - result.axis_min) / result.bin_count
        total = sum(b.density for b in result.channels[0].bins) * width
        assert total == pytest.approx(1.0, abs=1e-6)

    def test_the_shape_follows_the_draws(self) -> None:
        """The peak of the histogram is near the mean of the samples."""
        draws = {"A": _normal(1, 250.0, 20.0)}
        channels = [{"channel": "A", "eligible": True}]

        result = build_distribution(
            draws_by_channel=draws,
            channels=channels,
            probability_best={},
            bin_count=120,
        )

        bins = result.channels[0].bins
        peak = max(bins, key=lambda b: b.density)
        assert peak.x == pytest.approx(250.0, abs=40.0)

    def test_an_ineligible_channel_has_no_bars(self) -> None:
        """A channel that could not be used carries no density."""
        draws = {"A": _normal(1, 100.0, 10.0)}
        channels = [
            {"channel": "A", "eligible": True},
            {"channel": "B", "eligible": False, "exclusion_reason": "Not worth it"},
        ]

        result = build_distribution(
            draws_by_channel=draws,
            channels=channels,
            probability_best={},
        )

        ineligible = next(c for c in result.channels if c.channel == "B")
        assert ineligible.eligible is False
        assert ineligible.exclusion_reason == "Not worth it"
        assert ineligible.bins == ()

    def test_the_same_draws_always_give_the_same_histogram(self) -> None:
        """The builder is a pure function of its input."""
        draws = {"A": _normal(7, 100.0, 10.0)}
        channels = [{"channel": "A", "eligible": True}]

        first = build_distribution(draws_by_channel=draws, channels=channels, probability_best={})
        second = build_distribution(draws_by_channel=draws, channels=channels, probability_best={})

        assert [b.density for b in first.channels[0].bins] == [
            b.density for b in second.channels[0].bins
        ]

    def test_draws_with_no_spread_do_not_divide_by_zero(self) -> None:
        """A distribution with a single value still produces a usable axis."""
        draws = {"A": np.full(100, 42.0)}
        channels = [{"channel": "A", "eligible": True}]

        result = build_distribution(
            draws_by_channel=draws,
            channels=channels,
            probability_best={},
        )

        assert result.axis_max > result.axis_min
        assert all(b.density >= 0 for b in result.channels[0].bins)

    def test_the_bin_count_must_be_positive(self) -> None:
        """A histogram with no bars is not a histogram."""
        with pytest.raises(ValueError):
            build_distribution(
                draws_by_channel={},
                channels=[],
                probability_best={},
                bin_count=0,
            )


class TestDistributionEndpoint:
    """The endpoint that serves the histogram."""

    @pytest.mark.asyncio
    async def test_it_returns_the_distribution(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """A decision can be described as a distribution."""
        unit = await make_unit(db_session)
        created = await client.post(f"/api/v1/units/{unit.id}/decide")
        assert created.status_code == 201
        decision_id = created.json()["id"]

        response = await client.get(f"/api/v1/decisions/{decision_id}/distribution")
        assert response.status_code == 200

        data = response.json()
        assert data["decision_id"] == decision_id
        assert data["input_snapshot_hash"] == created.json()["input_snapshot_hash"]
        assert data["bin_count"] == DEFAULT_BIN_COUNT
        assert data["axis"]["max"] > data["axis"]["min"]
        assert len(data["channels"]) > 0

    @pytest.mark.asyncio
    async def test_every_eligible_channel_has_bars(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The channels that could be used are the ones that are drawn."""
        unit = await make_unit(db_session)
        created = await client.post(f"/api/v1/units/{unit.id}/decide")
        decision_id = created.json()["id"]

        response = await client.get(f"/api/v1/decisions/{decision_id}/distribution")
        data = response.json()

        eligible = [c for c in data["channels"] if c["eligible"]]
        assert eligible
        for channel in eligible:
            assert len(channel["bins"]) == data["bin_count"]
            assert all(bin_["density"] >= 0 for bin_ in channel["bins"])

    @pytest.mark.asyncio
    async def test_the_same_decision_always_returns_the_same_histogram(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The endpoint is deterministic."""
        unit = await make_unit(db_session)
        created = await client.post(f"/api/v1/units/{unit.id}/decide")
        decision_id = created.json()["id"]

        first = await client.get(f"/api/v1/decisions/{decision_id}/distribution")
        second = await client.get(f"/api/v1/decisions/{decision_id}/distribution")

        assert first.json()["channels"] == second.json()["channels"]
        assert first.json()["axis"] == second.json()["axis"]

    @pytest.mark.asyncio
    async def test_the_replay_still_agrees_with_the_stored_decision(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The response says whether the replay still agrees."""
        unit = await make_unit(db_session)
        created = await client.post(f"/api/v1/units/{unit.id}/decide")
        decision = created.json()

        response = await client.get(f"/api/v1/decisions/{decision['id']}/distribution")
        data = response.json()

        assert data["matches_stored_decision"] is True
        assert data["recommended_channel"] == decision["recommended_channel"]
        assert data["confidence"] == pytest.approx(decision["confidence"])

    @pytest.mark.asyncio
    async def test_the_bin_count_can_be_chosen(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The caller can ask for a coarser histogram."""
        unit = await make_unit(db_session)
        created = await client.post(f"/api/v1/units/{unit.id}/decide")
        decision_id = created.json()["id"]

        response = await client.get(
            f"/api/v1/decisions/{decision_id}/distribution", params={"bins": 24}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["bin_count"] == 24
        assert len(data["channels"][0]["bins"]) == 24

    @pytest.mark.asyncio
    async def test_an_unknown_decision_is_a_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """A decision that does not exist is not described."""
        response = await client.get(f"/api/v1/decisions/{uuid4()}/distribution")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_a_bin_count_out_of_range_is_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """The histogram cannot be empty or absurdly large."""
        unit = await make_unit(db_session)
        created = await client.post(f"/api/v1/units/{unit.id}/decide")
        decision_id = created.json()["id"]

        too_small = await client.get(
            f"/api/v1/decisions/{decision_id}/distribution", params={"bins": 1}
        )
        too_large = await client.get(
            f"/api/v1/decisions/{decision_id}/distribution", params={"bins": 100000}
        )

        assert too_small.status_code == 422
        assert too_large.status_code == 422
