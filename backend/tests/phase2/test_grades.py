"""
Tests for the grade rules (F2.3).
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from secondroute.condition.grades import (
    GRADES,
    InspectionSignals,
    channel_eligibility,
    condition_score,
    expected_grade_level,
    grade_distribution,
)


def make_signals(
    battery: float = 90.0,
    grade: str = "B",
    tests: dict[str, bool] | None = None,
    lock: str = "none",
) -> InspectionSignals:
    """Build inspection signals for a test."""
    return InspectionSignals(
        battery_health_pct=battery,
        cosmetic_grade=grade,
        functional_tests=tests if tests is not None else {"display": True, "keyboard": True},
        accessories={"charger": True},
        activation_lock=lock,
    )


class TestProbabilities:
    """Probabilities must always form a proper distribution."""

    def test_probabilities_sum_to_one(self) -> None:
        """The four probabilities sum to exactly one."""
        distribution = grade_distribution(make_signals())
        assert sum(distribution.probabilities.values()) == pytest.approx(1.0, abs=1e-9)

    def test_all_grades_are_present(self) -> None:
        """Every grade has a probability."""
        distribution = grade_distribution(make_signals())
        assert set(distribution.probabilities) == set(GRADES)

    def test_probabilities_are_non_negative(self) -> None:
        """No probability is negative."""
        distribution = grade_distribution(make_signals())
        assert all(p >= 0.0 for p in distribution.probabilities.values())

    def test_probabilities_do_not_exceed_one(self) -> None:
        """No probability exceeds one."""
        distribution = grade_distribution(make_signals())
        assert all(p <= 1.0 for p in distribution.probabilities.values())

    @pytest.mark.parametrize(
        ("battery", "grade", "tests"),
        [
            (100.0, "A", {"a": True, "b": True}),
            (55.0, "D", {"a": False, "b": False}),
            (80.0, "C", {"a": True, "b": False}),
        ],
    )
    def test_sum_to_one_across_the_input_space(
        self, battery: float, grade: str, tests: dict[str, bool]
    ) -> None:
        """The sum holds across the whole input space."""
        distribution = grade_distribution(make_signals(battery, grade, tests))
        assert sum(distribution.probabilities.values()) == pytest.approx(1.0, abs=1e-9)


class TestMonotonicity:
    """Worse battery health must never increase the probability of grade A."""

    def test_worse_battery_never_increases_grade_a(self) -> None:
        """P(A) is non-increasing as battery health drops."""
        previous = None
        for battery in range(100, 49, -1):
            distribution = grade_distribution(make_signals(battery=float(battery)))
            current = distribution.probabilities["A"]
            if previous is not None:
                assert current <= previous + 1e-12, (
                    f"P(A) rose from {previous} to {current} at battery {battery}"
                )
            previous = current

    def test_better_battery_never_decreases_grade_a(self) -> None:
        """P(A) is non-decreasing as battery health rises."""
        previous = None
        for battery in range(50, 101):
            distribution = grade_distribution(make_signals(battery=float(battery)))
            current = distribution.probabilities["A"]
            if previous is not None:
                assert current >= previous - 1e-12
            previous = current

    def test_expected_level_is_monotone_in_battery(self) -> None:
        """The expected grade level rises with battery health."""
        previous = None
        for battery in range(50, 101):
            level = expected_grade_level(condition_score(make_signals(battery=float(battery))))
            if previous is not None:
                assert level >= previous - 1e-12
            previous = level

    def test_failures_reduce_grade_a(self) -> None:
        """More failed tests never increase P(A)."""
        without = grade_distribution(make_signals(tests={"a": True, "b": True}))
        with_failure = grade_distribution(make_signals(tests={"a": True, "b": False}))
        assert with_failure.probabilities["A"] <= without.probabilities["A"] + 1e-12

    def test_worse_cosmetic_grade_reduces_grade_a(self) -> None:
        """A worse cosmetic grade never increases P(A)."""
        previous = None
        for grade in ("A", "B", "C", "D"):
            current = grade_distribution(make_signals(grade=grade)).probabilities["A"]
            if previous is not None:
                assert current <= previous + 1e-12
            previous = current


class TestSignals:
    """Reading signals from stored records."""

    def test_from_inspection_mapping(self) -> None:
        """A plain mapping is read correctly."""
        signals = InspectionSignals.from_inspection(
            {
                "battery_health_pct": "88.5",
                "battery_cycles": "210",
                "cosmetic_grade": "B",
                "functional_tests": '{"display": true}',
                "accessories": '{"charger": false}',
                "activation_lock": "none",
            }
        )
        assert signals.battery_health_pct == pytest.approx(88.5)
        assert signals.battery_cycles == 210
        assert signals.cosmetic_grade == "B"
        assert signals.functional_tests == {"display": True}
        assert signals.accessories == {"charger": False}

    def test_from_inspection_handles_missing_values(self) -> None:
        """Missing values fall back to safe defaults.

        A missing battery reading is not a battery at zero per cent: it is no
        reading at all, which is what a device without a battery produces.
        """
        signals = InspectionSignals.from_inspection({})
        assert signals.battery_health_pct is None
        assert signals.battery_cycles is None
        assert signals.activation_lock == "unknown"

    def test_from_inspection_handles_bad_battery(self) -> None:
        """A non-numeric battery reading is not a battery reading either."""
        signals = InspectionSignals.from_inspection({"battery_health_pct": "not a number"})
        assert signals.battery_health_pct is None
        # An unreadable reading is treated exactly as an absent one.
        assert condition_score(signals) == condition_score(InspectionSignals.from_inspection({}))

    def test_from_inspection_handles_json_string(self) -> None:
        """JSON strings are decoded."""
        signals = InspectionSignals.from_inspection(
            {
                "functional_tests": '{"display": true, "ports": false}',
                "accessories": "not json",
            }
        )
        assert signals.functional_tests == {"display": True, "ports": False}
        assert signals.accessories == {}


class TestEligibility:
    """Channel eligibility is deterministic policy."""

    def test_activation_lock_blocks_resale(self) -> None:
        """A locked unit cannot be resold."""
        signals = make_signals(lock="present")
        distribution = grade_distribution(signals)
        eligibility = channel_eligibility(signals, distribution)

        assert eligibility["RESELL_OPEN_BOX"][0] is False
        assert eligibility["RESELL_REFURB"][0] is False
        assert eligibility["RECYCLE"][0] is True
        assert eligibility["DONATE"][0] is True
        assert "Activation lock" in (eligibility["RESELL_OPEN_BOX"][1] or "")

    def test_poor_condition_blocks_open_box(self) -> None:
        """A worn unit cannot be sold as open-box."""
        signals = make_signals(battery=62.0, grade="D", tests={"a": False, "b": False})
        distribution = grade_distribution(signals)
        eligibility = channel_eligibility(signals, distribution)

        assert eligibility["RESELL_OPEN_BOX"][0] is False
        assert eligibility["RESELL_REFURB"][0] is True

    def test_good_condition_allows_everything(self) -> None:
        """A healthy unit can take any channel."""
        signals = make_signals(battery=98.0, grade="A")
        distribution = grade_distribution(signals)
        eligibility = channel_eligibility(signals, distribution)

        assert all(allowed for allowed, _ in eligibility.values())


@settings(max_examples=50, deadline=None)
@given(
    battery=st.floats(min_value=0.0, max_value=100.0),
    grade=st.sampled_from(GRADES),
    failure_rate=st.floats(min_value=0.0, max_value=1.0),
)
def test_distribution_is_always_valid(battery: float, grade: str, failure_rate: float) -> None:
    """For any input the distribution is a valid probability distribution."""
    tests = {"t1": True, "t2": failure_rate < 0.5, "t3": True, "t4": failure_rate < 0.25}
    distribution = grade_distribution(make_signals(battery, grade, tests))
    total = sum(distribution.probabilities.values())
    assert total == pytest.approx(1.0, abs=1e-9)
    assert all(p >= 0.0 for p in distribution.probabilities.values())
