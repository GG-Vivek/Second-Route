"""
Tests for the model registry (Phase 6 - F6.1).
"""

import pytest
from datetime import datetime, timezone, UTC
from uuid import uuid4

from secondroute.learning.registry import (
    ModelRegistry,
    ModelVersionRecord,
    compute_training_data_hash,
    DEFAULT_MODEL_VERSION,
)


class TestModelVersionRecord:
    """Tests for ModelVersionRecord dataclass."""

    def test_create_record(self) -> None:
        """Test creating a model version record."""
        record = ModelVersionRecord(
            model_version="decision-v1",
            model_name="secondroute-decision-engine",
            training_data_hash="abc123",
            metrics={"net_mae": 0.15, "ece": 0.05},
            calibration_curve=[(0.1, 0.15), (0.5, 0.52)],
            feature_list=["grade", "channel", "price"],
            is_active=True,
        )

        assert record.model_version == "decision-v1"
        assert record.training_data_hash == "abc123"
        assert record.metrics == {"net_mae": 0.15, "ece": 0.05}
        assert len(record.calibration_curve) == 2
        assert record.feature_list == ["grade", "channel", "price"]
        assert record.is_active is True

    def test_to_dict(self) -> None:
        """Test converting record to dict."""
        record = ModelVersionRecord(
            model_version="decision-v1",
            model_name="secondroute-decision-engine",
            training_data_hash="abc123",
        )

        d = record.to_dict()
        assert d["model_version"] == "decision-v1"
        assert d["training_data_hash"] == "abc123"
        assert "created_at" in d

    def test_from_dict(self) -> None:
        """Test creating record from dict."""
        data = {
            "model_version": "decision-v1",
            "model_name": "secondroute-decision-engine",
            "training_data_hash": "abc123",
            "metrics": {"net_mae": 0.15},
            "calibration_curve": [[0.1, 0.15]],
            "feature_list": ["grade"],
            "created_at": "2026-10-20T12:00:00+00:00",
            "is_active": True,
            "mlflow_run_id": None,
        }

        record = ModelVersionRecord.from_dict(data)
        assert record.model_version == "decision-v1"
        assert record.training_data_hash == "abc123"
        assert record.metrics == {"net_mae": 0.15}
        assert record.is_active is True


class TestModelRegistry:
    """Tests for ModelRegistry."""

    @pytest.fixture
    def registry(self) -> ModelRegistry:
        """Create an in-memory registry (MLflow not available)."""
        return ModelRegistry(tracking_uri="http://localhost:5000")

    def test_register_model(self, registry: ModelRegistry) -> None:
        """Test registering a new model version."""
        record = registry.register_model(
            model_version="decision-v1",
            training_data_hash="abc123",
            metrics={"net_mae": 0.15, "ece": 0.05},
            calibration_curve=[(0.1, 0.15), (0.5, 0.52)],
            feature_list=["grade", "channel", "price"],
            set_active=True,
        )

        assert record.model_version == "decision-v1"
        assert record.training_data_hash == "abc123"
        assert record.metrics == {"net_mae": 0.15, "ece": 0.05}
        assert record.is_active is True

    def test_get_model_version(self, registry: ModelRegistry) -> None:
        """Test getting a registered model version."""
        registry.register_model(
            model_version="decision-v1",
            training_data_hash="abc123",
        )

        record = registry.get_model_version("decision-v1")
        assert record is not None
        assert record.model_version == "decision-v1"
        assert record.training_data_hash == "abc123"

    def test_get_model_version_not_found(self, registry: ModelRegistry) -> None:
        """Test getting a non-existent model version."""
        record = registry.get_model_version("nonexistent")
        assert record is None

    def test_list_model_versions(self, registry: ModelRegistry) -> None:
        """Test listing all model versions."""
        registry.register_model(model_version="decision-v1", training_data_hash="hash1")
        registry.register_model(model_version="decision-v2", training_data_hash="hash2")

        versions = registry.list_model_versions()
        assert len(versions) == 2
        version_strings = [v.model_version for v in versions]
        assert "decision-v1" in version_strings
        assert "decision-v2" in version_strings

    def test_set_active_version(self, registry: ModelRegistry) -> None:
        """Test setting the active model version."""
        registry.register_model(model_version="decision-v1", training_data_hash="hash1")
        registry.register_model(model_version="decision-v2", training_data_hash="hash2")

        # Initially, no active version is set
        assert registry.get_active_version() == DEFAULT_MODEL_VERSION

        # Set decision-v2 as active
        registry.set_active_version("decision-v2")
        assert registry.get_active_version() == "decision-v2"

        # Check that is_active flags are updated
        record1 = registry.get_model_version("decision-v1")
        record2 = registry.get_model_version("decision-v2")
        assert record1 is not None and record1.is_active is False
        assert record2 is not None and record2.is_active is True

    def test_set_active_version_not_found(self, registry: ModelRegistry) -> None:
        """Test setting a non-existent version as active raises ValueError."""
        with pytest.raises(ValueError):
            registry.set_active_version("nonexistent")

    def test_get_active_record(self, registry: ModelRegistry) -> None:
        """Test getting the active model version record."""
        registry.register_model(
            model_version="decision-v1",
            training_data_hash="hash1",
            set_active=True,
        )

        record = registry.get_active_record()
        assert record is not None
        assert record.model_version == "decision-v1"
        assert record.is_active is True

    def test_get_active_record_no_active(self, registry: ModelRegistry) -> None:
        """Test getting active record when no active version is set."""
        registry.register_model(model_version="decision-v2", training_data_hash="hash1")

        # No active version set, and "decision-v2" is not the default
        # So get_active_version returns DEFAULT_MODEL_VERSION ("decision-v1")
        # which is not in the registry
        record = registry.get_active_record()
        assert record is None

    def test_register_with_mlflow_fallback(self, registry: ModelRegistry) -> None:
        """Test that registration works even when MLflow fails."""
        # MLflow might be available but fail to connect - registration should still work
        record = registry.register_model(
            model_version="decision-v1",
            training_data_hash="hash1",
        )
        assert record is not None
        assert record.model_version == "decision-v1"

    def test_register_duplicate_version(self, registry: ModelRegistry) -> None:
        """Test registering a duplicate version overwrites the previous one."""
        registry.register_model(model_version="decision-v1", training_data_hash="hash1")
        registry.register_model(model_version="decision-v1", training_data_hash="hash2")

        record = registry.get_model_version("decision-v1")
        assert record is not None
        assert record.training_data_hash == "hash2"


class TestComputeTrainingDataHash:
    """Tests for compute_training_data_hash function."""

    def test_hash_dict(self) -> None:
        """Test hashing a dictionary."""
        data = {"key": "value", "numbers": [1, 2, 3]}
        hash1 = compute_training_data_hash(data)
        hash2 = compute_training_data_hash(data)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256

    def test_hash_different_data(self) -> None:
        """Test that different data produces different hashes."""
        hash1 = compute_training_data_hash({"a": 1})
        hash2 = compute_training_data_hash({"a": 2})
        assert hash1 != hash2

    def test_hash_list(self) -> None:
        """Test hashing a list."""
        data = [1, 2, 3, "test"]
        hash1 = compute_training_data_hash(data)
        assert len(hash1) == 64

    def test_hash_none(self) -> None:
        """Test hashing None."""
        hash1 = compute_training_data_hash(None)
        assert len(hash1) == 64