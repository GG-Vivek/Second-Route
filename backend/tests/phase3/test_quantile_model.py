"""
Tests for the price quantile model (F3.4).
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from uuid import UUID, uuid4

import numpy as np
import pytest

from secondroute.pricing.quantile import (
    DEFAULT_MIN_SAMPLES,
    QUANTILES,
    QuantilePriceModel,
    QuantilePriceSource,
    SkuFeatures,
    TrainingRow,
    pinball_loss,
)

NOW = datetime(2025, 6, 1, tzinfo=UTC)


def make_rows(
    count: int,
    *,
    family: str = "MacBook Pro",
    grade: str = "B",
    base_price: float = 1200.0,
    spread: float = 60.0,
    seed: int = 1,
) -> list[TrainingRow]:
    """Build training rows for a cell."""
    rng = np.random.default_rng(seed)
    rows: list[TrainingRow] = []
    for index in range(count):
        price = base_price + float(rng.normal(0.0, spread))
        rows.append(
            TrainingRow(
                features=SkuFeatures(
                    family=family,
                    grade=grade,
                    year=2023,
                    storage_gb=512.0,
                    ram_gb=18.0,
                    age_days=float(index % 30),
                    source="partner_a",
                ),
                price=price,
                weight=1.0,
            )
        )
    return rows


class TestPinballLoss:
    """The loss the model is judged on."""

    def test_perfect_prediction_has_no_loss(self) -> None:
        """Predicting exactly gives zero loss."""
        y = np.array([1.0, 2.0, 3.0])
        assert pinball_loss(y, y, 0.5) == pytest.approx(0.0)

    def test_median_loss_is_half_the_absolute_error(self) -> None:
        """At the median quantile the loss is half the absolute error."""
        y = np.array([10.0, 20.0])
        p = np.array([12.0, 18.0])
        # The absolute error is 2 on each row, so the loss is 1 on each row.
        assert pinball_loss(y, p, 0.5) == pytest.approx(1.0)

    def test_empty_input(self) -> None:
        """No data means no loss."""
        assert np.isnan(pinball_loss(np.array([]), np.array([]), 0.5))

    def test_loss_grows_with_the_error(self) -> None:
        """A worse prediction scores worse."""
        y = np.array([100.0])
        close = pinball_loss(y, np.array([95.0]), 0.5)
        far = pinball_loss(y, np.array([50.0]), 0.5)
        assert far > close


class TestFitting:
    """The model fits and reports its loss."""

    def test_fit_returns_metrics_with_pinball_loss(self) -> None:
        """The acceptance criterion: the pinball loss is recorded."""
        model = QuantilePriceModel(model_version="quantile-test")
        metrics = model.fit(make_rows(120))

        assert metrics.model_version == "quantile-test"
        assert metrics.training_rows == 120
        assert set(metrics.pinball_loss) == set(QUANTILES)
        assert all(v >= 0 for v in metrics.pinball_loss.values())

    def test_fit_logs_the_model_version(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The pinball loss is logged with the model version."""
        import secondroute.pricing.quantile as quantile_module

        calls: list[tuple[str, dict]] = []
        monkeypatch.setattr(
            quantile_module.logger,
            "info",
            lambda event, **kwargs: calls.append((event, kwargs)),
        )

        model = QuantilePriceModel(model_version="quantile-logged")
        model.fit(make_rows(80))

        assert calls
        event, kwargs = calls[0]
        assert event == "quantile_model_fitted"
        assert kwargs["model_version"] == "quantile-logged"
        assert set(kwargs["pinball_loss"]) == {str(q) for q in QUANTILES}

    def test_fit_records_the_cell_counts(self) -> None:
        """The model knows how much data each cell has."""
        model = QuantilePriceModel()
        model.fit(make_rows(40, family="MacBook Pro", grade="A"))
        assert model.sample_count("MacBook Pro", "A") == 40
        assert model.sample_count("MacBook Pro", "B") == 0

    def test_fit_with_no_rows_is_rejected(self) -> None:
        """A model needs data."""
        model = QuantilePriceModel()
        with pytest.raises(ValueError, match="no observations"):
            model.fit([])

    def test_predict_before_fit_is_rejected(self) -> None:
        """An unfitted model cannot predict."""
        model = QuantilePriceModel()
        with pytest.raises(ValueError, match="not been fitted"):
            model.predict(SkuFeatures(family="MacBook Pro", grade="B"))

    def test_predict_returns_every_quantile(self) -> None:
        """The prediction covers p10, p50 and p90."""
        model = QuantilePriceModel()
        model.fit(make_rows(120))
        prediction = model.predict(
            SkuFeatures(family="MacBook Pro", grade="B", year=2023, storage_gb=512.0)
        )
        assert set(prediction) == set(QUANTILES)
        assert prediction[0.1] < prediction[0.5] < prediction[0.9]

    def test_model_is_marked_as_fitted(self) -> None:
        """The fitted flag works."""
        model = QuantilePriceModel()
        assert model.is_fitted is False
        model.fit(make_rows(40))
        assert model.is_fitted is True


class TestSampleThreshold:
    """The fallback threshold."""

    def test_default_minimum_is_thirty(self) -> None:
        """The default minimum sample count is 30."""
        assert DEFAULT_MIN_SAMPLES == 30

    def test_below_the_threshold_the_model_is_not_used(self) -> None:
        """The acceptance criterion: the fallback triggers below the sample."""
        model = QuantilePriceModel(min_samples=30)
        model.fit(make_rows(20, grade="B"))
        assert model.has_enough_data("MacBook Pro", "B") is False

    def test_at_the_threshold_the_model_is_used(self) -> None:
        """At the threshold the model is used."""
        model = QuantilePriceModel(min_samples=30)
        model.fit(make_rows(30, grade="B"))
        assert model.has_enough_data("MacBook Pro", "B") is True

    def test_above_the_threshold_the_model_is_used(self) -> None:
        """Above the threshold the model is used."""
        model = QuantilePriceModel(min_samples=30)
        model.fit(make_rows(45, grade="B"))
        assert model.has_enough_data("MacBook Pro", "B") is True


class TestQuantilePriceSource:
    """The source that uses the model."""

    def _source(
        self, count: int, *, min_samples: int = 30, seed: int = 3
    ) -> tuple[QuantilePriceSource, UUID]:
        """Build a source over a single cell."""
        rows = make_rows(count, seed=seed)
        model = QuantilePriceModel(min_samples=min_samples)
        model.fit(rows)

        observations: dict[tuple[str, str, str], list[tuple[float, float, datetime]]] = {
            ("MacBook Pro", "B", "RESELL_OPEN_BOX"): [
                (row.price, row.weight, NOW - timedelta(days=row.features.age_days)) for row in rows
            ]
        }
        sku_id = uuid4()
        features = SkuFeatures(
            family="MacBook Pro",
            grade="B",
            year=2023,
            storage_gb=512.0,
            ram_gb=18.0,
            source="partner_a",
        )
        source = QuantilePriceSource(model, observations, {sku_id: features})
        return source, sku_id

    @pytest.mark.asyncio
    async def test_model_is_used_when_there_is_enough_data(self) -> None:
        """Above the threshold the prediction comes from the model."""
        source, sku_id = self._source(60)
        distribution = await source.get_distribution(sku_id, "B", "RESELL_OPEN_BOX", NOW)
        assert "quantile-v1" in distribution.source or "quantile" in distribution.source
        assert distribution.metadata["fallback"] == "model"

    @pytest.mark.asyncio
    async def test_fallback_is_used_below_the_threshold(self) -> None:
        """The acceptance criterion: below the threshold the empirical values win."""
        source, sku_id = self._source(10)
        distribution = await source.get_distribution(sku_id, "B", "RESELL_OPEN_BOX", NOW)
        assert distribution.metadata["fallback"] == "empirical"
        assert "empirical" in distribution.source

    @pytest.mark.asyncio
    async def test_fallback_quantiles_match_the_observations(self) -> None:
        """The empirical fallback reports the observed quantiles."""
        rows = make_rows(15, seed=5)
        prices = [row.price for row in rows]

        model = QuantilePriceModel(min_samples=30)
        model.fit(rows)
        observations = {
            ("MacBook Pro", "B", "RESELL_OPEN_BOX"): [(row.price, 1.0, NOW) for row in rows]
        }
        sku_id = uuid4()
        source = QuantilePriceSource(model, observations, {sku_id: SkuFeatures("MacBook Pro", "B")})

        distribution = await source.get_distribution(sku_id, "B", "RESELL_OPEN_BOX", NOW)
        assert distribution.quantile(0.1) == pytest.approx(
            float(np.quantile(prices, 0.1)), rel=0.02
        )
        assert distribution.quantile(0.5) == pytest.approx(
            float(np.quantile(prices, 0.5)), rel=0.02
        )

    @pytest.mark.asyncio
    async def test_unknown_cell_raises(self) -> None:
        """A cell with no data is an error, not a guess."""
        source, sku_id = self._source(30)
        with pytest.raises(Exception, match="No price observations"):
            await source.get_distribution(sku_id, "Z", "RESELL_OPEN_BOX", NOW)
