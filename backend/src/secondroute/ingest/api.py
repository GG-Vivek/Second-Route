"""
Partner data import API (Phase 3 - F3.2).

Endpoints:

* ``POST /api/v1/imports/sales/preview`` - upload a file, see its columns and
  the suggested mapping. This is the mapping step.
* ``POST /api/v1/imports/sales`` - import a file, optionally as a dry run.
* ``GET  /api/v1/imports/sales`` - list the past imports.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.db import get_session
from secondroute.ingest.components import (
    import_component_prices_csv,
    list_component_prices,
    upsert_component_price,
)
from secondroute.ingest.fred import pull_component_prices
from secondroute.ingest.models import ImportFile
from secondroute.ingest.sales import import_sales, preview_sales_file
from secondroute.ingest.schemas import (
    ColumnMapping,
    ComponentPriceCreate,
    ComponentPriceImportRead,
    ComponentPriceListRead,
    ComponentPriceRead,
    ImportListRead,
    ImportPreview,
    ImportRecordRead,
    ImportResult,
)

router = APIRouter(prefix="/imports", tags=["Imports"])
component_router = APIRouter(prefix="/components", tags=["Components"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

#: Refuse files bigger than this. A partner sales file is a spreadsheet, not
#: a data dump.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@router.post(
    "/sales/preview",
    response_model=ImportPreview,
    summary="Preview a partner sales file and suggest a column mapping",
)
async def preview_sales(
    file: Annotated[UploadFile, File(description="The sales CSV")],
) -> ImportPreview:
    """Describe a sales file without importing anything.

    Args:
        file: The uploaded CSV.

    Returns:
        The columns, the suggested mapping, the row count and the file hash.
    """
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"the file is larger than {MAX_UPLOAD_BYTES} bytes",
        )
    return preview_sales_file(content, file.filename or "upload.csv")


@router.post(
    "/sales",
    response_model=ImportResult,
    summary="Import a partner sales file",
)
async def import_sales_file(
    session: SessionDep,
    file: Annotated[UploadFile, File(description="The sales CSV")],
    source: Annotated[str, Form(description="The partner's name")] = "partner",
    dry_run: Annotated[bool, Form(description="Report without writing")] = False,
    mapping_json: Annotated[
        str | None, Form(description="JSON column mapping; auto-detected when omitted")
    ] = None,
) -> ImportResult:
    """Import a partner sales file.

    The import is idempotent: the same file imported twice changes nothing.

    Args:
        session: Database session.
        file: The uploaded CSV.
        source: The partner's name. This becomes the price observation source.
        dry_run: When true, nothing is written but the counts are identical.
        mapping_json: An explicit column mapping as JSON.

    Returns:
        The result of the import.

    Raises:
        HTTPException: 422 when the file cannot be mapped.
    """
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"the file is larger than {MAX_UPLOAD_BYTES} bytes",
        )

    mapping: ColumnMapping | None = None
    if mapping_json:
        import json

        try:
            mapping = ColumnMapping.model_validate(json.loads(mapping_json))
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"the column mapping is not valid: {exc}",
            ) from exc

    try:
        return await import_sales(
            session,
            content,
            filename=file.filename or "upload.csv",
            source=source,
            mapping=mapping,
            dry_run=dry_run,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get(
    "/sales",
    response_model=ImportListRead,
    summary="List the past sales imports",
)
async def list_sales_imports(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ImportListRead:
    """Return the past sales imports, newest first.

    Args:
        session: Database session.
        limit: Page size.
        offset: Page offset.

    Returns:
        A page of import records.
    """
    total_result = await session.execute(
        select(func.count()).select_from(ImportFile).where(ImportFile.import_kind == "sales")
    )
    total = int(total_result.scalar_one())

    result = await session.execute(
        select(ImportFile)
        .where(ImportFile.import_kind == "sales")
        .order_by(ImportFile.imported_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = result.scalars().all()

    return ImportListRead(
        items=[ImportRecordRead.model_validate(row) for row in rows],
        total=total,
    )


# ----------------------------------------------------------------------
# Component prices
# ----------------------------------------------------------------------


@component_router.get(
    "/prices",
    response_model=ComponentPriceListRead,
    summary="List the component prices",
)
async def list_component_prices_endpoint(
    session: SessionDep,
    component_type: Annotated[
        str | None, Query(description="Restrict to one component type")
    ] = None,
) -> ComponentPriceListRead:
    """Return the component prices, each flagged stale or not.

    Args:
        session: Database session.
        component_type: Restrict to one component type.

    Returns:
        The component prices and how many of them are stale.
    """
    views = await list_component_prices(session, component_type=component_type)
    return ComponentPriceListRead(
        items=[ComponentPriceRead(**view.as_dict()) for view in views],
        total=len(views),
        stale_count=sum(1 for view in views if view.is_stale),
    )


@component_router.post(
    "/prices",
    response_model=ComponentPriceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Enter a component price",
)
async def create_component_price(
    session: SessionDep,
    body: ComponentPriceCreate,
) -> ComponentPriceRead:
    """Enter or update a component price by hand.

    Args:
        session: Database session.
        body: The price.

    Returns:
        The stored price, flagged stale or not.
    """
    row = await upsert_component_price(
        session,
        component_type=body.component_type,
        price_per_unit=body.price_per_unit,
        source=body.source,
        as_of=body.as_of,
        unit=body.unit,
        confidence_weight=body.confidence_weight,
    )
    views = await list_component_prices(session, component_type=body.component_type)
    for view in views:
        if str(view.id) == str(row.id):
            return ComponentPriceRead(**view.as_dict())
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="the price was stored but could not be read back",
    )


@component_router.post(
    "/prices/import",
    response_model=ComponentPriceImportRead,
    summary="Import component prices from a partner CSV",
)
async def import_component_prices(
    session: SessionDep,
    file: Annotated[UploadFile, File(description="The component price CSV")],
    source: Annotated[str, Form(description="The partner's name")] = "partner_csv",
) -> ComponentPriceImportRead:
    """Import component prices from a partner CSV.

    Args:
        session: Database session.
        file: The uploaded CSV.
        source: The source recorded on every imported row.

    Returns:
        How many rows were imported and what was wrong with the rest.
    """
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"the file is larger than {MAX_UPLOAD_BYTES} bytes",
        )
    try:
        imported, errors = await import_component_prices_csv(session, content, source=source)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return ComponentPriceImportRead(rows_imported=imported, errors=errors)


@component_router.post(
    "/prices/pull-fred",
    summary="Pull the configured FRED series into the component price table",
)
async def pull_fred_prices(session: SessionDep) -> dict[str, Any]:
    """Pull the configured FRED series.

    This is what the scheduled job calls. It does nothing when no FRED API
    key is configured.

    Args:
        session: Database session.

    Returns:
        How many rows were written.
    """
    rows = await pull_component_prices(session)
    return {"rows_written": rows}
