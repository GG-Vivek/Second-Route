"""
Backtest API routes (Phase 5 - F5.6).

Endpoints:

* ``POST /api/v1/backtests`` - replay past decisions and compare the
  engine against a baseline policy
* ``GET  /api/v1/backtests`` - list the stored runs
* ``GET  /api/v1/backtests/{run_id}`` - read a stored run
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.backtest.baseline import (
    BaselinePolicy,
    FixedChannelBaseline,
    MostCommonChannelBaseline,
)
from secondroute.backtest.engine import BacktestRunError, run_backtest
from secondroute.backtest.lookahead import LookAheadError
from secondroute.backtest.models import BacktestRun
from secondroute.backtest.schemas import (
    BacktestRequest,
    BacktestRunRead,
)
from secondroute.core.db import get_session

router = APIRouter(prefix="/backtests", tags=["Backtests"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _baseline_from_request(body: BacktestRequest) -> BaselinePolicy:
    """Build the baseline policy the request asked for.

    Raises:
        HTTPException: 422 when the request names a baseline that does not
            exist, or a fixed baseline with no channel.
    """
    if body.baseline == "fixed-channel":
        if not body.baseline_channel:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A fixed-channel baseline needs a baseline_channel.",
            )
        return FixedChannelBaseline(channel=body.baseline_channel)
    if body.baseline == "most-common-channel":
        # The counts are filled in by the runner once it knows what the
        # partner actually did; until then the policy has no answer.
        return MostCommonChannelBaseline(counts={})
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Unknown baseline {body.baseline!r}.",
    )


def _to_run_read(run: BacktestRun) -> BacktestRunRead:
    """Turn a stored run into its read model."""
    return BacktestRunRead(
        id=str(run.id),
        org_id=str(run.org_id) if run.org_id else None,
        created_at=run.created_at,
        name=run.name,
        baseline_name=run.baseline_name,
        baseline_channel=run.baseline_channel,
        window_start=run.window_start,
        window_end=run.window_end,
        decision_count=run.decision_count,
        mean_difference=run.mean_difference,
        ci_lower=run.ci_lower,
        ci_upper=run.ci_upper,
        confidence=run.confidence,
        method=run.method,
        samples=run.samples,
        seed=run.seed,
        is_synthetic=run.is_synthetic,
        report=run.report,
    )


@router.post(
    "",
    response_model=BacktestRunRead,
    status_code=status.HTTP_201_CREATED,
    summary="Replay past decisions and compare against a baseline",
)
async def create_backtest(body: BacktestRequest, session: SessionDep) -> BacktestRunRead:
    """Run a backtest over the decisions of one organisation.

    The run is refused if any decision in scope used data dated after it
    was made. A backtest that cannot prove it had no look-ahead is not
    reported at all.

    Args:
        body: What to compare and over which window.
        session: Database session.

    Returns:
        The stored run, including the full report.

    Raises:
        HTTPException: 409 when a decision in scope leaked, 422 when the
            request is not usable.
    """
    baseline = _baseline_from_request(body)

    try:
        result = await run_backtest(
            session,
            org_id=body.org_id,
            baseline=baseline,
            window_start=body.window_start,
            window_end=body.window_end,
            confidence=body.confidence,
            samples=body.samples,
            seed=body.seed,
        )
    except LookAheadError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "findings": [finding.as_dict() for finding in exc.report.leaks],
            },
        ) from exc
    except BacktestRunError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    report = result.as_dict()
    run = BacktestRun(
        org_id=body.org_id,
        created_at=datetime.utcnow(),
        name=body.name,
        baseline_name=result.baseline_name,
        baseline_channel=result.baseline_channel,
        window_start=result.window_start,
        window_end=result.window_end,
        decision_count=result.decision_count,
        mean_difference=result.mean_difference,
        ci_lower=result.interval.lower if result.interval else None,
        ci_upper=result.interval.upper if result.interval else None,
        confidence=result.confidence,
        method=result.method,
        samples=body.samples,
        seed=body.seed,
        report_json=json.dumps(report, sort_keys=True),
        is_synthetic=True,
    )
    session.add(run)
    await session.flush()
    await session.refresh(run)

    return _to_run_read(run)


@router.get(
    "",
    response_model=list[BacktestRunRead],
    summary="List the stored backtest runs",
)
async def list_backtests(
    session: SessionDep,
    org_id: UUID | None = Query(None, description="Only runs of this organisation."),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[BacktestRunRead]:
    """List the stored backtest runs, newest first.

    Args:
        session: Database session.
        org_id: Only runs of this organisation.
        limit: Maximum results.
        offset: Offset for pagination.

    Returns:
        The stored runs.
    """
    statement = select(BacktestRun)
    if org_id is not None:
        statement = statement.where(BacktestRun.org_id == org_id)
    statement = statement.order_by(desc(BacktestRun.created_at)).limit(limit).offset(offset)

    result = await session.execute(statement)
    return [_to_run_read(run) for run in result.scalars().all()]


@router.get(
    "/{run_id}",
    response_model=BacktestRunRead,
    summary="Read a stored backtest run",
)
async def get_backtest(run_id: UUID, session: SessionDep) -> BacktestRunRead:
    """Read one stored backtest run.

    Args:
        run_id: The run to read.
        session: Database session.

    Returns:
        The stored run.

    Raises:
        HTTPException: 404 when the run does not exist.
    """
    run = await session.get(BacktestRun, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest run {run_id} not found",
        )
    return _to_run_read(run)
