"""
Audit log event listeners for Phase 1.

Automatically logs all CREATE, UPDATE, DELETE operations to audit_log table.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import event, insert, inspect
from sqlalchemy.orm import Mapper, Session

from secondroute.core.db import Base, get_current_actor
from secondroute.decision.models import Decision
from secondroute.feedback.models import AuditLog, AuditAction, Outcome, Override
from secondroute.identity.models import SKU, SerialPrefix
from secondroute.identity.organizations import Organization
from secondroute.intake.models import Unit, Inspection, Photo

#: Key under which the pending audit entries are stashed on the session.
AUDIT_PENDING_KEY = "_secondroute_pending_audits"


# Entities to audit - maps model class to entity name
#
# A decision is deliberately not in this list. The decision row is already
# append-only, and it carries the model version, the input snapshot hash
# and the whole input snapshot, so it is its own record of what the
# engine did and when. Auditing it would copy that snapshot into the
# audit log a second time, for no gain.
#
# An outcome is a different matter: it is a human asserting that a unit
# sold for a given price, and that assertion is exactly the kind of fact
# an audit trail has to carry.
AUDITED_MODELS: dict[type[Any], str] = {
    SKU: "skus",
    SerialPrefix: "serial_prefixes",
    Unit: "units",
    Inspection: "inspections",
    Photo: "photos",
    Override: "overrides",
    Outcome: "outcomes",
    Organization: "organizations",
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

    # Fall back to the org the instance belongs to, which for inspections
    # and photos is the org of their unit.
    if org_id is None:
        org_id = _resolve_org_id(session, instance)

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
    """Write the audit rows once the primary keys are assigned.

    The rows are written with a direct ``INSERT`` rather than
    ``session.add()``. ``add()`` would place the row in the session's
    identity map, and the flush that is currently in progress has already
    built its INSERT/UPDATE plan, so the row would only reach the database
    on a *later* flush. A caller that flushes without committing would
    therefore see no audit row at all, and a caller that commits would
    trigger a second flush to persist it.

    A direct ``INSERT`` issued from ``after_flush`` runs on the same
    connection and inside the same transaction as the change it describes,
    so the audit trail rolls back with the business change - which is the
    only correct behaviour for an audit log.
    """
    pending: list[PendingAudit] = session.info.pop(AUDIT_PENDING_KEY, [])
    if not pending:
        return

    rows: list[dict[str, Any]] = []
    for item in pending:
        values = _build_audit_values(item, session)
        if values is not None:
            rows.append(values)

    if not rows:
        return

    # ``no_autoflush`` prevents the INSERT from re-entering the flush
    # process, which would recurse forever.
    with session.no_autoflush:
        session.execute(insert(AuditLog), rows)


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


def _resolve_org_id(session: Session, instance: Any) -> Optional[uuid.UUID]:
    """The organisation an audited row belongs to.

    Most audited models carry ``org_id`` directly. The rest have to be
    reached through the record they belong to:

    - an organisation *is* an organisation, so its own id is the answer;
    - an inspection and a photo belong to a unit, and the unit carries the
      org;
    - an override belongs to a decision, and the decision carries the org.

    Resolving the org matters because the tenant-isolation policies check
    ``org_id`` on every write: an audit row with a null ``org_id`` would be
    rejected outright.

    Args:
        session: The session the audited object belongs to.
        instance: The audited object.

    Returns:
        The organisation's id, or ``None`` when it cannot be determined.
    """
    org_id: Optional[uuid.UUID] = getattr(instance, "org_id", None)
    if org_id is not None:
        return org_id

    if isinstance(instance, Organization):
        organization_id: Optional[uuid.UUID] = getattr(instance, "id", None)
        return organization_id

    unit_id: Optional[uuid.UUID] = getattr(instance, "unit_id", None)
    if unit_id is not None:
        # ``session.get`` answers from the identity map when the unit is
        # already loaded, and issues a single indexed SELECT otherwise. The
        # relationship is deliberately not used: touching it would trigger
        # a lazy load, which cannot run inside a flush.
        unit = session.get(Unit, unit_id)
        return getattr(unit, "org_id", None) if unit is not None else None

    decision_id: Optional[uuid.UUID] = getattr(instance, "decision_id", None)
    if decision_id is not None:
        decision = session.get(Decision, decision_id)
        return getattr(decision, "org_id", None) if decision is not None else None

    return None


def _build_audit_values(item: PendingAudit, session: Session) -> Optional[dict[str, Any]]:
    """Turn a captured audit entry into a column/value mapping.

    Args:
        item: The captured entry.
        session: The session the audited object belongs to.

    Returns:
        The column values, or ``None`` when the instance has no primary key
        yet.
    """
    entity_id = getattr(item.instance, "id", None)
    if entity_id is None:
        return None

    org_id = _resolve_org_id(session, item.instance)

    payload = item.payload
    if item.action is AuditAction.CREATE:
        # The column defaults - the identifier, the creation time, the
        # status - are applied during the flush. The payload was captured
        # before it, so it says that the record was created with no
        # identifier and no time. It is read again here, where the record
        # is whole.
        payload = {
            "action": AuditAction.CREATE.value,
            "data": get_full_payload(type(item.instance), item.instance),
        }

    return {
        "id": uuid.uuid4(),
        "org_id": org_id,
        "actor": get_current_actor(),
        "action": item.action.value,
        "entity": item.entity_name,
        "entity_id": str(entity_id),
        "payload_json": payload,
        "created_at": datetime.utcnow(),
    }


def _build_audit_row(item: PendingAudit, session: Session) -> Optional[AuditLog]:
    """Turn a captured audit entry into a persistable row.

    Args:
        item: The captured entry.
        session: The session the audited object belongs to.

    Returns:
        The row, or ``None`` when the instance has no primary key yet.
    """
    values = _build_audit_values(item, session)
    if values is None:
        return None

    return AuditLog(
        id=values["id"],
        org_id=values["org_id"],
        actor=values["actor"],
        action=AuditAction(values["action"]),
        entity=values["entity"],
        entity_id=values["entity_id"],
        payload_json=values["payload_json"],
        created_at=values["created_at"],
    )


# Don't initialize at import time - call setup_audit_listeners() explicitly after all models are loaded
