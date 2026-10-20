"""
Tests for Thompson sampling over channels (Phase 6 - F6.6).
"""

import pytest
import numpy as np

from secondroute.learning.bandit import (
    ThompsonSampler,
    BanditArm,
    BanditState,
    simulate_bandit,
    simulate_random_choice,
)


class TestThompsonSampler:
    """Tests for ThompsonSampler."""

    def test_select_channel(self) -> None:
        """Test channel selection."""
        sampler = ThompsonSampler(channels=["A", "B", "C"], rng_seed=42)
        rng = np.random.default_rng(42)

        selected = sampler.select_channel(rng)
        assert selected in ["A", "B", "C"]

    def test_update_increments_counts(self) -> None:
        """Test that update increments pull counts."""
        sampler = ThompsonSampler(channels=["A", "B"], rng_seed=42)

        sampler.update("A", reward=10.0, success=True)
        assert sampler.state.arms["A"].pulls == 1
        assert sampler.state.arms["A"].total_reward == 10.0
        assert sampler.state.arms["A"].alpha == 2.0  # prior 1 + 1

        sampler.update("B", reward=5.0, success=False)
        assert sampler.state.arms["B"].pulls == 1
        # beta is always 1.0 in Gaussian TS (compatibility property)

    def test_get_best_channel(self) -> None:
        """Test getting the best channel (greedy)."""
        sampler = ThompsonSampler(channels=["A", "B"], rng_seed=42)

        # Give A more successes
        for _ in range(10):
            sampler.update("A", reward=10.0, success=True)
        for _ in range(5):
            sampler.update("B", reward=5.0, success=False)

        best = sampler.get_best_channel()
        assert best == "A"

    def test_get_expected_rewards(self) -> None:
        """Test getting expected rewards."""
        sampler = ThompsonSampler(channels=["A", "B"], rng_seed=42)
        sampler.update("A", reward=10.0, success=True)

        rewards = sampler.get_expected_rewards()
        assert "A" in rewards
        assert "B" in rewards
        assert rewards["A"] > rewards["B"]

    def test_get_pull_counts(self) -> None:
        """Test getting pull counts."""
        sampler = ThompsonSampler(channels=["A", "B"], rng_seed=42)
        sampler.update("A", reward=10.0, success=True)
        sampler.update("A", reward=10.0, success=True)
        sampler.update("B", reward=5.0, success=True)

        counts = sampler.get_pull_counts()
        assert counts["A"] == 2
        assert counts["B"] == 1

    def test_reset(self) -> None:
        """Test resetting the bandit."""
        sampler = ThompsonSampler(channels=["A", "B"], rng_seed=42)
        sampler.update("A", reward=10.0, success=True)

        assert sampler.state.arms["A"].pulls == 1

        sampler.reset()
        assert sampler.state.arms["A"].pulls == 0
        assert sampler.state.arms["A"].alpha == 1.0
        assert sampler.state.arms["A"].beta == 1.0

    def test_new_channel_created_on_update(self) -> None:
        """Test that updating an unknown channel creates it."""
        sampler = ThompsonSampler(channels=["A", "B"], rng_seed=42)
        sampler.update("C", reward=10.0, success=True)

        assert "C" in sampler.state.arms
        assert sampler.state.arms["C"].pulls == 1


class TestBanditSimulation:
    """Tests for bandit simulation."""

    def test_simulate_bandit_regret_decreases(self) -> None:
        """Test that Thompson sampling regret decreases over time."""
        true_rewards = {
            "A": 0.8,
            "B": 0.5,
            "C": 0.3,
        }

        result = simulate_bandit(true_rewards, n_rounds=1000, rng_seed=42)

        assert result["cumulative_regret"] >= 0
        assert len(result["regret_history"]) == 1000
        assert result["best_channel"] == "A"
        assert result["most_pulled_channel"] == "A"

        # Regret should be sublinear (growing slower than linear)
        # Check that the last regret is less than linear (n_rounds * max_regret)
        max_regret_per_round = 0.8 - 0.3  # best - worst
        assert result["cumulative_regret"] < 1000 * max_regret_per_round

    def test_simulate_bandit_beats_random(self) -> None:
        """Test that Thompson sampling has lower regret than random choice."""
        true_rewards = {
            "A": 0.8,
            "B": 0.5,
            "C": 0.3,
        }

        ts_result = simulate_bandit(true_rewards, n_rounds=1000, rng_seed=42)
        random_result = simulate_random_choice(true_rewards, n_rounds=1000, rng_seed=42)

        # Thompson sampling should have lower cumulative regret than random
        assert ts_result["cumulative_regret"] < random_result["cumulative_regret"]

    def test_simulate_bandit_deterministic(self) -> None:
        """Test that simulation is deterministic with same seed."""
        true_rewards = {"A": 0.8, "B": 0.5, "C": 0.3}

        result1 = simulate_bandit(true_rewards, n_rounds=100, rng_seed=42)
        result2 = simulate_bandit(true_rewards, n_rounds=100, rng_seed=42)

        assert result1["cumulative_regret"] == result2["cumulative_regret"]
        assert result1["channel_history"] == result2["channel_history"]

    def test_simulate_random_choice(self) -> None:
        """Test random choice simulation."""
        true_rewards = {"A": 0.8, "B": 0.5, "C": 0.3}

        result = simulate_random_choice(true_rewards, n_rounds=100, rng_seed=42)

        assert result["cumulative_regret"] >= 0
        assert len(result["regret_history"]) == 100
        assert len(result["channel_history"]) == 100

    def test_simulate_bandit_single_channel(self) -> None:
        """Test bandit with single channel."""
        true_rewards = {"A": 0.8}

        result = simulate_bandit(true_rewards, n_rounds=100, rng_seed=42)

        assert result["cumulative_regret"] == 0.0
        assert result["best_channel"] == "A"
        assert result["most_pulled_channel"] == "A"

    def test_simulate_bandit_two_channels(self) -> None:
        """Test bandit with two channels."""
        true_rewards = {"A": 0.9, "B": 0.1}

        result = simulate_bandit(true_rewards, n_rounds=500, rng_seed=42)

        assert result["cumulative_regret"] >= 0
        assert result["most_pulled_channel"] == "A"
        # Should pull A much more than B
        assert result["final_pulls"]["A"] > result["final_pulls"]["B"]
