"""
Tests for the health check endpoint.
"""

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_returns_200(self, client: AsyncClient) -> None:
        """Test that health check returns 200 OK."""
        response = await client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_check_returns_json(self, client: AsyncClient) -> None:
        """Test that health check returns valid JSON."""
        response = await client.get("/health")
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_health_check_has_required_fields(self, client: AsyncClient) -> None:
        """Test that health check response has all required fields."""
        response = await client.get("/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "environment" in data
        assert "checks" in data

    @pytest.mark.asyncio
    async def test_health_check_status_values(self, client: AsyncClient) -> None:
        """Test that status is either healthy or degraded."""
        response = await client.get("/health")
        data = response.json()

        assert data["status"] in ["healthy", "degraded"]

    @pytest.mark.asyncio
    async def test_health_check_checks_structure(self, client: AsyncClient) -> None:
        """Test that checks object has database and redis."""
        response = await client.get("/health")
        data = response.json()

        checks = data["checks"]
        assert "database" in checks
        assert "redis" in checks
        assert checks["database"] in ["ok", "failed"]
        assert checks["redis"] in ["ok", "failed"]

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient) -> None:
        """Test root endpoint returns basic info."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()

        assert "name" in data
        assert "version" in data
        assert "health" in data
        assert "api" in data
