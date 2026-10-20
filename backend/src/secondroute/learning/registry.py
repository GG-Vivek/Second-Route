"""
Model registry for Phase 6 (F6.1).

Uses MLflow to track each model version with training data hash, metrics,
calibration curve, and feature list. Every decision stores the model version.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, UTC
from typing import Any, Sequence
from uuid import UUID

import structlog
from pydantic import BaseModel, ConfigDict

logger = structlog.get_logger(__name__)

try:
    import mlflow
    from mlflow.tracking import MlflowClient
    from mlflow.entities import Run, RunStatus

    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    mlflow = None  # type: ignore
    MlflowClient = None  # type: ignore
    Run = None  # type: ignore
    RunStatus = None  # type: ignore


# Default model version for the decision engine
DEFAULT_MODEL_VERSION = "decision-v1"


@dataclass
class ModelVersionRecord:
    """Record of a model version tracked in the registry.

    Attributes:
        model_version: Unique version string (e.g., "decision-v1", "decision-v2").
        model_name: Name of the model (e.g., "decision-engine").
        training_data_hash: SHA-256 hash of the training data used.
        metrics: Dictionary of evaluation metrics (e.g., {"net_mae": 0.15, "ece": 0.05}).
        calibration_curve: List of (predicted, observed) points for the calibration curve.
        feature_list: List of feature names used by the model.
        created_at: Timestamp when the model was registered.
        is_active: Whether this model is the active one.
        mlflow_run_id: MLflow run ID for tracking.
    """

    model_version: str
    model_name: str
    training_data_hash: str
    metrics: dict[str, float] = field(default_factory=dict)
    calibration_curve: list[tuple[float, float]] = field(default_factory=list)
    feature_list: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    is_active: bool = False
    mlflow_run_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "model_version": self.model_version,
            "model_name": self.model_name,
            "training_data_hash": self.training_data_hash,
            "metrics": self.metrics,
            "calibration_curve": self.calibration_curve,
            "feature_list": self.feature_list,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
            "mlflow_run_id": self.mlflow_run_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelVersionRecord:
        """Create from dictionary."""
        return cls(
            model_version=data["model_version"],
            model_name=data["model_name"],
            training_data_hash=data["training_data_hash"],
            metrics=data.get("metrics", {}),
            calibration_curve=data.get("calibration_curve", []),
            feature_list=data.get("feature_list", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            is_active=data.get("is_active", False),
            mlflow_run_id=data.get("mlflow_run_id"),
        )


class ModelVersion(BaseModel):
    """Pydantic schema for model version information."""

    model_config = ConfigDict(from_attributes=True)

    model_version: str
    model_name: str
    training_data_hash: str
    metrics: dict[str, float] = {}
    calibration_curve: list[tuple[float, float]] = []
    feature_list: list[str] = []
    created_at: datetime
    is_active: bool = False
    mlflow_run_id: str | None = None


class ModelRegistry:
    """Registry for tracking model versions using MLflow.

    Falls back to an in-memory registry when MLflow is not available.
    """

    MODEL_NAME = "secondroute-decision-engine"

    def __init__(self, tracking_uri: str = "http://localhost:5000") -> None:
        self.tracking_uri = tracking_uri
        self._in_memory_registry: dict[str, ModelVersionRecord] = {}
        self._active_version: str | None = None
        self._mlflow_available = MLFLOW_AVAILABLE
        self._client: MlflowClient | None = None

        if self._mlflow_available:
            try:
                mlflow.set_tracking_uri(tracking_uri)
                self._client = MlflowClient(tracking_uri=tracking_uri)
            except Exception as e:
                logger.warning("MLflow not available, using in-memory registry: %s", e)
                self._mlflow_available = False
                self._client = None
        else:
            logger.info("MLflow not available, using in-memory registry")

    def register_model(  # noqa: PLR0913, PLR0917
        self,
        model_version: str,
        training_data_hash: str,
        metrics: dict[str, float] | None = None,
        calibration_curve: list[tuple[float, float]] | None = None,
        feature_list: list[str] | None = None,
        set_active: bool = False,
    ) -> ModelVersionRecord:
        """Register a new model version.

        Args:
            model_version: Unique version string.
            training_data_hash: SHA-256 hash of training data.
            metrics: Evaluation metrics.
            calibration_curve: Calibration curve points.
            feature_list: Feature names used.
            set_active: Whether to set this as the active version.

        Returns:
            The registered ModelVersionRecord.
        """
        metrics = metrics or {}
        calibration_curve = calibration_curve or []
        feature_list = feature_list or []

        mlflow_run_id = None

        if self._mlflow_available and self._client is not None:
            try:
                # Create an experiment if it doesn't exist
                experiment_name = "secondroute-model-registry"
                experiment = self._client.get_experiment_by_name(experiment_name)
                if experiment is None:
                    experiment_id = self._client.create_experiment(experiment_name)
                else:
                    experiment_id = experiment.experiment_id

                # Create a run for this model version
                run = self._client.create_run(
                    experiment_id=experiment_id,
                    tags={
                        "model_version": model_version,
                        "model_name": self.MODEL_NAME,
                        "training_data_hash": training_data_hash,
                    },
                )
                mlflow_run_id = run.info.run_id

                # Log metrics
                for metric_name, metric_value in metrics.items():
                    self._client.log_metric(run.info.run_id, metric_name, metric_value)

                # Log params (training data hash, feature list)
                self._client.log_param(run.info.run_id, "training_data_hash", training_data_hash)
                self._client.log_param(run.info.run_id, "feature_list", json.dumps(feature_list))

                # Log calibration curve as artifact
                calibration_data = {
                    "calibration_curve": calibration_curve,
                }
                import tempfile
                from pathlib import Path
                with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                    json.dump(calibration_data, f)
                    temp_path = f.name
                try:
                    self._client.log_artifact(run.info.run_id, temp_path, "calibration")
                finally:
                    Path(temp_path).unlink(missing_ok=True)

                # End the run
                self._client.set_terminated(run.info.run_id, status="FINISHED")
            except Exception as e:
                logger.warning("Failed to register model in MLflow: %s", e)
                mlflow_run_id = None

        record = ModelVersionRecord(
            model_version=model_version,
            model_name=self.MODEL_NAME,
            training_data_hash=training_data_hash,
            metrics=metrics,
            calibration_curve=calibration_curve,
            feature_list=feature_list,
            created_at=datetime.now(UTC),
            is_active=set_active,
            mlflow_run_id=mlflow_run_id,
        )

        # Store in in-memory registry
        self._in_memory_registry[model_version] = record

        # Set active version if requested
        if set_active:
            self.set_active_version(model_version)

        logger.info(
            "model_registered",
            model_version=model_version,
            training_data_hash=training_data_hash,
            metrics=metrics,
            mlflow_run_id=mlflow_run_id,
        )

        return record

    def get_model_version(self, model_version: str) -> ModelVersionRecord | None:
        """Get a model version record by version string.

        Args:
            model_version: Version string to look up.

        Returns:
            The ModelVersionRecord if found, None otherwise.
        """
        # Check in-memory registry first
        if model_version in self._in_memory_registry:
            return self._in_memory_registry[model_version]

        # Try MLflow
        if self._mlflow_available and self._client is not None:
            try:
                experiment = self._client.get_experiment_by_name("secondroute-model-registry")
                if experiment is None:
                    return None

                runs = self._client.search_runs(
                    experiment_ids=[experiment.experiment_id],
                    filter_string=f"tags.model_version = '{model_version}'",
                    max_results=1,
                )

                if not runs:
                    return None

                run = runs[0]
                return ModelVersionRecord(
                    model_version=run.data.tags.get("model_version", model_version),
                    model_name=run.data.tags.get("model_name", self.MODEL_NAME),
                    training_data_hash=run.data.tags.get("training_data_hash", ""),
                    metrics=run.data.metrics,
                    calibration_curve=[],
                    feature_list=json.loads(run.data.params.get("feature_list", "[]")),
                    created_at=run.info.start_time,
                    is_active=self._active_version == model_version,
                    mlflow_run_id=run.info.run_id,
                )
            except Exception as e:
                logger.warning("Failed to get model version from MLflow: %s", e)
                return None

        return None

    def list_model_versions(self) -> list[ModelVersionRecord]:
        """List all registered model versions.

        Returns:
            List of ModelVersionRecord objects.
        """
        # Return in-memory registry entries
        records = list(self._in_memory_registry.values())

        # Also try MLflow
        if self._mlflow_available and self._client is not None:
            try:
                experiment = self._client.get_experiment_by_name("secondroute-model-registry")
                if experiment is not None:
                    runs = self._client.search_runs(
                        experiment_ids=[experiment.experiment_id],
                        max_results=100,
                    )
                    for run in runs:
                        mv = run.data.tags.get("model_version")
                        if mv and mv not in [r.model_version for r in records]:
                            records.append(
                                ModelVersionRecord(
                                    model_version=mv,
                                    model_name=run.data.tags.get("model_name", self.MODEL_NAME),
                                    training_data_hash=run.data.tags.get("training_data_hash", ""),
                                    metrics=run.data.metrics,
                                    calibration_curve=[],
                                    feature_list=json.loads(run.data.params.get("feature_list", "[]")),
                                    created_at=run.info.start_time,
                                    is_active=self._active_version == mv,
                                    mlflow_run_id=run.info.run_id,
                                )
                            )
            except Exception as e:
                logger.warning("Failed to list model versions from MLflow: %s", e)

        return records

    def set_active_version(self, model_version: str) -> None:
        """Set the active model version.

        Args:
            model_version: Version string to set as active.
        """
        if model_version not in self._in_memory_registry and self.get_model_version(model_version) is None:
            raise ValueError(f"Model version {model_version} not found in registry")

        self._active_version = model_version

        # Update is_active flags
        for record in self._in_memory_registry.values():
            record.is_active = record.model_version == model_version

        logger.info("active_model_version_set", model_version=model_version)

    def get_active_version(self) -> str:
        """Get the active model version string.

        Returns:
            The active model version string, or DEFAULT_MODEL_VERSION if none set.
        """
        return self._active_version or DEFAULT_MODEL_VERSION

    def get_active_record(self) -> ModelVersionRecord | None:
        """Get the active model version record.

        Returns:
            The active ModelVersionRecord, or None if not found.
        """
        active = self.get_active_version()
        return self.get_model_version(active)


def compute_training_data_hash(data: Any) -> str:
    """Compute a SHA-256 hash of training data for registry purposes.

    Args:
        data: The training data (any JSON-serializable object).

    Returns:
        SHA-256 hash string.
    """
    try:
        serialized = json.dumps(data, sort_keys=True, default=str)
    except (TypeError, ValueError):
        serialized = str(data)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()