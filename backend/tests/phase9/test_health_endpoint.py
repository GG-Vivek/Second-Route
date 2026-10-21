"""
The health of the service (F9.5).

The endpoint answers at the root as well as under the versioned prefix.
The root is where a load balancer and a container health check look, and
the front end has a page of its own at ``/health``, so the two cannot
both have it.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from secondroute.api.main import health_status


class TestTheHealthEndpoint:
    """The health check."""

    @pytest.mark.asyncio
    async def test_it_answers_at_the_root(self, client: AsyncClient) -> None:
        """The root is where the infrastructure looks."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] in ("healthy", "degraded")

    @pytest.mark.asyncio
    async def test_it_answers_under_the_versioned_prefix(self, client: AsyncClient) -> None:
        """The application asks for this one."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] in ("healthy", "degraded")

    @pytest.mark.asyncio
    async def test_a_dependency_that_is_not_in_use_is_not_a_failure(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A machine with no cache is not degraded for the want of one."""
        from secondroute.core.config import settings

        monkeypatch.setattr(settings, "REDIS_URL", "")

        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["checks"]["redis"] == "not_configured"

    @pytest.mark.asyncio
    async def test_the_two_answers_are_the_same(self, client: AsyncClient) -> None:
        """There is one health check, not two."""
        root = await client.get("/health")
        versioned = await client.get("/api/v1/health")
        assert root.json() == versioned.json()


class TestTheRule:
    """A dependency that is not configured is not a failure."""

    def test_a_working_cache_is_healthy(self) -> None:
        assert health_status(True, "ok") == "healthy"

    def test_a_cache_that_is_not_in_use_is_healthy(self) -> None:
        assert health_status(True, "not_configured") == "healthy"

    def test_a_cache_that_is_broken_degrades_the_service(self) -> None:
        assert health_status(True, "failed") == "degraded"

    def test_a_database_that_is_down_degrades_the_service(self) -> None:
        assert health_status(False, "ok") == "degraded"
