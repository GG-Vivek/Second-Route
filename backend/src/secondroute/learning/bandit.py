"""
Thompson sampling over channels for Phase 6 (F6.6).

Bandit policy using NumPy, operating only within exploration-eligible units.
Uses Gaussian Thompson sampling for continuous rewards.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class BanditArm:
    channel: str
    n: int = 0
    sum_rewards: float = 0.0
    sum_sq_rewards: float = 0.0

    @property
    def mean_reward(self) -> float:
        if self.n == 0:
            return 0.0
        return self.sum_rewards / self.n

    @property
    def variance(self) -> float:
        if self.n < 2:
            return 1.0
        mean = self.mean_reward
        return max(self.sum_sq_rewards / self.n - mean * mean, 1e-6)

    @property
    def pulls(self) -> int:
        return self.n

    @property
    def total_reward(self) -> float:
        return self.sum_rewards

    @property
    def alpha(self) -> float:
        return self.n + 1.0

    @property
    def beta(self) -> float:
        return 1.0


@dataclass
class BanditState:
    arms: dict[str, BanditArm] = field(default_factory=dict)
    rng_seed: int = 42

    def get_rng(self) -> np.random.Generator:
        return np.random.default_rng(self.rng_seed)


class ThompsonSampler:
    def __init__(
        self,
        channels: list[str],
        rng_seed: int = 42,
        prior_mean: float = 0.0,
        prior_variance: float = 1.0,
    ) -> None:
        self.channels = channels
        self.rng_seed = rng_seed
        self.prior_mean = prior_mean
        self.prior_variance = prior_variance
        self.state = BanditState(
            arms={ch: BanditArm(channel=ch) for ch in channels},
            rng_seed=rng_seed,
        )

    def select_channel(self, rng: np.random.Generator | None = None) -> str:
        if rng is None:
            rng = self.state.get_rng()

        samples = {}
        for channel, arm in self.state.arms.items():
            if arm.n == 0:
                samples[channel] = rng.normal(self.prior_mean, np.sqrt(self.prior_variance))
            else:
                std = np.sqrt(arm.variance / (arm.n + 1))
                samples[channel] = rng.normal(arm.mean_reward, std)

        selected = max(samples, key=lambda ch: samples[ch])
        return selected

    def update(self, channel: str, reward: float, success: bool = True) -> None:  # noqa: ARG002
        if channel not in self.state.arms:
            self.state.arms[channel] = BanditArm(channel=channel)

        arm = self.state.arms[channel]
        arm.n += 1
        arm.sum_rewards += reward
        arm.sum_sq_rewards += reward * reward

    def get_best_channel(self) -> str:
        if not self.state.arms:
            return self.channels[0] if self.channels else ""

        best_channel = max(
            self.state.arms.keys(),
            key=lambda ch: self.state.arms[ch].mean_reward,
        )
        return best_channel

    def get_expected_rewards(self) -> dict[str, float]:
        return {ch: arm.mean_reward for ch, arm in self.state.arms.items()}

    def get_pull_counts(self) -> dict[str, int]:
        return {ch: arm.n for ch, arm in self.state.arms.items()}

    def reset(self) -> None:
        self.state = BanditState(
            arms={ch: BanditArm(channel=ch) for ch in self.channels},
            rng_seed=self.rng_seed,
        )


def simulate_bandit(
    true_rewards: dict[str, float],
    n_rounds: int = 1000,
    rng_seed: int = 42,
) -> dict[str, Any]:
    channels = list(true_rewards.keys())
    sampler = ThompsonSampler(channels=channels, rng_seed=rng_seed)
    rng = np.random.default_rng(rng_seed)

    cumulative_regret = 0.0
    regret_history = []
    channel_history = []

    best_reward = max(true_rewards.values())

    for _ in range(n_rounds):
        selected = sampler.select_channel(rng)
        _ = true_rewards[selected] + rng.normal(0, 0.1)

        sampler.update(selected, true_rewards[selected] + rng.normal(0, 0.1))

        regret = best_reward - true_rewards[selected]
        cumulative_regret += regret
        regret_history.append(cumulative_regret)
        channel_history.append(selected)

    return {
        "cumulative_regret": cumulative_regret,
        "regret_history": regret_history,
        "channel_history": channel_history,
        "final_pulls": sampler.get_pull_counts(),
        "final_expected_rewards": sampler.get_expected_rewards(),
        "best_channel": max(true_rewards, key=lambda ch: true_rewards[ch]),
        "most_pulled_channel": max(
            sampler.get_pull_counts(), key=lambda ch: sampler.get_pull_counts()[ch]
        ),
    }


def simulate_random_choice(
    true_rewards: dict[str, float],
    n_rounds: int = 1000,
    rng_seed: int = 42,
) -> dict[str, Any]:
    channels = list(true_rewards.keys())
    rng = np.random.default_rng(rng_seed)

    cumulative_regret = 0.0
    regret_history = []
    channel_history = []

    best_reward = max(true_rewards.values())

    for _ in range(n_rounds):
        selected = rng.choice(channels)
        _ = true_rewards[selected] + rng.normal(0, 0.1)

        regret = best_reward - true_rewards[selected]
        cumulative_regret += regret
        regret_history.append(cumulative_regret)
        channel_history.append(selected)

    return {
        "cumulative_regret": cumulative_regret,
        "regret_history": regret_history,
        "channel_history": channel_history,
    }
