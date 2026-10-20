"""
Off-policy evaluation for Phase 6 (F6.7).

Inverse propensity scoring to estimate the value of a proposed policy
from logged decisions, with confidence intervals.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

import numpy as np
import structlog
from pydantic import BaseModel, ConfigDict

logger = structlog.get_logger(__name__)


@dataclass
class LoggedDecision:
    """A logged decision with propensity.

    Attributes:
        channel_chosen: The channel that was chosen.
        reward: The observed reward (net value).
        propensity: The probability of choosing this channel under the logging policy.
        context: Optional context features.
    """

    channel_chosen: str
    reward: float
    propensity: float
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyValue:
    """Estimated value of a policy.

    Attributes:
        value: The estimated policy value.
        std_error: Standard error of the estimate.
        ci_lower: Lower bound of confidence interval.
        ci_upper: Upper bound of confidence interval.
        n: Number of samples used.
        method: The estimation method used.
    """

    value: float
    std_error: float
    ci_lower: float
    ci_upper: float
    n: int
    method: str


class OffPolicyEvaluator:
    """Off-policy evaluation using Inverse Propensity Scoring.

    Estimates the value of a proposed (target) policy from logged decisions
    collected under a different (behavior) policy.
    """

    def __init__(self, confidence_level: float = 0.95) -> None:
        self.confidence_level = confidence_level
        self.z_score = self._z_score(confidence_level)

    @staticmethod
    def _z_score(confidence_level: float) -> float:
        """Get z-score for confidence level."""
        try:
            from scipy import stats  # type: ignore[import-untyped]

            return float(stats.norm.ppf((1 + confidence_level) / 2))
        except ImportError:
            # Fallback to approximate z-score for 95% confidence
            if confidence_level >= 0.99:
                return 2.576
            elif confidence_level >= 0.95:
                return 1.96
            elif confidence_level >= 0.90:
                return 1.645
            else:
                return 1.96

    def ips(
        self,
        logged_decisions: Sequence[LoggedDecision],
        target_policy: dict[str, float],
    ) -> PolicyValue:
        """Inverse Propensity Scoring estimate.

        For each logged decision, the weight is:
            w = target_propensity / behavior_propensity

        The estimated value is the weighted average of rewards.

        Args:
            logged_decisions: List of logged decisions.
            target_policy: Dictionary mapping channel -> probability under target policy.

        Returns:
            PolicyValue with estimate and confidence interval.
        """
        if not logged_decisions:
            return PolicyValue(
                value=0.0,
                std_error=0.0,
                ci_lower=0.0,
                ci_upper=0.0,
                n=0,
                method="ips",
            )

        weights = []
        weighted_rewards = []

        for decision in logged_decisions:
            channel = decision.channel_chosen
            target_prob = target_policy.get(channel, 0.0)
            behavior_prob = decision.propensity

            if behavior_prob <= 0:
                continue

            weight = target_prob / behavior_prob
            weights.append(weight)
            weighted_rewards.append(weight * decision.reward)

        if not weights:
            return PolicyValue(
                value=0.0,
                std_error=0.0,
                ci_lower=0.0,
                ci_upper=0.0,
                n=0,
                method="ips",
            )

        n = len(weights)
        value = sum(weighted_rewards) / n

        # Compute variance
        mean_weighted = sum(weighted_rewards) / n
        variance = sum((wr - mean_weighted) ** 2 for wr in weighted_rewards) / n
        std_error = (variance / n) ** 0.5 if n > 0 else 0.0

        # Confidence interval
        margin = self.z_score * std_error
        ci_lower = value - margin
        ci_upper = value + margin

        return PolicyValue(
            value=value,
            std_error=std_error,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            n=n,
            method="ips",
        )

    def snips(
        self,
        logged_decisions: Sequence[LoggedDecision],
        target_policy: dict[str, float],
    ) -> PolicyValue:
        """Self-Normalized Inverse Propensity Scoring estimate.

        Normalizes the weights to reduce variance.

        Args:
            logged_decisions: List of logged decisions.
            target_policy: Dictionary mapping channel -> probability under target policy.

        Returns:
            PolicyValue with estimate and confidence interval.
        """
        if not logged_decisions:
            return PolicyValue(
                value=0.0,
                std_error=0.0,
                ci_lower=0.0,
                ci_upper=0.0,
                n=0,
                method="snips",
            )

        weights = []
        weighted_rewards = []

        for decision in logged_decisions:
            channel = decision.channel_chosen
            target_prob = target_policy.get(channel, 0.0)
            behavior_prob = decision.propensity

            if behavior_prob <= 0:
                continue

            weight = target_prob / behavior_prob
            weights.append(weight)
            weighted_rewards.append(weight * decision.reward)

        if not weights:
            return PolicyValue(
                value=0.0,
                std_error=0.0,
                ci_lower=0.0,
                ci_upper=0.0,
                n=0,
                method="snips",
            )

        n = len(weights)
        sum_weights = sum(weights)
        if sum_weights <= 0:
            return PolicyValue(
                value=0.0,
                std_error=0.0,
                ci_lower=0.0,
                ci_upper=0.0,
                n=n,
                method="snips",
            )

        value = sum(weighted_rewards) / sum_weights

        # Compute variance (self-normalized)
        mean_weighted = value
        variance = sum(
            (wr / sum_weights - mean_weighted * (w / sum_weights)) ** 2
            for wr, w in zip(weighted_rewards, weights, strict=False)
        )
        std_error = (variance / n) ** 0.5 if n > 0 else 0.0

        margin = self.z_score * std_error
        ci_lower = value - margin
        ci_upper = value + margin

        return PolicyValue(
            value=value,
            std_error=std_error,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            n=n,
            method="snips",
        )

    def direct_method(
        self,
        logged_decisions: Sequence[LoggedDecision],
        reward_model: dict[str, float],
        target_policy: dict[str, float],
    ) -> PolicyValue:
        """Direct method estimate using a reward model.

        Estimates the value as the expected reward under the target policy,
        using the reward model to predict rewards for each channel.

        Args:
            logged_decisions: List of logged decisions.
            reward_model: Dictionary mapping channel -> predicted reward.
            target_policy: Dictionary mapping channel -> probability under target policy.

        Returns:
            PolicyValue with estimate and confidence interval.
        """
        if not logged_decisions:
            return PolicyValue(
                value=0.0,
                std_error=0.0,
                ci_lower=0.0,
                ci_upper=0.0,
                n=0,
                method="direct",
            )

        # Estimate value as expected reward under target policy
        value = 0.0
        for channel, prob in target_policy.items():
            predicted_reward = reward_model.get(channel, 0.0)
            value += prob * predicted_reward

        # Bootstrap confidence interval (simplified)
        n = len(logged_decisions)
        std_error = 0.0  # Direct method doesn't have variance estimate without bootstrap
        margin = self.z_score * std_error if std_error > 0 else 0.0

        return PolicyValue(
            value=value,
            std_error=std_error,
            ci_lower=value - margin,
            ci_upper=value + margin,
            n=n,
            method="direct",
        )

    def doubly_robust(
        self,
        logged_decisions: Sequence[LoggedDecision],
        reward_model: dict[str, float],
        target_policy: dict[str, float],
    ) -> PolicyValue:
        """Doubly robust estimate combining IPS and direct method.

        Args:
            logged_decisions: List of logged decisions.
            reward_model: Dictionary mapping channel -> predicted reward.
            target_policy: Dictionary mapping channel -> probability under target policy.

        Returns:
            PolicyValue with estimate and confidence interval.
        """
        if not logged_decisions:
            return PolicyValue(
                value=0.0,
                std_error=0.0,
                ci_lower=0.0,
                ci_upper=0.0,
                n=0,
                method="doubly_robust",
            )

        # Compute IPS residuals
        ips_values = []
        for decision in logged_decisions:
            channel = decision.channel_chosen
            target_prob = target_policy.get(channel, 0.0)
            behavior_prob = decision.propensity

            if behavior_prob <= 0:
                continue

            predicted_reward = reward_model.get(channel, 0.0)
            residual = decision.reward - predicted_reward
            weight = target_prob / behavior_prob
            ips_values.append(weight * residual)

        # Add direct method estimate
        direct_value = 0.0
        for channel, prob in target_policy.items():
            predicted_reward = reward_model.get(channel, 0.0)
            direct_value += prob * predicted_reward

        n = len(ips_values)
        if n == 0:
            return PolicyValue(
                value=direct_value,
                std_error=0.0,
                ci_lower=direct_value,
                ci_upper=direct_value,
                n=0,
                method="doubly_robust",
            )

        ips_residual = sum(ips_values) / n
        value = direct_value + ips_residual

        # Variance estimate
        variance = sum((v - ips_residual) ** 2 for v in ips_values) / n
        std_error = (variance / n) ** 0.5 if n > 0 else 0.0

        margin = self.z_score * std_error
        ci_lower = value - margin
        ci_upper = value + margin

        return PolicyValue(
            value=value,
            std_error=std_error,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            n=n,
            method="doubly_robust",
        )


def simulate_off_policy_evaluation(
    true_policy_values: dict[str, float],
    behavior_policy: dict[str, float],
    target_policy: dict[str, float],
    n_samples: int = 1000,
    rng_seed: int = 42,
) -> dict[str, Any]:
    """Simulate off-policy evaluation with known true values.

    Args:
        true_policy_values: Dictionary of channel -> true mean reward.
        behavior_policy: Dictionary of channel -> probability under behavior policy.
        target_policy: Dictionary of channel -> probability under target policy.
        n_samples: Number of logged decisions to generate.
        rng_seed: Seed for the RNG.

    Returns:
        Dictionary with simulation results including true value and estimates.
    """
    rng = np.random.default_rng(rng_seed)
    channels = list(true_policy_values.keys())

    # Compute true value of target policy
    true_value = sum(target_policy.get(ch, 0.0) * true_policy_values[ch] for ch in channels)

    # Generate logged decisions under behavior policy
    logged_decisions = []
    for _ in range(n_samples):
        # Sample channel from behavior policy
        channel = rng.choice(channels, p=[behavior_policy.get(ch, 0.0) for ch in channels])
        propensity = behavior_policy.get(channel, 0.0)

        # Observe reward
        reward = true_policy_values[channel] + rng.normal(0, 0.1)

        logged_decisions.append(
            LoggedDecision(
                channel_chosen=channel,
                reward=reward,
                propensity=propensity,
            )
        )

    # Run IPS
    evaluator = OffPolicyEvaluator(confidence_level=0.95)
    ips_result = evaluator.ips(logged_decisions, target_policy)
    snips_result = evaluator.snips(logged_decisions, target_policy)

    return {
        "true_value": true_value,
        "ips_estimate": ips_result.value,
        "ips_ci_lower": ips_result.ci_lower,
        "ips_ci_upper": ips_result.ci_upper,
        "snips_estimate": snips_result.value,
        "snips_ci_lower": snips_result.ci_lower,
        "snips_ci_upper": snips_result.ci_upper,
        "n_samples": n_samples,
        "ips_within_ci": ips_result.ci_lower <= true_value <= ips_result.ci_upper,
        "snips_within_ci": snips_result.ci_lower <= true_value <= snips_result.ci_upper,
    }
