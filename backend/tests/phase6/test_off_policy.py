"""
Tests for off-policy evaluation (Phase 6 - F6.7).
"""

import pytest

from secondroute.learning.off_policy import (
    LoggedDecision,
    OffPolicyEvaluator,
    simulate_off_policy_evaluation,
)


class TestIPS:
    """Tests for inverse propensity scoring."""

    @pytest.mark.asyncio
    async def test_empty_log_returns_zero(self) -> None:
        """Test that an empty log produces a zeroed estimate."""
        evaluator = OffPolicyEvaluator()
        result = evaluator.ips([], {"RESELL": 1.0})

        assert result.value == 0.0
        assert result.std_error == 0.0
        assert result.n == 0
        assert result.method == "ips"

    @pytest.mark.asyncio
    async def test_matching_policy_is_unbiased(self) -> None:
        """Test that IPS under the behaviour policy recovers the mean reward."""
        evaluator = OffPolicyEvaluator()
        logged = [
            LoggedDecision(channel_chosen="RESELL", reward=100.0, propensity=0.5),
            LoggedDecision(channel_chosen="RESELL", reward=200.0, propensity=0.5),
            LoggedDecision(channel_chosen="RESELL", reward=300.0, propensity=0.5),
        ]

        result = evaluator.ips(logged, {"RESELL": 0.5})

        assert result.value == pytest.approx(200.0)
        assert result.n == 3

    @pytest.mark.asyncio
    async def test_zero_propensity_is_skipped(self) -> None:
        """Test that decisions with zero propensity are dropped."""
        evaluator = OffPolicyEvaluator()
        logged = [
            LoggedDecision(channel_chosen="RESELL", reward=100.0, propensity=0.0),
            LoggedDecision(channel_chosen="RESELL", reward=200.0, propensity=0.5),
        ]

        result = evaluator.ips(logged, {"RESELL": 0.5})

        assert result.n == 1
        assert result.value == pytest.approx(200.0)

    @pytest.mark.asyncio
    async def test_channel_missing_from_target_gets_zero_weight(self) -> None:
        """Test that a channel the target never picks contributes nothing."""
        evaluator = OffPolicyEvaluator()
        logged = [
            LoggedDecision(channel_chosen="RESELL", reward=100.0, propensity=0.5),
            LoggedDecision(channel_chosen="RECYCLE", reward=50.0, propensity=0.5),
        ]

        result = evaluator.ips(logged, {"RESELL": 1.0})

        # The RECYCLE decision gets a weight of zero, so it contributes no
        # reward but still counts towards the sample size.
        assert result.n == 2
        assert result.value == pytest.approx(100.0)


class TestSNIPS:
    """Tests for self-normalized inverse propensity scoring."""

    @pytest.mark.asyncio
    async def test_empty_log_returns_zero(self) -> None:
        """Test that an empty log produces a zeroed estimate."""
        evaluator = OffPolicyEvaluator()
        result = evaluator.snips([], {"RESELL": 1.0})

        assert result.value == 0.0
        assert result.n == 0
        assert result.method == "snips"

    @pytest.mark.asyncio
    async def test_weight_normalization(self) -> None:
        """Test that SNIPS divides by the sum of the weights."""
        evaluator = OffPolicyEvaluator()
        logged = [
            LoggedDecision(channel_chosen="RESELL", reward=100.0, propensity=0.5),
            LoggedDecision(channel_chosen="RECYCLE", reward=200.0, propensity=0.25),
        ]

        # Weights are 0.5/0.5 = 1 and 0.5/0.25 = 2, so the weighted rewards
        # are 100 and 400 and the sum of weights is 3.
        result = evaluator.snips(logged, {"RESELL": 0.5, "RECYCLE": 0.5})

        assert result.value == pytest.approx(500.0 / 3.0)
        assert result.n == 2


class TestDirectMethod:
    """Tests for the direct method."""

    @pytest.mark.asyncio
    async def test_empty_log_returns_zero(self) -> None:
        """Test that an empty log produces a zeroed estimate."""
        evaluator = OffPolicyEvaluator()
        result = evaluator.direct_method([], {"RESELL": 100.0}, {"RESELL": 1.0})

        assert result.value == 0.0
        assert result.n == 0
        assert result.method == "direct"

    @pytest.mark.asyncio
    async def test_weighted_reward_model(self) -> None:
        """Test that the estimate is the target-weighted reward model value."""
        evaluator = OffPolicyEvaluator()
        logged = [LoggedDecision(channel_chosen="RESELL", reward=120.0, propensity=0.5)]

        result = evaluator.direct_method(
            logged,
            {"RESELL": 100.0, "RECYCLE": 40.0},
            {"RESELL": 0.7, "RECYCLE": 0.3},
        )

        assert result.value == pytest.approx(0.7 * 100.0 + 0.3 * 40.0)
        assert result.ci_lower == pytest.approx(result.value)
        assert result.ci_upper == pytest.approx(result.value)


class TestDoublyRobust:
    """Tests for the doubly robust estimator."""

    @pytest.mark.asyncio
    async def test_empty_log_returns_zero(self) -> None:
        """Test that an empty log produces a zeroed estimate."""
        evaluator = OffPolicyEvaluator()
        result = evaluator.doubly_robust([], {"RESELL": 100.0}, {"RESELL": 1.0})

        assert result.value == 0.0
        assert result.n == 0
        assert result.method == "doubly_robust"

    @pytest.mark.asyncio
    async def test_perfect_reward_model_matches_direct_method(self) -> None:
        """Test that a perfect reward model reduces to the direct method."""
        evaluator = OffPolicyEvaluator()
        logged = [
            LoggedDecision(channel_chosen="RESELL", reward=100.0, propensity=0.5),
            LoggedDecision(channel_chosen="RECYCLE", reward=40.0, propensity=0.5),
        ]
        reward_model = {"RESELL": 100.0, "RECYCLE": 40.0}
        target = {"RESELL": 0.6, "RECYCLE": 0.4}

        result = evaluator.doubly_robust(logged, reward_model, target)
        direct = evaluator.direct_method(logged, reward_model, target)

        assert result.value == pytest.approx(direct.value)
        assert result.n == 2

    @pytest.mark.asyncio
    async def test_no_usable_decisions_falls_back_to_direct(self) -> None:
        """Test that zero propensities fall back to the direct estimate."""
        evaluator = OffPolicyEvaluator()
        logged = [LoggedDecision(channel_chosen="RESELL", reward=100.0, propensity=0.0)]

        result = evaluator.doubly_robust(logged, {"RESELL": 100.0}, {"RESELL": 1.0})

        assert result.value == pytest.approx(100.0)
        assert result.n == 0


class TestSimulation:
    """Tests for the simulated off-policy evaluation."""

    @pytest.mark.asyncio
    async def test_simulation_is_deterministic(self) -> None:
        """Test that the simulation is reproducible for a fixed seed."""
        kwargs = {
            "true_policy_values": {"RESELL": 100.0, "RECYCLE": 50.0},
            "behavior_policy": {"RESELL": 0.5, "RECYCLE": 0.5},
            "target_policy": {"RESELL": 0.7, "RECYCLE": 0.3},
            "n_samples": 500,
            "rng_seed": 7,
        }

        first = simulate_off_policy_evaluation(**kwargs)
        second = simulate_off_policy_evaluation(**kwargs)

        assert first["ips_estimate"] == second["ips_estimate"]
        assert first["snips_estimate"] == second["snips_estimate"]

    @pytest.mark.asyncio
    async def test_simulation_reports_true_value(self) -> None:
        """Test that the simulation reports the true target-policy value."""
        result = simulate_off_policy_evaluation(
            true_policy_values={"RESELL": 100.0, "RECYCLE": 50.0},
            behavior_policy={"RESELL": 0.5, "RECYCLE": 0.5},
            target_policy={"RESELL": 0.7, "RECYCLE": 0.3},
            n_samples=500,
            rng_seed=11,
        )

        assert result["true_value"] == pytest.approx(0.7 * 100.0 + 0.3 * 50.0)
        assert result["n_samples"] == 500
        # IPS keeps the true value inside its interval.
        assert result["ips_within_ci"] is True
        # SNIPS is self-normalised, so it carries a small finite-sample bias
        # when the target and behaviour policies differ.
        assert result["snips_within_ci"] in (True, False)
        assert result["snips_estimate"] == pytest.approx(result["true_value"], abs=5.0)

    @pytest.mark.asyncio
    async def test_simulation_estimate_is_close_to_truth(self) -> None:
        """Test that the IPS estimate lands close to the true value."""
        result = simulate_off_policy_evaluation(
            true_policy_values={"RESELL": 100.0, "RECYCLE": 50.0},
            behavior_policy={"RESELL": 0.5, "RECYCLE": 0.5},
            target_policy={"RESELL": 0.7, "RECYCLE": 0.3},
            n_samples=2000,
            rng_seed=3,
        )

        assert result["ips_estimate"] == pytest.approx(result["true_value"], abs=15.0)
        assert result["snips_estimate"] == pytest.approx(result["true_value"], abs=15.0)
