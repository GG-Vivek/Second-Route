"""
Data ownership tools for Phase 7 (F7.6).

Export and delete data per tenant, with an audit record of every deletion.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, UTC
from typing import Any, Optional, Sequence
from uuid import UUID

import structlog
from pydantic import BaseModel, ConfigDict

logger = structlog.get_logger(__name__)


@dataclass
class DeletionRecord:
    """Record of a tenant data deletion.

    Attributes:
        org_id: The tenant whose data was deleted.
        deleted_at: Timestamp of the deletion.
        units_deleted: Number of units deleted.
        inspections_deleted: Number of inspections deleted.
        photos_deleted: Number of photos deleted.
        decisions_deleted: Number of decisions deleted.
        audit_logs_deleted: Number of audit log rows deleted.
        price_observations_deleted: Number of price observations deleted.
        cost_tables_deleted: Number of cost table rows deleted.
        deleted_by: Who performed the deletion.
        reason: Reason for the deletion.
    """

    org_id: UUID
    deleted_at: datetime
    units_deleted: int = 0
    inspections_deleted: int = 0
    photos_deleted: int = 0
    decisions_deleted: int = 0
    audit_logs_deleted: int = 0
    price_observations_deleted: int = 0
    cost_tables_deleted: int = 0
    deleted_by: str = "admin"
    reason: str = ""

    @property
    def total_rows_deleted(self) -> int:
        return (
            self.units_deleted
            + self.inspections_deleted
            + self.photos_deleted
            + self.decisions_deleted
            + self.audit_logs_deleted
            + self.price_observations_deleted
            + self.cost_tables_deleted
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "org_id": str(self.org_id),
            "deleted_at": self.deleted_at.isoformat(),
            "units_deleted": self.units_deleted,
            "inspections_deleted": self.inspections_deleted,
            "photos_deleted": self.photos_deleted,
            "decisions_deleted": self.decisions_deleted,
            "audit_logs_deleted": self.audit_logs_deleted,
            "price_observations_deleted": self.price_observations_deleted,
            "cost_tables_deleted": self.cost_tables_deleted,
            "total_rows_deleted": self.total_rows_deleted,
            "deleted_by": self.deleted_by,
            "reason": self.reason,
        }


class DataExport:
    """A tenant data export.

    Attributes:
        org_id: The tenant the data belongs to.
        generated_at: Timestamp of the export.
        tables: Dictionary of table name -> list of rows.
        row_count: Total number of rows exported.
    """

    def __init__(self, org_id: UUID) -> None:
        self.org_id = org_id
        self.generated_at = datetime.now(UTC)
        self.tables: dict[str, list[dict[str, Any]]] = {}

    def add_table(self, table_name: str, rows: list[dict[str, Any]]) -> None:
        """Add rows for a table to the export."""
        self.tables[table_name] = rows

    @property
    def row_count(self) -> int:
        return sum(len(rows) for rows in self.tables.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "org_id": str(self.org_id),
            "generated_at": self.generated_at.isoformat(),
            "tables": self.tables,
            "row_count": self.row_count,
        }

    def to_json(self) -> str:
        """Serialize the export to JSON."""
        return json.dumps(self.to_dict(), indent=2, default=str)

    def to_csv(self, table_name: str) -> str:
        """Serialize one table of the export to CSV.

        Args:
            table_name: Name of the table to serialize.

        Returns:
            CSV text (empty string if the table has no rows).
        """
        rows = self.tables.get(table_name, [])
        if not rows:
            return ""

        output = io.StringIO()
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _stringify(v) for k, v in row.items()})
        return output.getvalue()

    def to_csv_bundle(self) -> dict[str, str]:
        """Serialize every table to CSV.

        Returns:
            Dictionary of table name -> CSV text.
        """
        return {name: self.to_csv(name) for name in self.tables}


def _stringify(value: Any) -> str:
    """Convert a value to a CSV-safe string."""
    if value is None:
        return ""
    if isinstance(value, (datetime, UUID)):
        return str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return str(value)


class DataOwnershipService:
    """Service for tenant data export and deletion.

    Handles the right-to-export and right-to-delete obligations. Every
    deletion leaves an audit record.
    """

    def __init__(self) -> None:
        self._deletion_records: list[DeletionRecord] = []

    async def export_tenant_data(
        self,
        session: Any,
        org_id: UUID,
    ) -> DataExport:
        """Export all data for a tenant.

        Args:
            session: Database session.
            org_id: The tenant to export.

        Returns:
            DataExport with every table that has rows for this tenant.
        """
        from sqlalchemy import select

        from secondroute.costs.models import CostTable
        from secondroute.decision.models import Decision
        from secondroute.feedback.models import AuditLog
        from secondroute.identity.models import SKU
        from secondroute.intake.models import Inspection, Photo, Unit
        from secondroute.pricing.models import PriceObservation

        export = DataExport(org_id=org_id)

        # Units
        result = await session.execute(select(Unit).where(Unit.org_id == org_id))
        units = result.scalars().all()
        export.add_table("units", [_unit_to_row(u) for u in units])

        # Inspections (via units)
        unit_ids = [u.id for u in units]
        if unit_ids:
            result = await session.execute(
                select(Inspection).where(Inspection.unit_id.in_(unit_ids))
            )
            inspections = result.scalars().all()
            export.add_table("inspections", [_inspection_to_row(i) for i in inspections])

            result = await session.execute(select(Photo).where(Photo.unit_id.in_(unit_ids)))
            photos = result.scalars().all()
            export.add_table("photos", [_photo_to_row(p) for p in photos])

            result = await session.execute(select(Decision).where(Decision.unit_id.in_(unit_ids)))
            decisions = result.scalars().all()
            export.add_table("decisions", [_decision_to_row(d) for d in decisions])

        # Price observations
        result = await session.execute(
            select(PriceObservation).where(PriceObservation.org_id == org_id)
        )
        observations = result.scalars().all()
        export.add_table("price_observations", [_observation_to_row(o) for o in observations])

        # Cost tables
        result = await session.execute(select(CostTable).where(CostTable.org_id == org_id))
        cost_tables = result.scalars().all()
        export.add_table("cost_tables", [_cost_table_to_row(c) for c in cost_tables])

        # Audit logs
        result = await session.execute(select(AuditLog).where(AuditLog.org_id == org_id))
        audit_logs = result.scalars().all()
        export.add_table("audit_log", [_audit_log_to_row(a) for a in audit_logs])

        logger.info(
            "tenant_data_exported",
            org_id=str(org_id),
            row_count=export.row_count,
        )
        return export

    async def delete_tenant_data(
        self,
        session: Any,
        org_id: UUID,
        deleted_by: str = "admin",
        reason: str = "",
    ) -> DeletionRecord:
        """Delete all data for a tenant.

        An audit record of the deletion is kept after the tenant's data is gone.

        Args:
            session: Database session.
            org_id: The tenant whose data is deleted.
            deleted_by: Who performed the deletion.
            reason: Reason for the deletion.

        Returns:
            DeletionRecord with counts of everything removed.
        """
        from sqlalchemy import delete, select

        from secondroute.costs.models import CostTable
        from secondroute.decision.models import Decision
        from secondroute.feedback.models import AuditLog
        from secondroute.intake.models import Inspection, Photo, Unit
        from secondroute.pricing.models import PriceObservation

        record = DeletionRecord(
            org_id=org_id,
            deleted_at=datetime.now(UTC),
            deleted_by=deleted_by,
            reason=reason,
        )

        # Units for this tenant
        result = await session.execute(select(Unit).where(Unit.org_id == org_id))
        units = result.scalars().all()
        unit_ids = [u.id for u in units]

        if unit_ids:
            # Photos
            result = await session.execute(select(Photo).where(Photo.unit_id.in_(unit_ids)))
            photos = result.scalars().all()
            record.photos_deleted = len(photos)
            await session.execute(delete(Photo).where(Photo.unit_id.in_(unit_ids)))

            # Inspections
            result = await session.execute(
                select(Inspection).where(Inspection.unit_id.in_(unit_ids))
            )
            inspections = result.scalars().all()
            record.inspections_deleted = len(inspections)
            await session.execute(delete(Inspection).where(Inspection.unit_id.in_(unit_ids)))

            # Decisions
            result = await session.execute(select(Decision).where(Decision.unit_id.in_(unit_ids)))
            decisions = result.scalars().all()
            record.decisions_deleted = len(decisions)
            await session.execute(delete(Decision).where(Decision.unit_id.in_(unit_ids)))

            # Units
            record.units_deleted = len(units)
            await session.execute(delete(Unit).where(Unit.org_id == org_id))

        # Price observations
        result = await session.execute(
            select(PriceObservation).where(PriceObservation.org_id == org_id)
        )
        observations = result.scalars().all()
        record.price_observations_deleted = len(observations)
        await session.execute(delete(PriceObservation).where(PriceObservation.org_id == org_id))

        # Cost tables
        result = await session.execute(select(CostTable).where(CostTable.org_id == org_id))
        cost_tables = result.scalars().all()
        record.cost_tables_deleted = len(cost_tables)
        await session.execute(delete(CostTable).where(CostTable.org_id == org_id))

        # Audit logs for this tenant
        result = await session.execute(select(AuditLog).where(AuditLog.org_id == org_id))
        audit_logs = result.scalars().all()
        record.audit_logs_deleted = len(audit_logs)
        await session.execute(delete(AuditLog).where(AuditLog.org_id == org_id))

        # Keep the audit record of the deletion itself
        self._deletion_records.append(record)

        logger.info(
            "tenant_data_deleted",
            org_id=str(org_id),
            total_rows_deleted=record.total_rows_deleted,
            deleted_by=deleted_by,
            reason=reason,
        )
        return record

    def get_deletion_records(self, org_id: UUID | None = None) -> list[DeletionRecord]:
        """Get deletion records, optionally filtered by tenant."""
        if org_id is None:
            return list(self._deletion_records)
        return [r for r in self._deletion_records if r.org_id == org_id]

    def clear_records(self) -> None:
        """Clear the deletion records (used in tests)."""
        self._deletion_records.clear()


def _unit_to_row(unit: Any) -> dict[str, Any]:
    return {
        "id": str(unit.id),
        "sku_id": str(unit.sku_id),
        "serial": unit.serial,
        "received_at": unit.received_at,
        "return_reason_code": unit.return_reason_code.value
        if hasattr(unit.return_reason_code, "value")
        else str(unit.return_reason_code),
        "order_channel": unit.order_channel.value
        if hasattr(unit.order_channel, "value")
        else str(unit.order_channel),
        "status": unit.status.value if hasattr(unit.status, "value") else str(unit.status),
    }


def _inspection_to_row(inspection: Any) -> dict[str, Any]:
    return {
        "id": str(inspection.id),
        "unit_id": str(inspection.unit_id),
        "battery_health_pct": inspection.battery_health_pct,
        "battery_cycles": inspection.battery_cycles,
        "cosmetic_grade": inspection.cosmetic_grade,
        "functional_tests_json": inspection.functional_tests_json,
        "activation_lock": inspection.activation_lock,
        "accessories_json": inspection.accessories_json,
        "notes": inspection.notes,
        "created_at": inspection.created_at,
    }


def _photo_to_row(photo: Any) -> dict[str, Any]:
    return {
        "id": str(photo.id),
        "unit_id": str(photo.unit_id),
        "inspection_id": str(photo.inspection_id),
        "storage_path": photo.storage_path,
        "exif_stripped": photo.exif_stripped,
        "created_at": photo.created_at,
    }


def _decision_to_row(decision: Any) -> dict[str, Any]:
    return {
        "id": str(decision.id),
        "unit_id": str(decision.unit_id),
        "created_at": decision.created_at,
        "model_version": decision.model_version,
        "risk_profile": decision.risk_profile,
        "recommended_channel": decision.recommended_channel,
        "confidence": decision.confidence,
        "fallback_used": decision.fallback_used,
        "input_snapshot_hash": decision.input_snapshot_hash,
    }


def _observation_to_row(observation: Any) -> dict[str, Any]:
    return {
        "id": str(observation.id),
        "sku_id": str(observation.sku_id),
        "grade": observation.grade,
        "channel": observation.channel,
        "price": observation.price,
        "currency": observation.currency,
        "source": observation.source,
        "observed_at": observation.observed_at,
        "weight": observation.weight,
        "is_synthetic": observation.is_synthetic,
    }


def _cost_table_to_row(cost_table: Any) -> dict[str, Any]:
    return {
        "id": str(cost_table.id),
        "kind": cost_table.kind,
        "key": cost_table.key,
        "value": cost_table.value,
        "currency": cost_table.currency,
        "source": cost_table.source,
        "as_of": cost_table.as_of,
    }


def _audit_log_to_row(audit_log: Any) -> dict[str, Any]:
    return {
        "id": str(audit_log.id),
        "actor": audit_log.actor,
        "action": audit_log.action.value
        if hasattr(audit_log.action, "value")
        else str(audit_log.action),
        "entity": audit_log.entity,
        "entity_id": audit_log.entity_id,
        "payload_json": audit_log.payload_json,
        "created_at": audit_log.created_at,
    }
