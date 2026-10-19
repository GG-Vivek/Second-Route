"""
Tests for the risk profiles and the certainty equivalent (F2.6).
"""

from __future__ import annotations

import numpy as np
import pytest

from secondroute.core.config import settings
from secondroute.decision.evaluator import ChannelEvaluation, CostBreakdown
from secondroute.decision.utility import (
    RISK_PROFILES,
    certainty_equivalent,
    lambda_for,
    rank_channels,
)


def make_channel(
    channel: str,
    mean: float,
    stddev: float,
    *,
    eligible: bool = True,
) -> ChannelEvaluation:
    """Build a channel evaluation for a test."""
    return ChannelEvaluation(
        channel=channel,
        eligible=eligible,
        exclusion_reason=None if eligible else "blocked for this test",
        net_samples=np.array([mean], dtype=np.float64),
        mean=mean,
        stddev=stddev,
        p10=mean - stddev,
        p50=mean,
        p90=mean + stddev,
        breakdown=CostBreakdown(
            sale_price=mean + 100.0,
            fees=50.0,
            logistics=20.0,
            handling=10.0,
            repair=10.0,
            holding=10.0,
        ),
        grade_probabilities={"A": 1.0},
    )


class TestRiskProfiles:
    """Three profiles exist with sensible parameters."""

    def test_three_profiles(self) -> None:
        """Conservative, balanced and aggressive exist."""
        assert set(RISK_PROFILES) == {"conservative", "balanced", "aggressive"}

    def test_lambda_ordering(self) -> None:
        """The conservative profile is the most risk averse."""
        assert lambda_for("conservative") > lambda_for("balanced")
        assert lambda_for("balanced") > lambda_for("aggressive")

    def test_unknown_profile_falls_back_to_balanced(self) -> None:
        """An unknown profile uses the balanced lambda."""
        assert lambda_for("does_not_exist") == lambda_for("balanced")

    def test_empty_profile_is_rejected(self) -> None:
        """An empty profile name is an error."""
        with pytest.raises(ValueError):
            lambda_for("")

    def test_lambda_comes_from_configuration(self) -> None:
        """The lambdas are configuration driven."""
        assert lambda_for("conservative") == settings.RISK_PROFILE_LAMBDA["conservative"]
        assert lambda_for("balanced") == settings.RISK_PROFILE_LAMBDA["balanced"]
        assert lambda_for("aggressive") == settings.RISK_PROFILE_LAMBDA["aggressive"]


class TestCertaintyEquivalent:
    """The certainty equivalent is ``mean - lambda * stddev``."""

    def test_formula(self) -> None:
        """The formula is applied exactly."""
        assert certainty_equivalent(100.0, 20.0, "balanced") == pytest.approx(100.0 - 20.0)
        assert certainty_equivalent(100.0, 20.0, "conservative") == pytest.approx(
            100.0 - 2.0 * 20.0
        )

    def test_zero_volatility_equals_the_mean(self) -> None:
        """A deterministic outcome has certainty equivalent equal to its mean."""
        assert certainty_equivalent(250.0, 0.0, "conservative") == pytest.approx(250.0)


class TestRanking:
    """Ranking is what separates the profiles."""

    #: Two channels with close means but very different dispersion.
    #: ``HIGH_MEAN_HIGH_VAR`` pays more on average but is much less predictable.
    HIGH_MEAN_HIGH_VAR = 1100.0
    HIGH_MEAN_HIGH_VAR_STD = 150.0
    LOW_MEAN_LOW_VAR = 1000.0
    LOW_MEAN_LOW_VAR_STD = 10.0

    def _fixture(self) -> tuple[ChannelEvaluation, ChannelEvaluation]:
        """Return the two-channel fixture."""
        return (
            make_channel(
                "HIGH_MEAN_HIGH_VAR",
                self.HIGH_MEAN_HIGH_VAR,
                self.HIGH_MEAN_HIGH_VAR_STD,
            ),
            make_channel(
                "LOW_MEAN_LOW_VAR",
                self.LOW_MEAN_LOW_VAR,
                self.LOW_MEAN_LOW_VAR_STD,
            ),
        )

    def test_conservative_picks_the_lower_variance_channel(self) -> None:
        """The conservative profile prefers predictability."""
        ranked = rank_channels(self._fixture(), "conservative")
        assert ranked[0][0] == "LOW_MEAN_LOW_VAR"

    def test_aggressive_picks_the_higher_mean_channel(self) -> None:
        """The aggressive profile prefers the expected value."""
        ranked = rank_channels(self._fixture(), "aggressive")
        assert ranked[0][0] == "HIGH_MEAN_HIGH_VAR"

    def test_the_two_profiles_disagree(self) -> None:
        """The fixture separates the conservative and aggressive profiles."""
        conservative = rank_channels(self._fixture(), "conservative")[0][0]
        aggressive = rank_channels(self._fixture(), "aggressive")[0][0]
        assert conservative != aggressive

    def test_balanced_ranks_both_channels(self) -> None:
        """The balanced profile still produces a full ranking."""
        ranked = rank_channels(self._fixture(), "balanced")
        assert [name for name, _ in ranked] == [
            "HIGH_MEAN_HIGH_VAR",
            "LOW_MEAN_LOW_VAR",
        ] or [name for name, _ in ranked] == [
            "LOW_MEAN_LOW_VAR",
            "HIGH_MEAN_HIGH_VAR",
        ]

    def test_identical_channels_produce_a_stable_order(self) -> None:
        """Equal channels rank without error."""
        channels = (
            make_channel("A", 500.0, 100.0),
            make_channel("B", 500.0, 100.0),
        )
        ranked = rank_channels(channels, "balanced")
        assert len(ranked) == 2
        assert {name for name, _ in ranked} == {"A", "B"}

    def test_ineligible_channels_are_excluded(self) -> None:
        """An ineligible channel is never recommended."""
        channels = (
            make_channel("BLOCKED", 5000.0, 10.0, eligible=False),
            make_channel("ALLOWED", 100.0, 10.0),
        )
        ranked = rank_channels(channels, "aggressive")
        assert [name for name, _ in ranked] == ["ALLOWED"]

    def test_ranking_is_sorted_descending(self) -> None:
        """The ranking comes back best first."""
        channels = (
            make_channel("A", 100.0, 10.0),
            make_channel("B", 300.0, 10.0),
            make_channel("C", 200.0, 10.0),
        )
        ranked = rank_channels(channels, "balanced")
        assert [name for name, _ in ranked] == ["B", "C", "A"]
        values = [value for _, value in ranked]
        assert values == sorted(values, reverse=True)
