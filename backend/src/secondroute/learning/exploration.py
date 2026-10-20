"""
Controlled exploration for Phase 6 (F6.5).

For a capped share of units (default 3 to 5%), the system may recommend
the second-best channel. Eligibility excludes high-value units and
conservative-profile retailers. Propensity of each choice is logged.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, UTC
from typing import Any, Optional, Sequence
from uuid import UUID

import numpy as np
import structlog
from pydantic import BaseModel, ConfigDict

logger = structlog.get_logger(__name__)

# Default exploration cap (3-5% of units)
DEFAULT_EXPLORATION_CAP = 0.04  # 4%

# High-value threshold (units above this value are excluded)
HIGH_VALUE_THRESHOLD = 500.0  # USD

# Conservative profile exclusion
EXCLUDED_PROFILES = {"conservative"}


@dataclass
class ExplorationEligibility:
    """Eligibility result for controlled exploration.

    Attributes:
        eligible: Whether the unit is eligible for exploration.
        reason: Reason for the decision.
        exploration_probability: Probability of exploration (0.0 if not eligible).
        propensity: Propensity score for the recommended choice.
    """

    eligible: bool
    reason: str
    exploration_probability: float = 0.0
    propensity: float = 1.0


class ExplorationService:
    """Service for controlled exploration of second-best channels.

    For a capped share of eligible units, the system may recommend the
    second-best channel instead of the best one. This enables learning
    about alternative channels while keeping risk bounded.
    """

    def __init__(
        self,
        exploration_cap: float = DEFAULT_EXPLORATION_CAP,
        high_value_threshold: float = HIGH_VALUE_THRESHOLD,
        excluded_profiles: set[str] | None = None,
    ) -> None:
        self.exploration_cap = exploration_cap
        self.high_value_threshold = high_value_threshold
        self.excluded_profiles = excluded_profiles or EXCLUDED_PROFILES

    def check_eligibility(
        self,
        risk_profile: str,
        unit_value: float,
        confidence: float,
        is_high_value: bool = False,
    ) -> ExplorationEligibility:
        """Check if a unit is eligible for controlled exploration.

        Eligibility excludes:
        - Conservative-profile retailers
        - High-value units (above threshold)
        - Low-confidence decisions

        Args:
            risk_profile: The retailer's risk profile.
            unit_value: Estimated value of the unit.
            confidence: Decision confidence.
            is_high_value: Whether the unit is flagged as high-value.

        Returns:
            ExplorationEligibility with eligibility decision.
        """
        # Check risk profile exclusion
        if risk_profile in self.excluded_profiles:
            return ExplorationEligibility(
                eligible=False,
                reason=f"Risk profile '{risk_profile}' is excluded from exploration",
                exploration_probability=0.0,
                propensity=1.0,
            )

        # Check high-value exclusion
        if is_high_value or unit_value >= self.high_value_threshold:
            return ExplorationEligibility(
                eligible=False,
                reason=f"Unit value ${unit_value:.2f} exceeds high-value threshold ${self.high_value_threshold:.2f}",
                exploration_probability=0.0,
                propensity=1.0,
            )

        # Check confidence threshold (low confidence decisions are not explored)
        if confidence < 0.5:
            return ExplorationEligibility(
                eligible=False,
                reason=f"Decision confidence {confidence:.2f} below minimum threshold 0.50",
                exploration_probability=0.0,
                propensity=1.0,
            )

        # Eligible for exploration
        # The exploration probability is the cap rate
        return ExplorationEligibility(
            eligible=True,
            reason="Eligible for controlled exploration",
            exploration_probability=self.exploration_cap,
            propensity=1.0 - self.exploration_cap,  # Propensity of choosing best (non-explored)
        )

    def should_explore(
        self,
        eligibility: ExplorationEligibility,
        rng_value: float,
    ) -> bool:
        """Determine if exploration should happen for this unit.

        Uses a deterministic RNG value to decide whether to explore.

        Args:
            eligibility: Eligibility result from check_eligibility.
            rng_value: A random value in [0, 1) for deterministic decision.

        Returns:
            True if exploration should happen.
        """
        if not eligibility.eligible:
            return False

        return rng_value < eligibility.exploration_probability

    def compute_propensity(
        self,
        explored: bool,
        eligibility: ExplorationEligibility,
    ) -> float:
        """Compute the propensity score for the recommended choice.

        The propensity is the probability of the recommended choice under
        the exploration policy. This is used for off-policy evaluation.

        Args:
            explored: Whether exploration happened.
            eligibility: Eligibility result.

        Returns:
            Propensity score (probability of the recommended choice).
        """
        if not eligibility.eligible:
            return 1.0  # No exploration, always pick best

        if explored:
            # Explored: probability of picking second-best
            return eligibility.exploration_probability
        else:
            # Not explored: probability of picking best
            return 1.0 - eligibility.exploration_probability

    def get_second_best_channel(
        self,
        candidates: list[dict],
    ) -> str | None:
        """Get the second-best channel from candidates.

        Args:
            candidates: List of candidate evaluations, sorted by net value.

        Returns:
            The second-best channel, or None if not available.
        """
        if len(candidates) < 2:
            return None

        # Sort by net_p50 descending
        sorted_candidates = sorted(
            candidates,
            key=lambda c: c.get("net_p50", 0),
            reverse=True,
        )

        return sorted_candidates[1].get("channel")