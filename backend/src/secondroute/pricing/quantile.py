"""
Price quantile model (Phase 3 - F3.4).

A quantile regression over the observed prices, so the engine can ask "what
is the 10th percentile for this SKU?" even for a cell it has never seen.

LightGBM is used for the regression, with one model per quantile. When a
(family, grade) cell has fewer observations than the configured minimum, the
model is **not** trusted: the empirical quantiles of that cell are used
instead. A model fitted on twenty observations is worse than no model at all,
and the whole point of the confidence gate is that thin data has to look
thin.

The pinball loss of every quantile is recorded per model version, so a model
can be compared with the one it replaced.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Final
from uuid import UUID

import numpy as np
from numpy.typing import NDArray

from secondroute.core.logging import get_logger
from secondroute.pricing.protocols import PriceDistribution, PriceSourceNotFoundError

logger = get_logger(__name__)

__all__ = [
    "DEFAULT_MIN_SAMPLES",
    "QUANTILES",
    "ModelMetrics",
    "QuantilePriceModel",
    "QuantilePriceSource",
    "SkuFeatures",
    "TrainingRow",
    "pinball_loss",
]

#: The quantiles the engine needs.
QUANTILES: Final[tuple[float, ...]] = (0.1, 0.5, 0.9)

#: Below this many observations in a cell, the empirical quantiles are used
#: instead of the model.
DEFAULT_MIN_SAMPLES: Final[int] = 30

#: Weights used to turn three quantiles back into a distribution.
QUANTILE_WEIGHTS: Final[tuple[float, ...]] = (0.25, 0.5, 0.25)


@dataclass(frozen=True, slots=True)
class SkuFeatures:
    """The features the model predicts from.

    Attributes:
        family: The SKU family.
        grade: The condition grade.
        year: The model year.
        storage_gb: Storage in gigabytes.
        ram_gb: Memory in gigabytes.
        age_days: How long the observation is (0 for a fresh prediction).
        source: The source tag, encoded.
    """

    family: str
    grade: str
    year: int = 0
    storage_gb: float = 0.0
    ram_gb: float = 0.0
    age_days: float = 0.0
    source: str = ""


@dataclass(frozen=True, slots=True)
class TrainingRow:
    """One observation the model learns from.

    Attributes:
        features: The features of the observation.
        price: The observed price.
        weight: How much the observation counts.
    """

    features: SkuFeatures
    price: float
    weight: float = 1.0


def pinball_loss(y_true: NDArray[np.float64], y_pred: NDArray[np.float64], alpha: float) -> float:
    """Return the pinball (quantile) loss of a prediction.

    Args:
        y_true: The actual values.
        y_pred: The predicted values.
        alpha: The quantile being predicted.

    Returns:
        The mean pinball loss. Lower is better.
    """
    if y_true.size == 0:
        return float("nan")
    diff = y_true - y_pred
    loss = np.maximum(alpha * diff, (alpha - 1) * diff)
    return float(np.average(loss, weights=np.ones_like(loss)))


@dataclass(slots=True)
class ModelMetrics:
    """How a fitted model did.

    Attributes:
        model_version: The version of the model.
        training_rows: How many observations it was fitted on.
        cells: The (family, grade) cells it covers.
        pinball_loss: The pinball loss per quantile.
        empirical_mae: The mean absolute error of the median prediction.
        fitted_at: When it was fitted.
    """

    model_version: str
    training_rows: int
    cells: int
    pinball_loss: dict[float, float] = field(default_factory=dict)
    empirical_mae: float = 0.0
    fitted_at: datetime = field(default_factory=datetime.utcnow)

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of the metrics."""
        return {
            "model_version": self.model_version,
            "training_rows": self.training_rows,
            "cells": self.cells,
            "pinball_loss": {str(q): v for q, v in self.pinball_loss.items()},
            "empirical_mae": self.empirical_mae,
            "fitted_at": self.fitted_at.isoformat(),
        }


class QuantilePriceModel:
    """LightGBM quantile regression over observed prices.

    Attributes:
        model_version: The version stamped on the fitted model.
        min_samples: Below this many observations in a cell, the model is not
            used.
    """

    def __init__(
        self,
        model_version: str = "quantile-v1",
        min_samples: int = DEFAULT_MIN_SAMPLES,
    ) -> None:
        self.model_version = model_version
        self.min_samples = min_samples
        self._models: dict[float, Any] = {}
        self._vocabulary: dict[str, int] = {}
        self._cell_counts: dict[tuple[str, str], int] = {}
        self._metrics: ModelMetrics | None = None

    # ------------------------------------------------------------------
    # Fitting
    # ------------------------------------------------------------------

    def fit(self, rows: Sequence[TrainingRow]) -> ModelMetrics:
        """Fit one model per quantile.

        Args:
            rows: The observations to learn from.

        Returns:
            The metrics of the fitted model, with the pinball loss of every
            quantile.

        Raises:
            ValueError: If there are no rows to learn from.
        """
        if not rows:
            raise ValueError("cannot fit a quantile model with no observations")

        import lightgbm as lgb

        self._vocabulary = self._build_vocabulary(rows)
        self._cell_counts = self._count_cells(rows)

        features = np.array([self._vector(row.features) for row in rows], dtype=np.float64)
        targets = np.array([row.price for row in rows], dtype=np.float64)
        weights = np.array([row.weight for row in rows], dtype=np.float64)

        dataset = lgb.Dataset(
            features,
            label=targets,
            weight=weights,
            free_raw_data=False,
        )

        metrics = ModelMetrics(
            model_version=self.model_version,
            training_rows=len(rows),
            cells=len(self._cell_counts),
        )

        for quantile in QUANTILES:
            params = {
                "objective": "quantile",
                "alpha": quantile,
                "num_leaves": 15,
                "learning_rate": 0.05,
                "min_data_in_leaf": 10,
                "verbosity": -1,
                "seed": 42,
                "deterministic": True,
                "num_threads": 1,
            }
            model = lgb.train(params, dataset, num_boost_round=200)
            self._models[quantile] = model

            predictions = np.asarray(model.predict(features), dtype=np.float64)
            metrics.pinball_loss[quantile] = pinball_loss(targets, predictions, quantile)

        median_predictions = np.asarray(self._models[0.5].predict(features), dtype=np.float64)
        metrics.empirical_mae = float(np.mean(np.abs(targets - median_predictions)))
        self._metrics = metrics

        logger.info(
            "quantile_model_fitted",
            model_version=self.model_version,
            training_rows=metrics.training_rows,
            cells=metrics.cells,
            pinball_loss={str(q): round(v, 4) for q, v in metrics.pinball_loss.items()},
            empirical_mae=round(metrics.empirical_mae, 4),
        )
        return metrics

    @property
    def metrics(self) -> ModelMetrics | None:
        """The metrics of the fitted model."""
        return self._metrics

    @property
    def is_fitted(self) -> bool:
        """Whether the model has been fitted."""
        return bool(self._models)

    def sample_count(self, family: str, grade: str) -> int:
        """How many observations the model saw for a cell.

        Args:
            family: The SKU family.
            grade: The grade.

        Returns:
            The observation count.
        """
        return self._cell_counts.get((family, grade), 0)

    def has_enough_data(self, family: str, grade: str) -> bool:
        """Whether the model may be used for a cell.

        Args:
            family: The SKU family.
            grade: The grade.

        Returns:
            True when the cell has at least ``min_samples`` observations.
        """
        return self.sample_count(family, grade) >= self.min_samples

    # ------------------------------------------------------------------
    # Predicting
    # ------------------------------------------------------------------

    def predict(self, features: SkuFeatures) -> dict[float, float]:
        """Predict the quantiles for one SKU.

        Args:
            features: The features to predict from.

        Returns:
            The predicted value for each quantile.

        Raises:
            ValueError: If the model has not been fitted.
        """
        if not self._models:
            raise ValueError("the quantile model has not been fitted")

        vector = np.array([self._vector(features)], dtype=np.float64)
        return {
            quantile: float(model.predict(vector)[0]) for quantile, model in self._models.items()
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_vocabulary(self, rows: Sequence[TrainingRow]) -> dict[str, int]:
        """Map the categorical values onto integers."""
        families = sorted({row.features.family for row in rows})
        grades = sorted({row.features.grade for row in rows})
        sources = sorted({row.features.source for row in rows})
        vocabulary: dict[str, int] = {}
        for index, value in enumerate(families):
            vocabulary[f"family:{value}"] = index
        for index, value in enumerate(grades):
            vocabulary[f"grade:{value}"] = index
        for index, value in enumerate(sources):
            vocabulary[f"source:{value}"] = index
        return vocabulary

    def _count_cells(self, rows: Sequence[TrainingRow]) -> dict[tuple[str, str], int]:
        """Count the observations per (family, grade) cell."""
        counts: dict[tuple[str, str], int] = {}
        for row in rows:
            key = (row.features.family, row.features.grade)
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _vector(self, features: SkuFeatures) -> list[float]:
        """Turn the features into a numeric vector."""
        vocabulary = self._vocabulary
        return [
            float(vocabulary.get(f"family:{features.family}", 0)),
            float(vocabulary.get(f"grade:{features.grade}", 0)),
            float(vocabulary.get(f"source:{features.source}", 0)),
            float(features.year),
            float(features.storage_gb),
            float(features.ram_gb),
            float(features.age_days),
            math.log1p(max(features.storage_gb, 0.0)),
            math.log1p(max(features.ram_gb, 0.0)),
        ]


class QuantilePriceSource:
    """A price source backed by the quantile model.

    When the model has enough data for the cell, the prediction is used. When
    it does not, the empirical quantiles of the cell are used instead.

    Attributes:
        source_tag: The source tag recorded on the observations.
    """

    source_tag = "quantile_model"

    def __init__(
        self,
        model: QuantilePriceModel,
        observations: dict[tuple[str, str, str], list[tuple[float, float, datetime]]],
        sku_features: dict[UUID, SkuFeatures] | None = None,
    ) -> None:
        """Build the source.

        Args:
            model: The fitted quantile model.
            observations: Observations keyed by ``(family, grade, channel)``.
                Each entry is a list of ``(price, weight, observed_at)``.
            sku_features: The features of each SKU, so the model knows what to
                predict for.
        """
        self.model = model
        self.observations = observations
        self.sku_features = sku_features or {}

    async def get_distribution(
        self,
        sku_id: UUID,
        grade: str,
        channel: str,
        as_of: datetime,
    ) -> PriceDistribution:
        """Return the price distribution for one cell.

        Args:
            sku_id: The SKU the price applies to.
            grade: The condition grade.
            channel: The disposition channel.
            as_of: Only observations at or before this timestamp are used.

        Returns:
            The distribution for the requested cell.

        Raises:
            PriceSourceNotFoundError: If the cell has no usable data.
        """
        features = self.sku_features.get(sku_id)
        family = features.family if features else "unknown"

        cell = (family, grade, channel)
        rows = self.observations.get(cell, [])

        if not rows:
            raise PriceSourceNotFoundError(
                f"No price observations for family={family} grade={grade} channel={channel}"
            )

        if self.model.is_fitted and self.model.has_enough_data(family, grade):
            prediction = self.model.predict(
                features if features else SkuFeatures(family=family, grade=grade)
            )
            values = tuple(round(prediction[q], 2) for q in QUANTILES)
            weights = QUANTILE_WEIGHTS
            source = f"{self.source_tag}:{self.model.model_version}"
        else:
            # Not enough data for the model: use the observed prices directly.
            prices = [price for price, _, _ in rows]
            observed_weights = [weight for _, weight, _ in rows]
            values = tuple(round(price, 2) for price in prices)
            weights = tuple(observed_weights)
            source = f"{self.source_tag}:empirical"

        latest = max(observed_at for _, _, observed_at in rows)

        return PriceDistribution(
            values=values,
            weights=weights,
            source=source,
            as_of=min(latest, as_of) if latest > as_of else latest,
            metadata={
                "family": family,
                "fallback": "empirical" if not self._uses_model(family, grade) else "model",
                "sample_count": str(len(rows)),
            },
        )

    def _uses_model(self, family: str, grade: str) -> bool:
        """Whether the model is used for a cell."""
        return self.model.is_fitted and self.model.has_enough_data(family, grade)

    @staticmethod
    def _weighted_quantile(rows: Sequence[tuple[float, float, datetime]], q: float) -> float:
        """Compute a weighted quantile of the observations."""
        ordered = sorted(rows, key=lambda row: row[0])
        total = sum(weight for _, weight, _ in ordered)
        if total <= 0:
            prices = [price for price, _, _ in ordered]
            return float(np.quantile(prices, q))

        cumulative = 0.0
        for price, weight, _ in ordered:
            cumulative += weight
            if cumulative / total >= q:
                return price
        return ordered[-1][0]
