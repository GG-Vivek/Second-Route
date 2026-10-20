"""
Audit log event listeners for Phase 1.

Automatically logs all CREATE, UPDATE, DELETE operations to audit_log table.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import event, inspect
from sqlalchemy.orm import Mapper, Session

from secondroute.core.db import Base
from secondroute.feedback.models import AuditLog, AuditAction
from secondroute.identity.models import SKU, SerialPrefix
from secondroute.intake.models import Unit, Inspection, Photo

#: Key under which the pending audit entries are stashed on the session.
AUDIT_PENDING_KEY = "_secondroute_pending_audits"


# Entities to audit - maps model class to entity name
AUDITED_MODELS: dict[type[Any], str] = {
    SKU: "skus",
    SerialPrefix: "serial_prefixes",
    Unit: "units",
    Inspection: "inspections",
    Photo: "photos",
}

# Fields to exclude from audit payload (sensitive or large)
EXCLUDED_FIELDS = {
    "password",
    "hashed_password",
    "secret",
    "token",
    "api_key",
}


def get_model_changes(model_class: type, instance: Any, session: Session) -> dict[str, Any]:
    """
    Get the changed attributes for a model instance.

    Returns a dict with 'before' and 'after' states.
    """
    inspector = inspect(instance)
    changes: dict[str, Any] = {}

    # Get all column attributes
    for attr in inspector.attrs:
        if attr.key in EXCLUDED_FIELDS:
            continue

        if attr.key == "id" and isinstance(getattr(instance, attr.key, None), uuid.UUID):
            continue  # Don't audit ID changes

        history = inspector.get_history(attr.key, True)
        if history.has_changes():
            # Get the old value (deleted) and new value (added)
            old_value = history.deleted[0] if history.deleted else None
            new_value = history.added[0] if history.added else None

            # Convert UUID to string for JSON serialization
            if isinstance(old_value, uuid.UUID):
                old_value = str(old_value)
            if isinstance(new_value, uuid.UUID):
                new_value = str(new_value)
            if isinstance(old_value, datetime):
                old_value = old_value.isoformat()
            if isinstance(new_value, datetime):
                new_value = new_value.isoformat()
            if isinstance(old_value, date):
                old_value = old_value.isoformat()
            if isinstance(new_value, date):
                new_value = new_value.isoformat()

            changes[attr.key] = {"before": old_value, "after": new_value}

    return changes


def get_full_payload(model_class: type, instance: Any) -> dict[str, Any]:
    """
    Get the full payload of a model instance for audit logging.
    """
    inspector = inspect(instance)
    payload: dict[str, Any] = {}

    for attr in inspector.attrs:
        if attr.key in EXCLUDED_FIELDS:
            continue

        value = getattr(instance, attr.key, None)

        # Convert UUID to string for JSON serialization
        if isinstance(value, uuid.UUID):
            value = str(value)
        elif isinstance(value, (datetime, date)):
            value = value.isoformat()

        payload[attr.key] = value

    return payload


def create_audit_entry(
    session: Session,
    model_class: type,
    instance: Any,
    action: AuditAction,
    actor: str = "anonymous",
    org_id: Optional[uuid.UUID] = None,
) -> Optional[AuditLog]:
    """
    Create an audit log entry for a model instance.

    Returns the created AuditLog instance or None if not audited.
    """
    entity_name = AUDITED_MODELS.get(model_class)
    if not entity_name:
        return None

    entity_id = getattr(instance, "id", None)
    if entity_id is None:
        return None

    entity_id_str = str(entity_id)

    # Get org_id from instance if available
    if org_id is None and hasattr(instance, "org_id"):
        org_id = instance.org_id

    if action == AuditAction.UPDATE:
        changes = get_model_changes(model_class, instance, session)
        if not changes:
            return None  # No actual changes
        payload = {
            "action": action.value,
            "changes": changes,
        }
    else:
        payload = {
            "action": action.value,
            "data": get_full_payload(model_class, instance),
        }

    audit_entry = AuditLog(
        org_id=org_id,
        actor=actor,
        action=action,
        entity=entity_name,
        entity_id=entity_id_str,
        payload_json=payload,
        created_at=datetime.utcnow(),
    )

    return audit_entry


@dataclass(frozen=True)
class PendingAudit:
    """An audit entry captured before the flush and written after it.

    The payload is captured in ``before_flush`` because that is the only
    point where the attribute history of an update is still readable. The row
    itself is written in ``after_flush``, where the primary key of a newly
    inserted object has been assigned.
    """

    model_class: type
    instance: Any
    action: AuditAction
    entity_name: str
    payload: dict[str, Any]


def capture_pending_audits(session: Session) -> list[PendingAudit]:
    """Collect the audit entries implied by the session's pending changes.

    Args:
        session: The session about to be flushed.

    Returns:
        One entry per audited create, update and delete.
    """
    pending: list[PendingAudit] = []

    for instance in list(session.new):
        model_class = type(instance)
        entity_name = AUDITED_MODELS.get(model_class)
        if entity_name is None:
            continue
        pending.append(
            PendingAudit(
                model_class=model_class,
                instance=instance,
                action=AuditAction.CREATE,
                entity_name=entity_name,
                payload={
                    "action": AuditAction.CREATE.value,
                    "data": get_full_payload(model_class, instance),
                },
            )
        )

    for instance in list(session.dirty):
        model_class = type(instance)
        entity_name = AUDITED_MODELS.get(model_class)
        if entity_name is None:
            continue
        if not session.is_modified(instance, include_collections=False):
            continue
        changes = get_model_changes(model_class, instance, session)
        if not changes:
            continue
        pending.append(
            PendingAudit(
                model_class=model_class,
                instance=instance,
                action=AuditAction.UPDATE,
                entity_name=entity_name,
                payload={
                    "action": AuditAction.UPDATE.value,
                    "changes": changes,
                },
            )
        )

    for instance in list(session.deleted):
        model_class = type(instance)
        entity_name = AUDITED_MODELS.get(model_class)
        if entity_name is None:
            continue
        pending.append(
            PendingAudit(
                model_class=model_class,
                instance=instance,
                action=AuditAction.DELETE,
                entity_name=entity_name,
                payload={
                    "action": AuditAction.DELETE.value,
                    "data": get_full_payload(model_class, instance),
                },
            )
        )

    return pending


def _capture_audits(session: Session, flush_context: Any, instances: Any) -> None:
    """Capture the pending audit entries before the flush."""
    pending = capture_pending_audits(session)
    if pending:
        existing = session.info.get(AUDIT_PENDING_KEY, [])
        session.info[AUDIT_PENDING_KEY] = [*existing, *pending]


def _write_audits(session: Session, flush_context: Any) -> None:
    """Write the audit rows once the primary keys are assigned."""
    pending: list[PendingAudit] = session.info.pop(AUDIT_PENDING_KEY, [])
    for item in pending:
        entry = _build_audit_row(item)
        if entry is not None:
            session.add(entry)


def setup_audit_listeners() -> None:
    """
    Set up SQLAlchemy event listeners for automatic audit logging.

    The listeners are attached to the **Session**, not to the mapped classes.
    A mapper-level ``after_insert`` receives only a connection, so the audit
    row would have to be written through a second session. That audit row
    would then sit outside the caller's transaction: it would not be rolled
    back with the business change, and a failed request would still leave an
    audit trail for a change that never happened.

    Session-level ``before_flush``/``after_flush`` keeps the audit row in the
    same transaction as the change it describes, which is the only correct
    behaviour for an audit log.

    Registration is idempotent - calling it twice does not double every
    audit row.
    """
    if not event.contains(Session, "before_flush", _capture_audits):
        event.listen(Session, "before_flush", _capture_audits)
    if not event.contains(Session, "after_flush", _write_audits):
        event.listen(Session, "after_flush", _write_audits)


def _build_audit_row(item: PendingAudit) -> Optional[AuditLog]:
    """Turn a captured audit entry into a persistable row.

    Args:
        item: The captured entry.

    Returns:
        The row, or ``None`` when the instance has no primary key yet.
    """
    entity_id = getattr(item.instance, "id", None)
    if entity_id is None:
        return None

    org_id = getattr(item.instance, "org_id", None)

    return AuditLog(
        org_id=org_id,
        actor="anonymous",
        action=item.action,
        entity=item.entity_name,
        entity_id=str(entity_id),
        payload_json=item.payload,
        created_at=datetime.utcnow(),
    )


# Don't initialize at import time - call setup_audit_listeners() explicitly after all models are loaded
