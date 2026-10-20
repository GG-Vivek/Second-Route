"""
The export API (Phase 4 - F4.8).

The decisions, the overrides and the outcomes can be exported as CSV and
read back to check that the export round-trips.
"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.analytics.export import ExportService, entity_for, read_csv
from secondroute.analytics.schemas import ImportResultRead
from secondroute.core.db import get_session

router = APIRouter(prefix="/export", tags=["Export"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/decisions",
    summary="Export the decisions as CSV",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}}},
)
async def export_decisions(session: SessionDep) -> Response:
    """Export the decisions, with the snapshot hash and the model version.

    Args:
        session: Database session.

    Returns:
        The CSV.
    """
    csv_text, _hash = await ExportService().decisions(session)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="decisions.csv"'},
    )


@router.get(
    "/overrides",
    summary="Export the overrides as CSV",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}}},
)
async def export_overrides(session: SessionDep) -> Response:
    """Export the overrides, with the reason and the channel that was taken.

    Args:
        session: Database session.

    Returns:
        The CSV.
    """
    csv_text, _hash = await ExportService().overrides(session)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="overrides.csv"'},
    )


@router.get(
    "/outcomes",
    summary="Export the outcomes as CSV",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}}},
)
async def export_outcomes(session: SessionDep) -> Response:
    """Export the outcomes, with the realized numbers.

    Args:
        session: Database session.

    Returns:
        The CSV.
    """
    csv_text, _hash = await ExportService().outcomes(session)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="outcomes.csv"'},
    )


@router.post(
    "/{entity}/import",
    summary="Read an export back and check that it round-trips",
    response_model=ImportResultRead,
)
async def import_export(
    entity: str,
    session: SessionDep,
    csv_text: Annotated[str, Body(media_type="text/csv")],
) -> ImportResultRead:
    """Read an export back and check that it round-trips.

    The rows are not written to the database: the decisions, the overrides
    and the outcomes are append-only, so a re-import would duplicate them.
    What the import does is recompute the hash of every row and report
    whether the export came back unchanged.

    Args:
        entity: Which export to read: ``decisions``, ``overrides`` or
            ``outcomes``.
        session: Database session.
        csv_text: The CSV.

    Returns:
        What the import found.
    """
    known = entity_for(entity)
    if known is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown export: {entity}",
        )

    result = read_csv(known, csv_text)

    return ImportResultRead.model_validate(result.to_dict())
