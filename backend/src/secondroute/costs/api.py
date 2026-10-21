"""
Cost administration API (Phase 2 - F2.4).

Reads and updates the cost tables. Every write requires a ``source``: a cost
value without provenance is rejected with a 422.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.db import current_org_uuid, get_session
from secondroute.costs.models import CostKind, CostTable
from secondroute.costs.schemas import CostCreate, CostListRead, CostRead, CostUpdate
from secondroute.costs.service import seed_default_costs

router = APIRouter(prefix="/costs", tags=["Costs"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=CostListRead, summary="List cost values")
async def list_costs(
    session: SessionDep,
    kind: Annotated[str | None, Query(description="Filter by cost kind")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CostListRead:
    """Return the cost rows, optionally filtered by kind.

    Args:
        session: Database session.
        kind: Restrict to one cost kind.
        limit: Page size.
        offset: Page offset.

    Returns:
        A page of cost rows.
    """
    query = select(CostTable)
    count_query = select(func.count()).select_from(CostTable)
    if kind:
        query = query.where(CostTable.kind == kind)
        count_query = count_query.where(CostTable.kind == kind)

    total = int((await session.execute(count_query)).scalar_one())
    result = await session.execute(
        query.order_by(CostTable.kind, CostTable.key).limit(limit).offset(offset)
    )
    rows = result.scalars().all()

    return CostListRead(items=[_to_read(row) for row in rows], total=total)


@router.get("/kinds", summary="List the supported cost kinds")
async def list_cost_kinds() -> dict[str, Any]:
    """Return every cost kind the decision engine understands.

    Returns:
        The cost kinds with a description of each.
    """
    return {
        "kinds": [
            {
                "kind": CostKind.CHANNEL_FEE_PCT,
                "key_format": "<channel>",
                "description": "Share of the sale price taken as a fee.",
            },
            {
                "kind": CostKind.FIXED_FEE,
                "key_format": "<channel>",
                "description": "Fixed per-unit transaction fee.",
            },
            {
                "kind": CostKind.LOGISTICS_COST,
                "key_format": "<channel>",
                "description": "Outbound logistics cost per unit.",
            },
            {
                "kind": CostKind.HANDLING_COST,
                "key_format": "<channel>",
                "description": "Handling, photography and repacking cost per unit.",
            },
            {
                "kind": CostKind.REPAIR_COST,
                "key_format": "<channel>:<grade>",
                "description": "Expected repair spend for a channel and grade.",
            },
            {
                "kind": CostKind.HOLDING_COST_PER_DAY,
                "key_format": "<channel>",
                "description": "Cost of holding a unit for one day.",
            },
            {
                "kind": CostKind.EXPECTED_DAYS_TO_SELL,
                "key_format": "<channel>:<grade>",
                "description": "Expected days to sell for a channel and grade.",
            },
            {
                "kind": CostKind.RESALE_RECOVERY_PCT,
                "key_format": "<channel>",
                "description": "Share of the resale value recovered by the channel.",
            },
        ]
    }


@router.post(
    "",
    response_model=CostRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a cost value",
)
async def create_cost(body: CostCreate, session: SessionDep) -> CostRead:
    """Create a cost row.

    Args:
        body: The cost to create. ``source`` is required.
        session: Database session.

    Returns:
        The created row.

    Raises:
        HTTPException: 409 when the row already exists.
    """
    existing = await session.execute(
        select(CostTable).where(
            CostTable.org_id == body.org_id,
            CostTable.kind == body.kind,
            CostTable.key == body.key,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cost {body.kind}:{body.key} already exists",
        )

    row = CostTable(
        org_id=body.org_id,
        kind=body.kind,
        key=body.key,
        value=body.value,
        currency=body.currency,
        source=body.source,
        as_of=body.as_of,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return _to_read(row)


@router.patch("/{cost_id}", response_model=CostRead, summary="Update a cost value")
async def update_cost(cost_id: UUID, body: CostUpdate, session: SessionDep) -> CostRead:
    """Update a cost row.

    Args:
        cost_id: The row to update.
        body: The fields to change.
        session: Database session.

    Returns:
        The updated row.

    Raises:
        HTTPException: 404 when the row does not exist.
    """
    row = await session.get(CostTable, cost_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cost not found",
        )

    if body.value is not None:
        row.value = body.value
    if body.source is not None:
        row.source = body.source
    if body.as_of is not None:
        row.as_of = body.as_of
    if body.currency is not None:
        row.currency = body.currency

    await session.flush()
    await session.refresh(row)
    return _to_read(row)


@router.post(
    "/seed-defaults",
    summary="Seed the default cost values",
)
async def seed_defaults(session: SessionDep) -> dict[str, int]:
    """Insert the default cost rows if the table is empty.

    Args:
        session: Database session.

    Returns:
        How many rows were inserted.
    """
    inserted = await seed_default_costs(session, current_org_uuid())
    return {"inserted": inserted}


def _to_read(row: CostTable) -> CostRead:
    """Convert a cost row into the API schema."""
    return CostRead(
        id=row.id,
        org_id=row.org_id,
        kind=row.kind,
        key=row.key,
        value=row.value,
        currency=row.currency,
        source=row.source,
        as_of=row.as_of,
        created_at=row.created_at.isoformat() if row.created_at else datetime.utcnow().isoformat(),
        updated_at=row.updated_at.isoformat() if row.updated_at else datetime.utcnow().isoformat(),
    )
