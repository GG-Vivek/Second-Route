"""
Override API routes (Phase 4 - F4.1).

Provides endpoints to override a decision recommendation with a required
reason, and to read the overrides recorded for a decision or a unit.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.db import get_session
from secondroute.decision.models import Decision
from secondroute.feedback.models import Override
from secondroute.feedback.schemas import OverrideCreate, OverrideListRead, OverrideRead

router = APIRouter(tags=["Overrides"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/decisions/{decision_id}/override",
    response_model=OverrideRead,
    status_code=status.HTTP_201_CREATED,
    summary="Override a decision recommendation",
)
async def create_override(
    decision_id: UUID,
    body: OverrideCreate,
    session: SessionDep,
) -> OverrideRead:
    """Record a human override of a decision recommendation.

    The reason is mandatory. Overrides are append-only: they are never
    updated or deleted.

    Args:
        decision_id: The decision being overridden.
        body: The chosen channel and the reason.
        session: Database session.

    Returns:
        The recorded override.

    Raises:
        HTTPException: 404 when the decision does not exist.
    """
    decision = await session.get(Decision, decision_id)
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision not found",
        )

    override = Override(
        decision_id=decision_id,
        user_id=None,  # "anonymous" until Phase 5 auth
        chosen_channel=body.chosen_channel,
        reason_text=body.reason_text,
    )
    session.add(override)
    await session.flush()
    await session.refresh(override)

    return OverrideRead.model_validate(override)


@router.get(
    "/decisions/{decision_id}/overrides",
    response_model=OverrideListRead,
    summary="List the overrides for a decision",
)
async def list_decision_overrides(
    decision_id: UUID,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OverrideListRead:
    """Return the overrides recorded for a decision, newest first.

    Args:
        decision_id: The decision.
        session: Database session.
        limit: Page size.
        offset: Page offset.

    Returns:
        A page of overrides.
    """
    total_result = await session.execute(
        select(func.count()).select_from(Override).where(Override.decision_id == decision_id)
    )
    total = int(total_result.scalar_one())

    result = await session.execute(
        select(Override)
        .where(Override.decision_id == decision_id)
        .order_by(desc(Override.created_at))
        .limit(limit)
        .offset(offset)
    )
    overrides = result.scalars().all()

    return OverrideListRead(
        items=[OverrideRead.model_validate(o) for o in overrides],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/units/{unit_id}/overrides",
    response_model=OverrideListRead,
    summary="List the overrides for a unit",
)
async def list_unit_overrides(
    unit_id: UUID,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OverrideListRead:
    """Return the overrides recorded for a unit, across all its decisions.

    Args:
        unit_id: The unit.
        session: Database session.
        limit: Page size.
        offset: Page offset.

    Returns:
        A page of overrides.
    """
    total_result = await session.execute(
        select(func.count())
        .select_from(Override)
        .join(Decision, Override.decision_id == Decision.id)
        .where(Decision.unit_id == unit_id)
    )
    total = int(total_result.scalar_one())

    result = await session.execute(
        select(Override)
        .join(Decision, Override.decision_id == Decision.id)
        .where(Decision.unit_id == unit_id)
        .order_by(desc(Override.created_at))
        .limit(limit)
        .offset(offset)
    )
    overrides = result.scalars().all()

    return OverrideListRead(
        items=[OverrideRead.model_validate(o) for o in overrides],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/overrides/{override_id}",
    response_model=OverrideRead,
    summary="Get an override by ID",
)
async def get_override(override_id: UUID, session: SessionDep) -> OverrideRead:
    """Return one override.

    Args:
        override_id: The override.
        session: Database session.

    Returns:
        The override.

    Raises:
        HTTPException: 404 when the override does not exist.
    """
    override = await session.get(Override, override_id)
    if override is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Override not found",
        )
    return OverrideRead.model_validate(override)
