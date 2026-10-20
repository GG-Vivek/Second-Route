"""
Promotion gate for Phase 6.

Provides the promotion gate logic for promoting shadow models to production.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class PromotionRecord:
    """Record of a model promotion decision."""

    id: UUID
    candidate_version: str
    champion_version: str
    promoted: bool
    reason: str
    metrics: dict
    decided_at: datetime
    decided_by: Optional[str] = None


@dataclass
class PromotionResult:
    """Result of a promotion evaluation."""

    promoted: bool
    reason: str
    metrics_comparison: dict


class PromotionGate:
    """Gate for promoting shadow models to production."""

    def __init__(
        self,
        min_sample_size: int = 1000,
        required_improvement: float = 0.01,
        max_regression: float = 0.02,
    ):
        self.min_sample_size = min_sample_size
        self.required_improvement = required_improvement
        self.max_regression = max_regression

    async def evaluate(
        self,
        candidate_metrics: dict,
        champion_metrics: dict,
        sample_size: int,
    ) -> PromotionResult:
        """
        Evaluate whether to promote a candidate model.

        Args:
            candidate_metrics: Metrics from the candidate model
            champion_metrics: Metrics from the current champion model
            sample_size: Number of samples used for evaluation

        Returns:
            PromotionResult with promotion decision and reasoning
        """
        if sample_size < self.min_sample_size:
            return PromotionResult(
                promoted=False,
                reason=f"Insufficient sample size: {sample_size} < {self.min_sample_size}",
                metrics_comparison={},
            )

        # Compare metrics
        candidate_mae = candidate_metrics.get("mae", float("inf"))
        champion_mae = champion_metrics.get("mae", float("inf"))
        candidate_ece = candidate_metrics.get("ece", float("inf"))
        champion_ece = champion_metrics.get("ece", float("inf"))

        mae_improvement = champion_mae - candidate_mae
        ece_improvement = champion_ece - candidate_ece

        # Check if candidate is better
        mae_better = mae_improvement >= self.required_improvement
        ece_better = ece_improvement >= 0  # ECE should not regress

        # Check for regression
        mae_regression = candidate_mae - champion_mae
        ece_regression = candidate_ece - champion_ece

        if mae_regression > self.max_regression or ece_regression > self.max_regression:
            return PromotionResult(
                promoted=False,
                reason=f"Regression detected: MAE delta={mae_regression:.4f}, ECE delta={ece_regression:.4f}",
                metrics_comparison={
                    "candidate_mae": candidate_mae,
                    "champion_mae": champion_mae,
                    "candidate_ece": candidate_ece,
                    "champion_ece": champion_ece,
                },
            )

        if mae_better and ece_better:
            return PromotionResult(
                promoted=True,
                reason=f"Improvement: MAE {mae_improvement:.4f}, ECE {ece_improvement:.4f}",
                metrics_comparison={
                    "candidate_mae": candidate_mae,
                    "champion_mae": champion_mae,
                    "candidate_ece": candidate_ece,
                    "champion_ece": champion_ece,
                },
            )

        return PromotionResult(
            promoted=False,
            reason="No significant improvement",
            metrics_comparison={
                "candidate_mae": candidate_mae,
                "champion_mae": champion_mae,
                "candidate_ece": candidate_ece,
                "champion_ece": champion_ece,
            },
        )
