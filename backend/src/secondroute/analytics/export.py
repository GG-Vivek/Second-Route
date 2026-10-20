"""
Data export for Phase 4 (F4.8).

The decisions, the overrides and the outcomes can be exported as CSV. Every
row carries a hash of its own contents, so an export can be re-imported and
checked: the row count and the hashes have to come back the same.

The export never mixes synthetic and real data silently. Every row says
which kind of data it is.
"""

from __future__ import annotations

import csv
import hashlib
import io
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Optional, Sequence

import structlog

logger = structlog.get_logger(__name__)

#: The separator used when the row contents are hashed.
HASH_SEPARATOR = "\x1f"


@dataclass(frozen=True)
class ExportEntity:
    """One kind of row that can be exported.

    Attributes:
        name: The name of the entity, as it appears in the URL.
        columns: The columns of the CSV, in order.
        hashed_columns: The columns the row hash covers. The derived
            columns are left out, so a hash only depends on the data that
            was stored.
    """

    name: str
    columns: tuple[str, ...]
    hashed_columns: tuple[str, ...]

    @property
    def hash_column(self) -> str:
        """The name of the column that holds the row hash."""
        return "row_hash"


DECISIONS = ExportEntity(
    name="decisions",
    columns=(
        "decision_id",
        "unit_id",
        "created_at",
        "model_version",
        "risk_profile",
        "recommended_channel",
        "confidence",
        "fallback_used",
        "input_snapshot_hash",
        "calibration_version",
        "data_kind",
    ),
    hashed_columns=(
        "decision_id",
        "unit_id",
        "created_at",
        "model_version",
        "risk_profile",
        "recommended_channel",
        "confidence",
        "fallback_used",
        "input_snapshot_hash",
        "calibration_version",
        "data_kind",
    ),
)

OVERRIDES = ExportEntity(
    name="overrides",
    columns=(
        "override_id",
        "decision_id",
        "created_at",
        "chosen_channel",
        "reason_text",
        "data_kind",
    ),
    hashed_columns=(
        "override_id",
        "decision_id",
        "created_at",
        "chosen_channel",
        "reason_text",
        "data_kind",
    ),
)

OUTCOMES = ExportEntity(
    name="outcomes",
    columns=(
        "outcome_id",
        "unit_id",
        "decision_id",
        "recorded_at",
        "channel_taken",
        "sale_price",
        "fees_actual",
        "repair_cost_actual",
        "logistics_actual",
        "days_to_disposition",
        "final_status",
        "net",
        "data_kind",
    ),
    hashed_columns=(
        "outcome_id",
        "unit_id",
        "decision_id",
        "recorded_at",
        "channel_taken",
        "sale_price",
        "fees_actual",
        "repair_cost_actual",
        "logistics_actual",
        "days_to_disposition",
        "final_status",
        "data_kind",
    ),
)

ENTITIES = {entity.name: entity for entity in (DECISIONS, OVERRIDES, OUTCOMES)}


def format_value(value: Any) -> str:
    """Render one value the way the export stores it.

    Args:
        value: The value.

    Returns:
        The rendered value.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.6f}"
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def row_hash(entity: ExportEntity, row: dict[str, str]) -> str:
    """Compute the hash of one exported row.

    The hash covers the stored columns of the row, so it can be recomputed
    from the CSV alone.

    Args:
        entity: The kind of row.
        row: The row, keyed by column name.

    Returns:
        The hex digest of the row.
    """
    payload = HASH_SEPARATOR.join(
        f"{column}={row.get(column, '')}" for column in entity.hashed_columns
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def combined_hash(hashes: Sequence[str]) -> str:
    """Combine the row hashes of an export into one.

    Args:
        hashes: The row hashes, in the order they were exported.

    Returns:
        The hex digest of the whole export.
    """
    return hashlib.sha256(HASH_SEPARATOR.join(hashes).encode("utf-8")).hexdigest()


def write_csv(entity: ExportEntity, rows: Iterable[dict[str, str]]) -> str:
    """Render the rows of an export as CSV.

    Every row gets its hash column filled in.

    Args:
        entity: The kind of row.
        rows: The rows, keyed by column name.

    Returns:
        The CSV, with a header line.
    """
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[*entity.columns, entity.hash_column],
        lineterminator="\n",
        extrasaction="ignore",
    )
    writer.writeheader()
    for row in rows:
        rendered = {column: format_value(row.get(column)) for column in entity.columns}
        rendered[entity.hash_column] = row_hash(entity, rendered)
        writer.writerow(rendered)
    return buffer.getvalue()


@dataclass
class ImportResult:
    """What a re-import of an export found.

    Attributes:
        entity: The kind of row that was imported.
        rows: How many rows the export held.
        matching_hashes: How many rows had a hash that could be recomputed
            and matched.
        mismatching_hashes: How many rows had a hash that did not match.
        hash: The combined hash of the rows.
    """

    entity: str
    rows: int = 0
    matching_hashes: int = 0
    mismatching_hashes: int = 0
    hash: str = ""

    @property
    def round_trips(self) -> bool:
        """Whether the export came back exactly as it went out."""
        return self.rows > 0 and self.matching_hashes == self.rows

    def to_dict(self) -> dict[str, Any]:
        """Render the result for the API response.

        Returns:
            The result.
        """
        return {
            "entity": self.entity,
            "rows": self.rows,
            "matching_hashes": self.matching_hashes,
            "mismatching_hashes": self.mismatching_hashes,
            "hash": self.hash,
            "round_trips": self.round_trips,
        }


def read_csv(entity: ExportEntity, raw: str) -> ImportResult:
    """Read an export back and check that it round-trips.

    The rows are not written to the database: the decisions, the overrides
    and the outcomes are append-only, so a re-import would duplicate
    them. What the import does is recompute the hash of every row and
    report whether the export came back unchanged.

    Args:
        entity: The kind of row.
        raw: The CSV.

    Returns:
        What the import found.
    """
    reader = csv.DictReader(io.StringIO(raw))
    hashes: list[str] = []
    matching = 0
    mismatching = 0

    for row in reader:
        exported = row.get(entity.hash_column, "")
        recomputed = row_hash(entity, {column: row.get(column, "") for column in entity.columns})
        if exported == recomputed:
            matching += 1
        else:
            mismatching += 1
        hashes.append(recomputed)

    return ImportResult(
        entity=entity.name,
        rows=len(hashes),
        matching_hashes=matching,
        mismatching_hashes=mismatching,
        hash=combined_hash(hashes),
    )


class ExportService:
    """Builds the exports."""

    async def decisions(self, session: Any) -> tuple[str, str]:
        """Export the decisions.

        Args:
            session: Database session.

        Returns:
            The CSV and the combined hash of the rows.
        """
        from sqlalchemy import select

        from secondroute.decision.models import Decision

        from secondroute.analytics.reports import decision_is_synthetic

        result = await session.execute(select(Decision).order_by(Decision.created_at))
        rows = []
        for decision in result.scalars().all():
            rows.append(
                {
                    "decision_id": str(decision.id),
                    "unit_id": str(decision.unit_id),
                    "created_at": decision.created_at,
                    "model_version": decision.model_version,
                    "risk_profile": decision.risk_profile,
                    "recommended_channel": decision.recommended_channel,
                    "confidence": decision.confidence,
                    "fallback_used": decision.fallback_used,
                    "input_snapshot_hash": decision.input_snapshot_hash,
                    "calibration_version": decision.calibration_version,
                    "data_kind": "synthetic" if decision_is_synthetic(decision) else "real",
                }
            )
        return self._render(DECISIONS, rows)

    async def overrides(self, session: Any) -> tuple[str, str]:
        """Export the overrides.

        Args:
            session: Database session.

        Returns:
            The CSV and the combined hash of the rows.
        """
        from sqlalchemy import select

        from secondroute.decision.models import Decision
        from secondroute.feedback.models import Override

        from secondroute.analytics.reports import decision_is_synthetic

        decisions = await session.execute(select(Decision))
        kind_by_decision = {
            decision.id: ("synthetic" if decision_is_synthetic(decision) else "real")
            for decision in decisions.scalars().all()
        }

        result = await session.execute(select(Override).order_by(Override.created_at))
        rows = []
        for override in result.scalars().all():
            rows.append(
                {
                    "override_id": str(override.id),
                    "decision_id": str(override.decision_id),
                    "created_at": override.created_at,
                    "chosen_channel": override.chosen_channel,
                    "reason_text": override.reason_text,
                    "data_kind": kind_by_decision.get(override.decision_id, "real"),
                }
            )
        return self._render(OVERRIDES, rows)

    async def outcomes(self, session: Any) -> tuple[str, str]:
        """Export the outcomes.

        Args:
            session: Database session.

        Returns:
            The CSV and the combined hash of the rows.
        """
        from sqlalchemy import select

        from secondroute.decision.models import Decision
        from secondroute.feedback.models import Outcome

        from secondroute.analytics.reports import decision_is_synthetic

        decisions = await session.execute(select(Decision))
        kind_by_decision = {
            decision.id: ("synthetic" if decision_is_synthetic(decision) else "real")
            for decision in decisions.scalars().all()
        }

        result = await session.execute(select(Outcome).order_by(Outcome.recorded_at))
        rows = []
        for outcome in result.scalars().all():
            rows.append(
                {
                    "outcome_id": str(outcome.id),
                    "unit_id": str(outcome.unit_id),
                    "decision_id": str(outcome.decision_id),
                    "recorded_at": outcome.recorded_at,
                    "channel_taken": outcome.channel_taken,
                    "sale_price": outcome.sale_price,
                    "fees_actual": outcome.fees_actual,
                    "repair_cost_actual": outcome.repair_cost_actual,
                    "logistics_actual": outcome.logistics_actual,
                    "days_to_disposition": outcome.days_to_disposition,
                    "final_status": outcome.final_status,
                    "net": float(outcome.net),
                    "data_kind": kind_by_decision.get(outcome.decision_id, "real"),
                }
            )
        return self._render(OUTCOMES, rows)

    def _render(
        self,
        entity: ExportEntity,
        rows: list[dict[str, Any]],
    ) -> tuple[str, str]:
        """Render the rows as CSV and compute the combined hash.

        Args:
            entity: The kind of row.
            rows: The rows.

        Returns:
            The CSV and the combined hash of the rows.
        """
        rendered = [
            {column: format_value(row.get(column)) for column in entity.columns} for row in rows
        ]
        hashes = [row_hash(entity, row) for row in rendered]
        return write_csv(entity, rendered), combined_hash(hashes)


def entity_for(name: str) -> Optional[ExportEntity]:
    """Return the export entity with the given name.

    Args:
        name: The name.

    Returns:
        The entity, or None when there is no such export.
    """
    return ENTITIES.get(name)
