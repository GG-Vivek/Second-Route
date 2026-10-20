"""
Intake API routes for Phase 1.

Provides unit intake and inspection record endpoints.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from secondroute.core.db import current_org_uuid, get_session
from secondroute.intake.models import (
    Unit,
    Inspection,
    Photo,
    UnitStatus,
    ReturnReasonCode,
    OrderChannel,
)
from secondroute.intake.schemas import (
    UnitCreate,
    UnitRead,
    UnitDetailRead,
    InspectionCreate,
    InspectionRead,
    PhotoCreate,
    PhotoRead,
    UnitStatusUpdate,
)

router = APIRouter(prefix="/units", tags=["Unit Intake"])


@router.post(
    "",
    response_model=UnitRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new unit intake record",
)
async def create_unit(
    unit_data: UnitCreate, session: AsyncSession = Depends(get_session)
) -> UnitRead:
    """
    Create a new unit intake record.

    Args:
        unit_data: Unit data including SKU, optional serial, return reason, and order channel
        session: Database session

    Returns:
        Created unit with status 'received'

    Raises:
        HTTPException: If SKU not found or invalid return reason code
    """
    # Verify SKU exists
    from secondroute.identity.models import SKU

    sku = await session.get(SKU, unit_data.sku_id)
    if not sku:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referenced SKU not found",
        )

    # Create unit
    unit = Unit(
        sku_id=unit_data.sku_id,
        serial=unit_data.serial,
        return_reason_code=unit_data.return_reason_code,
        order_channel=unit_data.order_channel,
        status=UnitStatus.RECEIVED,
        # The unit belongs to the organisation the request acts for. The
        # row-level security policy checks it on the way in, so a request
        # that names no organisation is refused by the database rather
        # than quietly writing a row nobody owns.
        org_id=current_org_uuid(),
    )
    session.add(unit)
    await session.flush()
    await session.refresh(unit)
    return UnitRead.model_validate(unit)


@router.get(
    "",
    response_model=list[UnitRead],
    summary="List units",
)
async def list_units(
    status_filter: Optional[UnitStatus] = Query(
        None, alias="status", description="Filter by status"
    ),
    sku_id: Optional[UUID] = Query(None, description="Filter by SKU"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_session),
) -> list[UnitRead]:
    """
    List units with optional filtering.

    Args:
        status_filter: Optional status filter
        sku_id: Optional SKU filter
        limit: Maximum results to return
        offset: Pagination offset
        session: Database session

    Returns:
        List of units
    """
    query = select(Unit).order_by(Unit.received_at.desc())

    if status_filter:
        query = query.where(Unit.status == status_filter)

    if sku_id:
        query = query.where(Unit.sku_id == sku_id)

    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    units = result.scalars().all()
    return [UnitRead.model_validate(unit) for unit in units]


@router.get(
    "/{unit_id}",
    response_model=UnitDetailRead,
    summary="Get unit detail with inspections and photos",
)
async def get_unit(unit_id: UUID, session: AsyncSession = Depends(get_session)) -> UnitDetailRead:
    """
    Get a unit by ID with its inspections and photos.

    Args:
        unit_id: Unit UUID
        session: Database session

    Returns:
        Unit with inspections and photos

    Raises:
        HTTPException: If unit not found
    """
    result = await session.execute(
        select(Unit)
        .options(
            selectinload(Unit.inspections).selectinload(Inspection.photos),
            selectinload(Unit.photos),
        )
        .where(Unit.id == unit_id)
    )
    unit = result.scalar_one_or_none()

    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found",
        )

    return UnitDetailRead.model_validate(unit)


@router.patch(
    "/{unit_id}/status",
    response_model=UnitRead,
    summary="Update unit status",
)
async def update_unit_status(
    unit_id: UUID, status_update: UnitStatusUpdate, session: AsyncSession = Depends(get_session)
) -> UnitRead:
    """
    Update unit status.

    Args:
        unit_id: Unit UUID
        status_update: New status
        session: Database session

    Returns:
        Updated unit

    Raises:
        HTTPException: If unit not found
    """
    unit = await session.get(Unit, unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found",
        )

    unit.status = status_update.status  # type: ignore[assignment]
    await session.flush()
    await session.refresh(unit)
    return UnitRead.model_validate(unit)


@router.post(
    "/{unit_id}/inspections",
    response_model=InspectionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an inspection record for a unit",
)
async def create_inspection(
    unit_id: UUID, inspection_data: InspectionCreate, session: AsyncSession = Depends(get_session)
) -> InspectionRead:
    """
    Create an inspection record for a unit.

    Inspections are append-only. Multiple inspections allowed,
    latest one is considered current. Status moves to 'inspected'.

    Args:
        unit_id: Unit UUID
        inspection_data: Inspection data
        session: Database session

    Returns:
        Created inspection

    Raises:
        HTTPException: If unit not found or battery health invalid
    """
    unit = await session.get(Unit, unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found",
        )

    # Validate battery health range (0-100)
    battery_health = float(inspection_data.battery_health_pct)
    if not 0 <= battery_health <= 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Battery health must be between 0 and 100",
        )

    import json

    # Create inspection
    inspection = Inspection(
        unit_id=unit_id,
        battery_health_pct=inspection_data.battery_health_pct,
        battery_cycles=inspection_data.battery_cycles,
        cosmetic_grade=inspection_data.cosmetic_grade,
        functional_tests_json=json.dumps(inspection_data.functional_tests_json),
        activation_lock=inspection_data.activation_lock,
        accessories_json=json.dumps(inspection_data.accessories_json),
        notes=inspection_data.notes,
        offline_created=inspection_data.offline_created,
    )
    session.add(inspection)

    # Update unit status to inspected
    unit.status = UnitStatus.INSPECTED  # type: ignore[assignment]

    await session.flush()
    await session.refresh(inspection)
    return InspectionRead.model_validate(inspection)


@router.get(
    "/{unit_id}/inspections",
    response_model=list[InspectionRead],
    summary="List inspections for a unit",
)
async def list_inspections(
    unit_id: UUID, session: AsyncSession = Depends(get_session)
) -> list[InspectionRead]:
    """
    List all inspections for a unit (append-only history).

    Args:
        unit_id: Unit UUID
        session: Database session

    Returns:
        List of inspections ordered by creation date

    Raises:
        HTTPException: If unit not found
    """
    unit = await session.get(Unit, unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found",
        )

    result = await session.execute(
        select(Inspection).where(Inspection.unit_id == unit_id).order_by(Inspection.created_at)
    )
    inspections = result.scalars().all()
    return [InspectionRead.model_validate(i) for i in inspections]


@router.post(
    "/{unit_id}/photos",
    response_model=PhotoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a photo record for a unit inspection",
)
async def create_photo(
    unit_id: UUID, photo_data: PhotoCreate, session: AsyncSession = Depends(get_session)
) -> PhotoRead:
    """
    Create a photo record for a unit inspection.

    Args:
        unit_id: Unit UUID
        photo_data: Photo data
        session: Database session

    Returns:
        Created photo record

    Raises:
        HTTPException: If unit or inspection not found
    """
    unit = await session.get(Unit, unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found",
        )

    inspection = await session.get(Inspection, photo_data.inspection_id)
    if not inspection or inspection.unit_id != unit_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found for this unit",
        )

    photo = Photo(
        unit_id=unit_id,
        inspection_id=photo_data.inspection_id,
        storage_path=photo_data.storage_path,
        exif_stripped=str(photo_data.exif_stripped).lower(),
    )
    session.add(photo)
    await session.flush()
    await session.refresh(photo)
    return PhotoRead.model_validate(photo)


@router.get(
    "/{unit_id}/photos",
    response_model=list[PhotoRead],
    summary="List photos for a unit",
)
async def list_photos(
    unit_id: UUID, session: AsyncSession = Depends(get_session)
) -> list[PhotoRead]:
    """
    List all photos for a unit.

    Args:
        unit_id: Unit UUID
        session: Database session

    Returns:
        List of photos

    Raises:
        HTTPException: If unit not found
    """
    unit = await session.get(Unit, unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found",
        )

    result = await session.execute(
        select(Photo).where(Photo.unit_id == unit_id).order_by(Photo.created_at)
    )
    photos = result.scalars().all()
    return [PhotoRead.model_validate(p) for p in photos]
