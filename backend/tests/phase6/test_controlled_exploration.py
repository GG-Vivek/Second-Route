"""
Tests for controlled exploration (Phase 6 - F6.5).
"""

import pytest
from datetime import datetime, timezone, UTC

from secondroute.learning.exploration import (
    ExplorationService,
    ExplorationEligibility,
    DEFAULT_EXPLORATION_CAP,
    HIGH_VALUE_THRESHOLD,
)


class TestExplorationEligibility:
    """Tests for exploration eligibility checking."""

    def test_eligible_unit(self) -> None:
        """Test that a normal unit is eligible for exploration."""
        service = ExplorationService()
        result = service.check_eligibility(
            risk_profile="balanced",
            unit_value=200.0,
            confidence=0.85,
        )

        assert result.eligible is True
        assert result.exploration_probability == DEFAULT_EXPLORATION_CAP
        assert "Eligible" in result.reason

    def test_conservative_profile_excluded(self) -> None:
        """Test that conservative profile retailers are excluded."""
        service = ExplorationService()
        result = service.check_eligibility(
            risk_profile="conservative",
            unit_value=200.0,
            confidence=0.85,
        )

        assert result.eligible is False
        assert "conservative" in result.reason
        assert result.exploration_probability == 0.0

    def test_high_value_excluded(self) -> None:
        """Test that high-value units are excluded."""
        service = ExplorationService()
        result = service.check_eligibility(
            risk_profile="balanced",
            unit_value=600.0,  # Above threshold
            confidence=0.85,
        )

        assert result.eligible is False
        assert "high-value threshold" in result.reason
        assert result.exploration_probability == 0.0

    def test_high_value_flag_excluded(self) -> None:
        """Test that explicitly flagged high-value units are excluded."""
        service = ExplorationService()
        result = service.check_eligibility(
            risk_profile="balanced",
            unit_value=200.0,
            confidence=0.85,
            is_high_value=True,
        )

        assert result.eligible is False
        assert "high-value threshold" in result.reason

    def test_low_confidence_excluded(self) -> None:
        """Test that low-confidence decisions are excluded."""
        service = ExplorationService()
        result = service.check_eligibility(
            risk_profile="balanced",
            unit_value=200.0,
            confidence=0.40,  # Below threshold
        )

        assert result.eligible is False
        assert "confidence" in result.reason
        assert result.exploration_probability == 0.0

    def test_aggressive_profile_eligible(self) -> None:
        """Test that aggressive profile retailers are eligible."""
        service = ExplorationService()
        result = service.check_eligibility(
            risk_profile="aggressive",
            unit_value=200.0,
            confidence=0.85,
        )

        assert result.eligible is True

    def test_custom_exploration_cap(self) -> None:
        """Test with custom exploration cap."""
        service = ExplorationService(exploration_cap=0.05)
        result = service.check_eligibility(
            risk_profile="balanced",
            unit_value=200.0,
            confidence=0.85,
        )

        assert result.eligible is True
        assert result.exploration_probability == 0.05

    def test_custom_high_value_threshold(self) -> None:
        """Test with custom high-value threshold."""
        service = ExplorationService(high_value_threshold=1000.0)
        result = service.check_eligibility(
            risk_profile="balanced",
            unit_value=600.0,  # Below custom threshold
            confidence=0.85,
        )

        assert result.eligible is True


class TestShouldExplore:
    """Tests for exploration decision."""

    def test_not_eligible_never_explores(self) -> None:
        """Test that non-eligible units never explore."""
        service = ExplorationService()
        eligibility = ExplorationEligibility(
            eligible=False,
            reason="Excluded",
            exploration_probability=0.0,
        )

        assert service.should_explore(eligibility, 0.0) is False
        assert service.should_explore(eligibility, 0.5) is False
        assert service.should_explore(eligibility, 0.99) is False

    def test_eligible_explores_below_threshold(self) -> None:
        """Test that eligible units explore when RNG < probability."""
        service = ExplorationService(exploration_cap=0.04)
        eligibility = ExplorationEligibility(
            eligible=True,
            reason="Eligible",
            exploration_probability=0.04,
        )

        # RNG value below threshold -> explore
        assert service.should_explore(eligibility, 0.02) is True
        # RNG value above threshold -> don't explore
        assert service.should_explore(eligibility, 0.05) is False

    def test_boundary_values(self) -> None:
        """Test boundary values for exploration decision."""
        service = ExplorationService(exploration_cap=0.04)
        eligibility = ExplorationEligibility(
            eligible=True,
            reason="Eligible",
            exploration_probability=0.04,
        )

        # Exactly at threshold -> don't explore (rng_value < probability)
        assert service.should_explore(eligibility, 0.04) is False
        # Just below threshold -> explore
        assert service.should_explore(eligibility, 0.0399) is True


class TestPropensity:
    """Tests for propensity computation."""

    def test_not_eligible_propensity_is_1(self) -> None:
        """Test that non-eligible units have propensity 1.0."""
        service = ExplorationService()
        eligibility = ExplorationEligibility(
            eligible=False,
            reason="Excluded",
        )

        assert service.compute_propensity(explored=True, eligibility=eligibility) == 1.0
        assert service.compute_propensity(explored=False, eligibility=eligibility) == 1.0

    def test_explored_propensity(self) -> None:
        """Test propensity when exploration happens."""
        service = ExplorationService(exploration_cap=0.04)
        eligibility = ExplorationEligibility(
            eligible=True,
            reason="Eligible",
            exploration_probability=0.04,
        )

        propensity = service.compute_propensity(explored=True, eligibility=eligibility)
        assert propensity == 0.04

    def test_not_explored_propensity(self) -> None:
        """Test propensity when exploration doesn't happen."""
        service = ExplorationService(exploration_cap=0.04)
        eligibility = ExplorationEligibility(
            eligible=True,
            reason="Eligible",
            exploration_probability=0.04,
        )

        propensity = service.compute_propensity(explored=False, eligibility=eligibility)
        assert propensity == 0.96


class TestSecondBestChannel:
    """Tests for second-best channel selection."""

    def test_get_second_best(self) -> None:
        """Test getting the second-best channel."""
        service = ExplorationService()
        candidates = [
            {"channel": "RESELL_OPEN_BOX", "net_p50": 1000},
            {"channel": "RESELL_REFURB", "net_p50": 800},
            {"channel": "RECYCLE", "net_p50": 50},
        ]

        second_best = service.get_second_best_channel(candidates)
        assert second_best == "RESELL_REFURB"

    def test_single_candidate_returns_none(self) -> None:
        """Test that single candidate returns None."""
        service = ExplorationService()
        candidates = [
            {"channel": "RESELL_OPEN_BOX", "net_p50": 1000},
        ]

        second_best = service.get_second_best_channel(candidates)
        assert second_best is None

    def test_empty_candidates_returns_none(self) -> None:
        """Test that empty candidates returns None."""
        service = ExplorationService()
        second_best = service.get_second_best_channel([])
        assert second_best is None

    def test_unsorted_candidates(self) -> None:
        """Test that candidates are sorted before selecting second-best."""
        service = ExplorationService()
        candidates = [
            {"channel": "RECYCLE", "net_p50": 50},
            {"channel": "RESELL_OPEN_BOX", "net_p50": 1000},
            {"channel": "RESELL_REFURB", "net_p50": 800},
        ]

        second_best = service.get_second_best_channel(candidates)
        assert second_best == "RESELL_REFURB"


class TestNoExplorationOnExcluded:
    """Tests verifying no exploration on excluded units."""

    def test_conservative_never_explores(self) -> None:
        """Test that conservative profile units never explore."""
        service = ExplorationService()
        eligibility = service.check_eligibility(
            risk_profile="conservative",
            unit_value=100.0,
            confidence=0.90,
        )

        # Even with favorable RNG, should not explore
        assert service.should_explore(eligibility, 0.0) is False
        assert service.should_explore(eligibility, 0.01) is False
        assert service.should_explore(eligibility, 0.99) is False

    def test_high_value_never_explores(self) -> None:
        """Test that high-value units never explore."""
        service = ExplorationService()
        eligibility = service.check_eligibility(
            risk_profile="balanced",
            unit_value=1000.0,
            confidence=0.90,
        )

        assert service.should_explore(eligibility, 0.0) is False
        assert service.should_explore(eligibility, 0.01) is False

    def test_low_confidence_never_explores(self) -> None:
        """Test that low-confidence decisions never explore."""
        service = ExplorationService()
        eligibility = service.check_eligibility(
            risk_profile="balanced",
            unit_value=100.0,
            confidence=0.30,
        )

        assert service.should_explore(eligibility, 0.0) is False
        assert service.should_explore(eligibility, 0.01) is False