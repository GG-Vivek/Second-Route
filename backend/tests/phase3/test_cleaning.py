"""
Tests for the price cleaning step (F3.3).
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC

import pytest

from secondroute.pricing.cleaning import (
    DEFAULT_HALF_LIFE_DAYS,
    CleanedObservations,
    PriceObservationRow,
    apply_recency_weights,
    clean_observations,
    effective_sample_size,
    normalize_grade,
    recency_weight,
    remove_outliers,
)

NOW = datetime(2025, 6, 1, tzinfo=UTC)


def make_row(
    value: float,
    age_days: float = 0.0,
    grade: str = "B",
    weight: float = 1.0,
) -> PriceObservationRow:
    """Build an observation row for a test."""
    return PriceObservationRow(
        value=value,
        observed_at=NOW - timedelta(days=age_days),
        grade=grade,
        weight=weight,
    )


class TestRecencyWeight:
    """The exponential decay."""

    def test_fresh_observation_has_weight_one(self) -> None:
        """An observation from now weighs 1."""
        assert recency_weight(timedelta(0)) == pytest.approx(1.0)

    def test_one_half_life_halves_the_weight(self) -> None:
        """At the half-life the weight is 0.5."""
        assert recency_weight(timedelta(days=30)) == pytest.approx(0.5)

    def test_sixty_day_old_observation_is_about_a_quarter(self) -> None:
        """The acceptance criterion: 60 days at a 30 day half-life is a quarter."""
        weight = recency_weight(timedelta(days=60), half_life_days=30)
        assert weight == pytest.approx(0.25, rel=0.01)

    def test_weight_accepts_days_as_a_number(self) -> None:
        """A plain number of days works too."""
        assert recency_weight(60.0, half_life_days=30) == pytest.approx(0.25)

    def test_weight_decays_monotonically(self) -> None:
        """Older is always lighter."""
        weights = [recency_weight(timedelta(days=d)) for d in range(0, 120, 10)]
        assert weights == sorted(weights, reverse=True)

    def test_configurable_half_life(self) -> None:
        """The half-life is configurable."""
        assert recency_weight(timedelta(days=14), half_life_days=7) == pytest.approx(0.25)

    def test_default_half_life_is_thirty_days(self) -> None:
        """The default half-life is 30 days."""
        assert DEFAULT_HALF_LIFE_DAYS == 30

    def test_zero_half_life_is_rejected(self) -> None:
        """A non-positive half-life is an error."""
        with pytest.raises(ValueError, match="half_life_days"):
            recency_weight(timedelta(days=1), half_life_days=0)


class TestOutlierRemoval:
    """MAD-based outlier removal."""

    def test_injected_outlier_is_removed(self) -> None:
        """The acceptance criterion: an injected outlier is removed."""
        values = [100.0, 102.0, 101.0, 99.0, 103.0, 100000.0]
        kept, removed = remove_outliers(values)
        assert 100000.0 not in kept
        assert removed == 1
        assert len(kept) == 5

    def test_clean_data_is_untouched(self) -> None:
        """Ordinary variation is not treated as an outlier."""
        values = [100.0, 102.0, 101.0, 99.0, 103.0, 100.5]
        kept, removed = remove_outliers(values)
        assert removed == 0
        assert kept == tuple(values)

    def test_several_outliers_are_removed(self) -> None:
        """More than one outlier is caught."""
        values = [100.0, 101.0, 99.0, 100.5, 50000.0, -40000.0]
        kept, removed = remove_outliers(values)
        assert removed == 2
        assert 50000.0 not in kept
        assert -40000.0 not in kept

    def test_small_samples_are_kept(self) -> None:
        """Too few points to judge, so nothing is removed."""
        values = [100.0, 100000.0]
        kept, removed = remove_outliers(values)
        assert removed == 0
        assert kept == tuple(values)

    def test_identical_values_are_kept(self) -> None:
        """When every value is the same, nothing can be an outlier."""
        values = [50.0] * 10
        kept, removed = remove_outliers(values)
        assert removed == 0
        assert kept == tuple(values)

    def test_threshold_must_be_positive(self) -> None:
        """A non-positive threshold is an error."""
        with pytest.raises(ValueError, match="threshold"):
            remove_outliers([1.0, 2.0, 3.0], threshold=0)

    def test_outlier_removal_is_robust_to_the_outlier(self) -> None:
        """A standard deviation filter would fail this; the MAD does not."""
        values = [100.0, 101.0, 102.0, 99.0, 98.0, 100.0, 50000.0]
        kept, removed = remove_outliers(values)
        assert removed == 1
        assert max(kept) < 200.0


class TestGradeNormalization:
    """Every source names its grades differently."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("A", "A"),
            ("a", "A"),
            ("B+", "B"),
            ("Grade C", "C"),
            ("New", "A"),
            ("New other", "A"),
            ("New with defects", "B"),
            ("Manufacturer refurbished", "A"),
            ("Seller refurbished", "B"),
            ("Used", "C"),
            ("Very Good", "B"),
            ("Good", "C"),
            ("Acceptable", "D"),
            ("For parts or not working", "D"),
            ("  very good  ", "B"),
            ("1000", "A"),
            ("7000", "D"),
        ],
    )
    def test_known_labels_normalize(self, raw: str, expected: str) -> None:
        """Known labels map to the canonical grade."""
        assert normalize_grade(raw) == expected

    def test_unknown_label_returns_none(self) -> None:
        """An unrecognised label is not forced into a bucket."""
        assert normalize_grade("quantum") is None

    def test_empty_label_returns_none(self) -> None:
        """An empty label is not a grade."""
        assert normalize_grade("") is None
        assert normalize_grade("   ") is None
        assert normalize_grade(None) is None


class TestCleanObservations:
    """The full cleaning step."""

    def test_outliers_are_removed_and_counts_reported(self) -> None:
        """The summary reports what was removed."""
        rows = [make_row(100.0), make_row(101.0), make_row(99.0), make_row(100000.0)]
        cleaned = clean_observations(rows, now=NOW)
        assert cleaned.removed == 1
        assert cleaned.total == 4
        assert cleaned.count == 3
        assert not cleaned.is_empty

    def test_weights_reflect_recency(self) -> None:
        """A fresh observation weighs more than an old one."""
        rows = [make_row(100.0, age_days=0), make_row(100.0, age_days=60)]
        cleaned = clean_observations(rows, now=NOW)
        assert cleaned.weights[0] == pytest.approx(1.0)
        assert cleaned.weights[1] == pytest.approx(0.25, rel=0.02)

    def test_grades_are_normalized(self) -> None:
        """The grades come back canonical."""
        rows = [make_row(100.0, grade="Very Good"), make_row(101.0, grade="B+")]
        cleaned = clean_observations(rows, now=NOW)
        assert cleaned.grades == ("B", "B")

    def test_unrecognised_grade_falls_back(self) -> None:
        """An unrecognised grade does not break the cleaning."""
        rows = [make_row(100.0, grade="???"), make_row(101.0, grade="B")]
        cleaned = clean_observations(rows, now=NOW)
        assert len(cleaned.grades) == 2

    def test_empty_input(self) -> None:
        """Cleaning nothing gives nothing."""
        cleaned = clean_observations([], now=NOW)
        assert cleaned.is_empty
        assert cleaned.total == 0
        assert cleaned.removed == 0

    def test_source_weight_is_preserved(self) -> None:
        """The source's own weight multiplies the recency weight."""
        rows = [make_row(100.0, age_days=0, weight=2.0)]
        cleaned = clean_observations(rows, now=NOW)
        assert cleaned.weights[0] == pytest.approx(2.0)

    def test_invalid_parameters_are_rejected(self) -> None:
        """Bad parameters are errors."""
        with pytest.raises(ValueError, match="half_life_days"):
            clean_observations([make_row(1.0)], now=NOW, half_life_days=0)
        with pytest.raises(ValueError, match="mad_threshold"):
            clean_observations([make_row(1.0)], now=NOW, mad_threshold=0)

    def test_weights_line_up_with_values(self) -> None:
        """Every value keeps its weight."""
        rows = [make_row(100.0, age_days=0), make_row(101.0, age_days=10)]
        cleaned = clean_observations(rows, now=NOW)
        assert len(cleaned.values) == len(cleaned.weights)
        assert all(weight > 0 for weight in cleaned.weights)


class TestApplyRecencyWeights:
    """The weighting step on its own."""

    def test_weights_are_applied(self) -> None:
        """The values come back with their weights."""
        rows = [make_row(100.0, age_days=0), make_row(101.0, age_days=30)]
        values, weights = apply_recency_weights(rows, now=NOW)
        assert values == (100.0, 101.0)
        assert weights[0] == pytest.approx(1.0)
        assert weights[1] == pytest.approx(0.5)


class TestEffectiveSampleSize:
    """The effective sample size of a weighted set."""

    def test_equal_weights_give_the_count(self) -> None:
        """With equal weights the effective size is the count."""
        assert effective_sample_size([1.0, 1.0, 1.0, 1.0]) == pytest.approx(4.0)

    def test_unequal_weights_reduce_the_size(self) -> None:
        """Concentrated weight means less information."""
        assert effective_sample_size([1.0, 0.0, 0.0, 0.0]) == pytest.approx(1.0)

    def test_empty_weights(self) -> None:
        """No weights means no information."""
        assert effective_sample_size([]) == 0.0
