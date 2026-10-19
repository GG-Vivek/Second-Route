"""
Tests for configuration loading.
"""

import pytest
from pydantic import ValidationError

from secondroute.core.config import Settings


class TestSettings:
    """Tests for Settings model."""

    def test_default_settings(self) -> None:
        """Test that default settings load correctly."""
        settings = Settings(
            SECRET_KEY="test-secret-key-that-is-long-enough-for-validation",
            DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test",
            REDIS_URL="redis://localhost:6379/0",
        )

        assert settings.APP_NAME == "SecondRoute"
        assert settings.ENVIRONMENT == "development"
        assert settings.DEBUG is True
        assert settings.LOG_LEVEL == "DEBUG"
        assert settings.API_PREFIX == "/api/v1"
        assert settings.CONFIDENCE_THRESHOLD == 0.70
        assert settings.MONTE_CARLO_SAMPLES == 10_000
        assert settings.RNG_SEED == 42

    def test_risk_profile_lambdas(self) -> None:
        """Test risk profile lambda values."""
        settings = Settings(
            SECRET_KEY="test-secret-key-that-is-long-enough-for-validation",
            DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test",
            REDIS_URL="redis://localhost:6379/0",
        )

        assert settings.RISK_PROFILE_LAMBDA["conservative"] == 2.0
        assert settings.RISK_PROFILE_LAMBDA["balanced"] == 1.0
        assert settings.RISK_PROFILE_LAMBDA["aggressive"] == 0.5

    def test_is_production_property(self) -> None:
        """Test is_production computed field."""
        settings = Settings(
            SECRET_KEY="test-secret-key-that-is-long-enough-for-validation",
            DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test",
            REDIS_URL="redis://localhost:6379/0",
            ENVIRONMENT="development",
        )
        assert settings.is_production is False

        settings = Settings(
            SECRET_KEY="test-secret-key-that-is-long-enough-for-validation",
            DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test",
            REDIS_URL="redis://localhost:6379/0",
            ENVIRONMENT="production",
        )
        assert settings.is_production is True

    def test_database_url_sync_property(self) -> None:
        """Test database_url_sync computed field."""
        settings = Settings(
            SECRET_KEY="test-secret-key-that-is-long-enough-for-validation",
            DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test",
            REDIS_URL="redis://localhost:6379/0",
        )
        assert settings.database_url_sync == "postgresql://test:test@localhost:5432/test"

    def test_confidence_threshold_validation(self) -> None:
        """Test confidence threshold validation."""
        with pytest.raises(ValidationError):
            Settings(
                SECRET_KEY="test-secret-key-that-is-long-enough-for-validation",
                DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test",
                REDIS_URL="redis://localhost:6379/0",
                CONFIDENCE_THRESHOLD=1.5,  # > 1.0
            )

        with pytest.raises(ValidationError):
            Settings(
                SECRET_KEY="test-secret-key-that-is-long-enough-for-validation",
                DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test",
                REDIS_URL="redis://localhost:6379/0",
                CONFIDENCE_THRESHOLD=-0.1,  # < 0.0
            )

    def test_monte_carlo_samples_validation(self) -> None:
        """Test Monte Carlo samples validation."""
        with pytest.raises(ValidationError):
            Settings(
                SECRET_KEY="test-secret-key-that-is-long-enough-for-validation",
                DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test",
                REDIS_URL="redis://localhost:6379/0",
                MONTE_CARLO_SAMPLES=500,  # < 1000
            )

        with pytest.raises(ValidationError):
            Settings(
                SECRET_KEY="test-secret-key-that-is-long-enough-for-validation",
                DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test",
                REDIS_URL="redis://localhost:6379/0",
                MONTE_CARLO_SAMPLES=200_000,  # > 100_000
            )

    def test_secret_key_min_length(self) -> None:
        """Test secret key minimum length."""
        with pytest.raises(ValidationError):
            Settings(
                SECRET_KEY="short",  # Too short
                DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test",
                REDIS_URL="redis://localhost:6379/0",
            )
