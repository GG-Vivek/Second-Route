"""
Outcome API routes (Phase 4 - F4.2).

Provides endpoints to record the realized outcome of a dispositioned unit
and to read outcomes back. Outcomes are append-only: recording a second
outcome for the same unit creates a new row and never overwrites the first.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.db import get_session
from secondroute.decision.models import Decision
from secondroute.feedback.models import Outcome
from secondroute.feedback.schemas import OutcomeCreate, OutcomeListRead, OutcomeRead

router = APIRouter(tags=["Outcomes"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _latest_decision_for_unit(session: AsyncSession, unit_id: UUID) -> Optional[Decision]:
    """Return the most recent decision for a unit, if any."""
    result = await session.execute(
        select(Decision)
        .where(Decision.unit_id == unit_id)
        .order_by(desc(Decision.created_at))
        .limit(1)
    )
    return result.scalars().first()


@router.post(
    "/units/{unit_id}/outcome",
    response_model=OutcomeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record the outcome of a dispositioned unit",
)
async def create_outcome(
    unit_id: UUID,
    body: OutcomeCreate,
    session: SessionDep,
) -> OutcomeRead:
    """Record what actually happened to a unit.

    A unit with no decision cannot have an outcome: there is nothing to
    compare the realized numbers against. The outcome is linked to the
    decision that was active at disposition time.

    Outcomes are append-only. Recording a second outcome for the same unit
    creates a new row and leaves the first one untouched.

    Args:
        unit_id: The unit that was dispositioned.
        body: The realized numbers.
        session: Database session.

    Returns:
        The recorded outcome.

    Raises:
        HTTPException: 404 when the unit has no decision to link to.
    """
    if body.decision_id is not None:
        decision = await session.get(Decision, body.decision_id)
        if decision is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Decision not found",
            )
        if decision.unit_id != unit_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Decision does not belong to this unit",
            )
    else:
        decision = await _latest_decision_for_unit(session, unit_id)
        if decision is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit has no decision to link an outcome to",
            )

    outcome = Outcome(
        unit_id=unit_id,
        decision_id=decision.id,
        channel_taken=body.channel_taken,
        sale_price=body.sale_price,
        fees_actual=body.fees_actual,
        repair_cost_actual=body.repair_cost_actual,
        logistics_actual=body.logistics_actual,
        days_to_disposition=body.days_to_disposition,
        final_status=body.final_status,
    )
    session.add(outcome)
    await session.flush()
    await session.refresh(outcome)

    return OutcomeRead.model_validate(outcome)


@router.get(
    "/units/{unit_id}/outcomes",
    response_model=OutcomeListRead,
    summary="List the outcomes recorded for a unit",
)
async def list_unit_outcomes(
    unit_id: UUID,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OutcomeListRead:
    """Return the outcomes recorded for a unit, newest first.

    Args:
        unit_id: The unit.
        session: Database session.
        limit: Page size.
        offset: Page offset.

    Returns:
        A page of outcomes.
    """
    total_result = await session.execute(
        select(func.count()).select_from(Outcome).where(Outcome.unit_id == unit_id)
    )
    total = int(total_result.scalar_one())

    result = await session.execute(
        select(Outcome)
        .where(Outcome.unit_id == unit_id)
        .order_by(desc(Outcome.recorded_at))
        .limit(limit)
        .offset(offset)
    )
    outcomes = result.scalars().all()

    return OutcomeListRead(
        items=[OutcomeRead.model_validate(o) for o in outcomes],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/decisions/{decision_id}/outcomes",
    response_model=OutcomeListRead,
    summary="List the outcomes linked to a decision",
)
async def list_decision_outcomes(
    decision_id: UUID,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OutcomeListRead:
    """Return the outcomes linked to a decision, newest first.

    Args:
        decision_id: The decision.
        session: Database session.
        limit: Page size.
        offset: Page offset.

    Returns:
        A page of outcomes.
    """
    total_result = await session.execute(
        select(func.count()).select_from(Outcome).where(Outcome.decision_id == decision_id)
    )
    total = int(total_result.scalar_one())

    result = await session.execute(
        select(Outcome)
        .where(Outcome.decision_id == decision_id)
        .order_by(desc(Outcome.recorded_at))
        .limit(limit)
        .offset(offset)
    )
    outcomes = result.scalars().all()

    return OutcomeListRead(
        items=[OutcomeRead.model_validate(o) for o in outcomes],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/outcomes/{outcome_id}",
    response_model=OutcomeRead,
    summary="Get an outcome by ID",
)
async def get_outcome(outcome_id: UUID, session: SessionDep) -> OutcomeRead:
    """Return one outcome.

    Args:
        outcome_id: The outcome.
        session: Database session.

    Returns:
        The outcome.

    Raises:
        HTTPException: 404 when the outcome does not exist.
    """
    outcome = await session.get(Outcome, outcome_id)
    if outcome is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outcome not found",
        )
    return OutcomeRead.model_validate(outcome)
