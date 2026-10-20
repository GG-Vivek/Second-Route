"""
Audit log API routes for Phase 1.

Provides read-only access to audit log entries.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.db import get_session
from secondroute.feedback.models import AuditLog, AuditAction
from secondroute.feedback.schemas import AuditLogRead

router = APIRouter(prefix="/audit-log", tags=["Audit Log"])


@router.get(
    "",
    response_model=list[AuditLogRead],
    summary="List audit log entries",
)
async def list_audit_logs(
    entity: Optional[str] = Query(
        None, description="Filter by entity type (e.g., 'units', 'inspections')"
    ),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    action: Optional[AuditAction] = Query(
        None, description="Filter by action (create, update, delete)"
    ),
    actor: Optional[str] = Query(None, description="Filter by actor"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_session),
) -> list[AuditLogRead]:
    """
    List audit log entries with optional filtering.

    Args:
        entity: Filter by entity type
        entity_id: Filter by entity ID
        action: Filter by action type
        actor: Filter by actor
        limit: Maximum results to return
        offset: Pagination offset
        session: Database session

    Returns:
        List of audit log entries ordered by creation date (newest first)
    """
    query = select(AuditLog).order_by(desc(AuditLog.created_at))

    if entity:
        query = query.where(AuditLog.entity == entity)

    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)

    if action:
        query = query.where(AuditLog.action == action)

    if actor:
        query = query.where(AuditLog.actor == actor)

    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    logs = result.scalars().all()
    return [AuditLogRead.model_validate(log) for log in logs]


@router.get(
    "/{log_id}",
    response_model=AuditLogRead,
    summary="Get audit log entry by ID",
)
async def get_audit_log(
    log_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> AuditLogRead:
    """
    Get an audit log entry by ID.

    Args:
        log_id: Audit log UUID
        session: Database session

    Returns:
        Audit log entry

    Raises:
        HTTPException: If not found
    """
    from fastapi import HTTPException

    log = await session.get(AuditLog, log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log entry not found",
        )
    return AuditLogRead.model_validate(log)
