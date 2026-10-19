"""
Tests for the synthetic returns generator (F2.1).
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from synthetic.generator import (
    ACCESSORY_PRESENT_PROBABILITY,
    FUNCTIONAL_TESTS,
    GRADES,
    SyntheticReturnGenerator,
)


class TestDeterminism:
    """The generator must be fully reproducible."""

    def test_same_seed_gives_same_hash(self) -> None:
        """Same seed, same output hash."""
        first = SyntheticReturnGenerator(seed=42).generate(200)
        second = SyntheticReturnGenerator(seed=42).generate(200)
        assert SyntheticReturnGenerator.dataset_hash(first) == (
            SyntheticReturnGenerator.dataset_hash(second)
        )

    def test_different_seed_gives_different_hash(self) -> None:
        """Different seed, different output hash."""
        first = SyntheticReturnGenerator(seed=42).generate(200)
        second = SyntheticReturnGenerator(seed=43).generate(200)
        assert SyntheticReturnGenerator.dataset_hash(first) != (
            SyntheticReturnGenerator.dataset_hash(second)
        )

    def test_generated_count_is_exact(self) -> None:
        """The generator returns exactly the requested number of rows."""
        rows = SyntheticReturnGenerator(seed=7).generate(137)
        assert len(rows) == 137

    def test_zero_rows_is_allowed(self) -> None:
        """Generating zero rows is valid."""
        assert SyntheticReturnGenerator(seed=7).generate(0) == []

    def test_negative_count_raises(self) -> None:
        """A negative count is rejected."""
        with pytest.raises(ValueError):
            SyntheticReturnGenerator(seed=7).generate(-1)

    def test_price_observations_are_deterministic(self) -> None:
        """The price stream is deterministic as well."""
        first = SyntheticReturnGenerator(seed=11).generate_price_observations(5)
        second = SyntheticReturnGenerator(seed=11).generate_price_observations(5)
        assert SyntheticReturnGenerator.price_dataset_hash(first) == (
            SyntheticReturnGenerator.price_dataset_hash(second)
        )

    def test_price_stream_does_not_shift_unit_stream(self) -> None:
        """Generating prices does not change the unit stream."""
        generator = SyntheticReturnGenerator(seed=5)
        units_first = generator.generate(50)
        generator.generate_price_observations(3)
        units_second = generator.generate(50)
        assert SyntheticReturnGenerator.dataset_hash(units_first) == (
            SyntheticReturnGenerator.dataset_hash(units_second)
        )


class TestSyntheticTagging:
    """Every generated row must be flagged as synthetic."""

    def test_every_return_is_synthetic(self) -> None:
        """All rows carry ``is_synthetic = True``."""
        rows = SyntheticReturnGenerator(seed=1).generate(100)
        assert all(row.is_synthetic for row in rows)

    def test_every_price_observation_is_synthetic(self) -> None:
        """All price rows carry ``is_synthetic = True``."""
        rows = SyntheticReturnGenerator(seed=1).generate_price_observations(3)
        assert all(row.is_synthetic for row in rows)


class TestDistributions:
    """The generated data must stay inside the documented envelopes."""

    def test_battery_health_within_bounds(self) -> None:
        """Battery health stays inside the documented range."""
        rows = SyntheticReturnGenerator(seed=3).generate(500)
        assert all(55.0 <= row.battery_health_pct <= 100.0 for row in rows)

    def test_battery_cycles_within_bounds(self) -> None:
        """Cycle counts stay inside the documented range."""
        rows = SyntheticReturnGenerator(seed=3).generate(500)
        assert all(5 <= row.battery_cycles <= 1200 for row in rows)

    def test_cosmetic_grade_is_valid(self) -> None:
        """Only the four known grades are produced."""
        rows = SyntheticReturnGenerator(seed=3).generate(500)
        assert all(row.cosmetic_grade in GRADES for row in rows)

    def test_return_reason_is_known(self) -> None:
        """Only the documented return reasons are produced."""
        rows = SyntheticReturnGenerator(seed=3).generate(500)
        assert all(row.return_reason.isupper() for row in rows)

    def test_functional_tests_cover_the_full_suite(self) -> None:
        """Every functional test name is present on every row."""
        rows = SyntheticReturnGenerator(seed=3).generate(50)
        for row in rows:
            assert set(row.functional_tests) == set(FUNCTIONAL_TESTS)

    def test_accessory_presence_rate_is_plausible(self) -> None:
        """Accessory presence rates land near the documented probabilities."""
        rows = SyntheticReturnGenerator(seed=3).generate(4000)
        for accessory, expected in ACCESSORY_PRESENT_PROBABILITY.items():
            present = sum(1 for row in rows if row.accessories.get(accessory))
            rate = present / len(rows)
            assert abs(rate - expected) < 0.06, f"{accessory}: {rate} vs {expected}"

    def test_prices_are_non_negative(self) -> None:
        """No synthetic price is negative."""
        rows = SyntheticReturnGenerator(seed=3).generate_price_observations(20)
        assert all(row.price >= 0 for row in rows)

    def test_donate_channel_prices_are_zero(self) -> None:
        """The donate channel has no resale value."""
        rows = SyntheticReturnGenerator(seed=3).generate_price_observations(5)
        assert all(row.price == 0.0 for row in rows if row.channel == "DONATE")


class TestSerialUniqueness:
    """Generated serials must be unique."""

    def test_serials_are_unique(self) -> None:
        """No two generated units share a serial."""
        rows = SyntheticReturnGenerator(seed=9).generate(1000)
        serials = [row.serial for row in rows]
        assert len(set(serials)) == len(serials)


@settings(max_examples=10, deadline=None)
@given(
    seed=st.integers(min_value=0, max_value=10_000), count=st.integers(min_value=0, max_value=50)
)
def test_dataset_hash_is_stable_for_any_seed(seed: int, count: int) -> None:
    """The dataset hash is stable for any seed and count."""
    first = SyntheticReturnGenerator(seed=seed).generate(count)
    second = SyntheticReturnGenerator(seed=seed).generate(count)
    assert SyntheticReturnGenerator.dataset_hash(first) == (
        SyntheticReturnGenerator.dataset_hash(second)
    )
