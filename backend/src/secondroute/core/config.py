"""
Configuration management for SecondRoute.

Uses Pydantic Settings for type-safe environment variable handling.
All configuration is loaded from environment variables with sensible defaults.
"""

from functools import lru_cache
from typing import Any

from pydantic import Field, computed_field
from pydantic.networks import PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "SecondRoute"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"

    # API
    API_PREFIX: str = "/api/v1"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://secondroute:changeme@localhost:5432/secondroute",
        description="PostgreSQL async connection URL",
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    REDIS_MAX_CONNECTIONS: int = 50

    # Security
    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production-min-32-chars",
        min_length=32,
        description="Secret key for signing tokens",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # CORS
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="Allowed CORS origins",
    )

    # File Storage
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_IMAGE_TYPES: list[str] = Field(
        default=["image/jpeg", "image/png", "image/webp"],
        description="Allowed MIME types for image uploads",
    )

    # Pricing / Decision Engine
    CONFIDENCE_THRESHOLD: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description="Minimum confidence to recommend a channel (else SAFE_DEFAULT)",
    )
    MONTE_CARLO_SAMPLES: int = Field(
        default=10_000,
        ge=1000,
        le=100_000,
        description="Number of Monte Carlo samples for channel evaluation",
    )
    RNG_SEED: int = Field(
        default=42,
        description="Seed for reproducible stochastic operations",
    )

    # Risk Profiles (certainty equivalent lambda)
    RISK_PROFILE_LAMBDA: dict[str, float] = Field(
        default={"conservative": 2.0, "balanced": 1.0, "aggressive": 0.5},
        description="Risk aversion parameter per profile",
    )
    DEFAULT_RISK_PROFILE: str = "balanced"

    # Price Data
    PRICE_RECENCY_HALF_LIFE_DAYS: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Half-life for exponential recency weighting",
    )
    MIN_PRICE_OBSERVATIONS: int = Field(
        default=30,
        ge=5,
        description="Minimum observations before using ML model vs empirical quantiles",
    )

    # Source Health
    SOURCE_STALENESS_HOURS: int = Field(
        default=48,
        ge=1,
        description="Hours after which a price source is considered stale",
    )
    CONFIDENCE_DEGRADATION_FACTOR: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Factor to multiply confidence when source is stale",
    )

    # External APIs
    EBAY_APP_ID: str | None = Field(default=None, description="eBay Browse API App ID")
    EBAY_CERT_ID: str | None = Field(default=None, description="eBay Browse API Cert ID")
    EBAY_DEV_ID: str | None = Field(default=None, description="eBay Browse API Dev ID")
    EBAY_SANDBOX: bool = True

    FRED_API_KEY: str | None = Field(default=None, description="FRED API Key")

    # MLflow
    MLFLOW_TRACKING_URI: str = Field(
        default="http://localhost:5000",
        description="MLflow tracking server URI",
    )
    MLFLOW_EXPERIMENT_NAME: str = "secondroute-pricing"

    # Ollama (for explanation text)
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL",
    )
    OLLAMA_MODEL: str = Field(
        default="llama3.1:8b",
        description="Ollama model for explanation generation",
    )

    # Monitoring
    PROMETHEUS_METRICS_PORT: int = 9090
    GRAFANA_URL: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic."""
        url = str(self.DATABASE_URL)
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://")
        return url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
