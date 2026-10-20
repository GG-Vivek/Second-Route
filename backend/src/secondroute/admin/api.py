"""
Source health API (Phase 3 - F3.9).

``GET /api/v1/sources/health`` reports every data source: when it last spoke,
whether what it said is fresh, and how many times it has failed.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.admin.health import (
    DEFAULT_STALE_HOURS,
    SourceStatus,
    collect_source_health,
)
from secondroute.core.db import get_session

router = APIRouter(prefix="/sources", tags=["Sources"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/health", summary="Report the health of every data source")
async def source_health(
    session: SessionDep,
    stale_limit_hours: Annotated[
        int, Query(ge=1, le=8760, description="Age at which a source goes stale")
    ] = DEFAULT_STALE_HOURS,
) -> dict[str, Any]:
    """Report the health of every data source.

    Args:
        session: Database session.
        stale_limit_hours: The age at which a source goes stale.

    Returns:
        The status of every source, plus a summary.
    """
    statuses = await collect_source_health(session, stale_limit_hours=stale_limit_hours)
    return {
        "sources": [status.as_dict() for status in statuses],
        "summary": {
            "total": len(statuses),
            "fresh": sum(1 for status in statuses if status.status == "fresh"),
            "stale": sum(1 for status in statuses if status.status == "stale"),
            "missing": sum(1 for status in statuses if status.status == "missing"),
            "errors": sum(status.error_count for status in statuses),
        },
        "stale_limit_hours": stale_limit_hours,
    }
