"""
Analytics API routes (Phase 4).

Exposes the feedback loop measurements: the predicted vs realized
comparison (F4.3), the time-to-sell model (F4.4), the regret calculation
(F4.5) and the calibration report (F4.6).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.analytics.predicted_vs_realized import PredictedVsRealizedService
from secondroute.analytics.regret import RegretService
from secondroute.analytics.schemas import (
    PredictedVsRealizedListRead,
    PredictedVsRealizedRead,
    RegretEstimateRead,
    RegretMeasurementRead,
    RegretReportRead,
    StoredRegretRead,
    TimeToSellCellRead,
    TimeToSellRead,
)
from secondroute.analytics.time_to_sell import DEFAULT_MIN_SAMPLE, TimeToSellService
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


@router.get(
    "/time-to-sell",
    response_model=TimeToSellRead,
    summary="Kaplan-Meier time-to-sell curves by channel and grade",
)
async def get_time_to_sell(
    session: SessionDep,
    channel: Annotated[str | None, Query(description="Restrict to one channel")] = None,
    grade: Annotated[str | None, Query(description="Restrict to one grade")] = None,
    min_sample: Annotated[
        int,
        Query(
            ge=1,
            le=1000,
            description="Smallest sample a cell needs before its curve is trusted",
        ),
    ] = DEFAULT_MIN_SAMPLE,
) -> TimeToSellRead:
    """Return the time-to-sell curves computed from the recorded outcomes.

    A cell whose sample is below ``min_sample`` falls back to the Phase 3
    prior, and says so through ``used_fallback`` and ``source``.

    Args:
        session: Database session.
        channel: Restrict to a single channel.
        grade: Restrict to a single grade.
        min_sample: The smallest sample a cell needs before its curve is
            trusted.

    Returns:
        One cell per channel and grade that has at least one outcome.
    """
    service = TimeToSellService()
    cells = await service.curves(session, channel=channel, grade=grade, min_sample=min_sample)

    return TimeToSellRead(
        min_sample=min_sample,
        items=[TimeToSellCellRead.model_validate(cell) for cell in cells],
        total=len(cells),
        fallback_count=sum(1 for cell in cells if cell.used_fallback),
    )


@router.get(
    "/regret",
    response_model=RegretReportRead,
    summary="The regret of the recorded dispositions",
)
async def get_regret(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> RegretReportRead:
    """Return the regret of the recorded dispositions.

    The regret is computed live from the outcomes and the decisions, so a
    report never goes stale. Observed and estimated figures are reported
    separately, and the combined total says what it is made of.

    Args:
        session: Database session.
        limit: Maximum number of outcomes to consider.

    Returns:
        The regret of every outcome, newest first, with the summary.
    """
    service = RegretService()
    estimates = await service.measure_all(session, limit=limit)

    return RegretReportRead(
        items=[RegretEstimateRead.model_validate(estimate) for estimate in estimates],
        total=len(estimates),
        summary=service.summarize(estimates).to_dict(),
    )


@router.post(
    "/units/{unit_id}/regret",
    response_model=StoredRegretRead,
    summary="Record the regret of a unit's dispositions",
)
async def record_unit_regret(
    unit_id: UUID,
    session: SessionDep,
) -> StoredRegretRead:
    """Compute and store the regret of a unit's recorded dispositions.

    The rows are append-only: recording the same unit twice adds a second
    set of rows rather than changing the first.

    Args:
        unit_id: The unit.
        session: Database session.

    Returns:
        The stored measurements, with the observed and the estimated
        figures kept apart.
    """
    from typing import cast

    from secondroute.intake.models import Unit

    service = RegretService()
    estimates = await service.measure_unit(session, unit_id)
    if not estimates:
        return StoredRegretRead(items=[], total=0, summary=service.summarize([]).to_dict())

    unit = await session.get(Unit, unit_id)
    org_id = cast("UUID | None", unit.org_id) if unit is not None else None

    measurements = [estimate.as_measurement(org_id=org_id) for estimate in estimates]
    session.add_all(measurements)
    await session.commit()
    for measurement in measurements:
        await session.refresh(measurement)

    return StoredRegretRead(
        items=[RegretMeasurementRead.model_validate(m) for m in measurements],
        total=len(measurements),
        summary=service.summarize_measurements(measurements).to_dict(),
    )
