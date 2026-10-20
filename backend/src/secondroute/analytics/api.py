"""
Analytics API routes (Phase 4 - F4.3).

Exposes the predicted vs realized comparison: for each unit, what the engine
predicted against what actually happened, with the residual and whether the
realized value fell inside the predicted range.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.analytics.predicted_vs_realized import PredictedVsRealizedService
from secondroute.analytics.schemas import (
    PredictedVsRealizedListRead,
    PredictedVsRealizedRead,
)
from secondroute.core.db import get_session

router = APIRouter(prefix="/analytics", tags=["Analytics"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/units/{unit_id}/predicted-vs-realized",
    response_model=PredictedVsRealizedListRead,
    summary="Compare predicted net against realized net for a unit",
)
async def get_unit_predicted_vs_realized(
    unit_id: UUID,
    session: SessionDep,
) -> PredictedVsRealizedListRead:
    """Return the predicted vs realized comparison for one unit.

    Args:
        unit_id: The unit.
        session: Database session.

    Returns:
        One comparison per recorded outcome, newest first, with summary stats.
    """
    service = PredictedVsRealizedService()
    comparisons = await service.compare_unit(session, unit_id)

    return PredictedVsRealizedListRead(
        items=[PredictedVsRealizedRead.model_validate(c) for c in comparisons],
        total=len(comparisons),
        summary=service.summarize(comparisons),
    )


@router.get(
    "/predicted-vs-realized",
    response_model=PredictedVsRealizedListRead,
    summary="Compare predicted net against realized net across all units",
)
async def get_predicted_vs_realized(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> PredictedVsRealizedListRead:
    """Return the predicted vs realized comparison across every unit.

    Args:
        session: Database session.
        limit: Maximum number of outcomes to compare.

    Returns:
        One comparison per recorded outcome, newest first, with summary stats.
    """
    service = PredictedVsRealizedService()
    comparisons = await service.compare_all(session, limit=limit)

    return PredictedVsRealizedListRead(
        items=[PredictedVsRealizedRead.model_validate(c) for c in comparisons],
        total=len(comparisons),
        summary=service.summarize(comparisons),
    )
