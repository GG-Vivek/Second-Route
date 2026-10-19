"""
Identity API routes for Phase 1.

Provides SKU catalog and serial prefix lookup endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from secondroute.core.db import get_session
from secondroute.identity.models import SKU, SerialPrefix
from secondroute.identity.schemas import (
    SerialPrefixCreate,
    SerialPrefixRead,
    SKUCreate,
    SKULookupError,
    SKULookupResponse,
    SKURead,
)

router = APIRouter(prefix="/skus", tags=["SKU Catalog"])


@router.post(
    "",
    response_model=SKURead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new SKU",
)
async def create_sku(sku_data: SKUCreate, session: AsyncSession = Depends(get_session)) -> SKURead:
    """
    Create a new SKU in the catalog.

    Args:
        sku_data: SKU data to create
        session: Database session

    Returns:
        Created SKU

    Raises:
        HTTPException: If SKU variant already exists
    """
    # Check for existing SKU with same variant
    existing = await session.execute(
        select(SKU).where(
            SKU.family == sku_data.family,
            SKU.model_name == sku_data.model_name,
            SKU.year == sku_data.year,
            SKU.storage_gb == sku_data.storage_gb,
            SKU.ram_gb == sku_data.ram_gb,
            SKU.color == sku_data.color,
            SKU.region == sku_data.region,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="SKU with this variant already exists",
        )

    sku = SKU(**sku_data.model_dump())
    session.add(sku)
    await session.flush()
    await session.refresh(sku)
    return SKURead.model_validate(sku)


@router.get(
    "",
    response_model=list[SKURead],
    summary="List all SKUs",
)
async def list_skus(
    family: str | None = Query(None, description="Filter by family"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_session),
) -> list[SKURead]:
    """
    List all SKUs with optional filtering.

    Args:
        family: Optional family filter
        limit: Maximum results to return
        offset: Pagination offset
        session: Database session

    Returns:
        List of SKUs
    """
    query = select(SKU).order_by(SKU.family, SKU.model_name, SKU.year)

    if family:
        query = query.where(SKU.family == family)

    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    skus = result.scalars().all()
    return [SKURead.model_validate(sku) for sku in skus]


@router.get(
    "/{sku_id}",
    response_model=SKURead,
    summary="Get a SKU by ID",
)
async def get_sku(sku_id: UUID, session: AsyncSession = Depends(get_session)) -> SKURead:
    """
    Get a SKU by its ID.

    Args:
        sku_id: SKU UUID
        session: Database session

    Returns:
        SKU details

    Raises:
        HTTPException: If SKU not found
    """
    sku = await session.get(SKU, sku_id)
    if not sku:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU not found",
        )
    return SKURead.model_validate(sku)


@router.get(
    "/lookup/serial",
    response_model=SKULookupResponse,
    responses={
        404: {"model": SKULookupError, "description": "Serial prefix not found"},
    },
    summary="Look up SKU by serial number prefix",
)
async def lookup_sku_by_serial(
    serial: str = Query(..., min_length=1, max_length=100, description="Serial number to look up"),
    session: AsyncSession = Depends(get_session),
) -> SKULookupResponse:
    """
    Look up a SKU by serial number prefix.

    Matches the longest prefix first. If no prefix matches, returns 404 with
    error code 'manual_selection_required'.

    Args:
        serial: Serial number to look up
        session: Database session

    Returns:
        SKU and matched prefix

    Raises:
        HTTPException: If no matching prefix found
    """
    # Try to find the longest matching prefix
    # We check prefixes from longest to shortest
    for i in range(len(serial), 0, -1):
        prefix = serial[:i]
        result = await session.execute(
            select(SerialPrefix)
            .options(selectinload(SerialPrefix.sku))
            .where(SerialPrefix.prefix == prefix)
        )
        serial_prefix = result.scalar_one_or_none()
        if serial_prefix:
            return SKULookupResponse(
                sku=SKURead.model_validate(serial_prefix.sku),
                matched_prefix=prefix,
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=SKULookupError(
            message="No matching SKU found for serial prefix. Manual selection required.",
            serial=serial,
        ).model_dump(),
    )


@router.post(
    "/serial-prefixes",
    response_model=SerialPrefixRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a serial prefix mapping",
)
async def create_serial_prefix(
    prefix_data: SerialPrefixCreate, session: AsyncSession = Depends(get_session)
) -> SerialPrefixRead:
    """
    Create a new serial prefix to SKU mapping.

    Args:
        prefix_data: Serial prefix data
        session: Database session

    Returns:
        Created serial prefix

    Raises:
        HTTPException: If SKU not found or prefix already exists
    """
    # Verify SKU exists
    sku = await session.get(SKU, prefix_data.sku_id)
    if not sku:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referenced SKU not found",
        )

    # Check for existing prefix
    existing = await session.execute(
        select(SerialPrefix).where(SerialPrefix.prefix == prefix_data.prefix)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Serial prefix already exists",
        )

    prefix = SerialPrefix(
        prefix=prefix_data.prefix,
        sku_id=prefix_data.sku_id,
        source=prefix_data.source,
        as_of=prefix_data.as_of,
    )
    session.add(prefix)
    await session.flush()
    await session.refresh(prefix)
    return SerialPrefixRead.model_validate(prefix)


@router.get(
    "/serial-prefixes",
    response_model=list[SerialPrefixRead],
    summary="List all serial prefixes",
)
async def list_serial_prefixes(
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_session),
) -> list[SerialPrefixRead]:
    """
    List all serial prefix mappings.

    Args:
        limit: Maximum results to return
        offset: Pagination offset
        session: Database session

    Returns:
        List of serial prefixes
    """
    result = await session.execute(
        select(SerialPrefix)
        .options(selectinload(SerialPrefix.sku))
        .order_by(SerialPrefix.prefix)
        .limit(limit)
        .offset(offset)
    )
    prefixes = result.scalars().all()
    return [SerialPrefixRead.model_validate(p) for p in prefixes]
