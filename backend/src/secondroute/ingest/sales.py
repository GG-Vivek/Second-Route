"""
Partner sold-data CSV import (Phase 3 - F3.2).

A partner sends a CSV of the units they sold, the channel they sold them
through, and the price. Those are the highest-priority price signals in the
whole system, so the import has to be careful:

* **Every row is validated.** A row that cannot be trusted is rejected with a
  reason, not silently dropped.
* **The import is idempotent.** The file is hashed; importing the same file
  twice changes nothing.
* **A dry run reports exactly what a real run would do.** Same counts, same
  rejection reasons, nothing written.

The import writes into ``price_observations`` with the partner's name as the
source, so the engine can prefer it over market data.
"""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from datetime import date, datetime, timezone, UTC
from typing import Any, Final, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.logging import get_logger
from secondroute.ingest.models import ImportFile
from secondroute.ingest.schemas import (
    ColumnMapping,
    ImportPreview,
    ImportResult,
    RejectedRow,
)
from secondroute.pricing.cleaning import normalize_grade
from secondroute.pricing.models import PriceObservation

logger = get_logger(__name__)

__all__ = [
    "CANONICAL_CHANNELS",
    "SalesRow",
    "auto_detect_mapping",
    "file_hash",
    "import_sales",
    "parse_sales_csv",
    "preview_sales_file",
]

#: The channels a partner may report a sale through.
CANONICAL_CHANNELS: Final[tuple[str, ...]] = (
    "RESELL_OPEN_BOX",
    "RESELL_REFURB",
    "RECYCLE",
    "DONATE",
    "PARTS_HARVEST",
    "HOLD",
)

#: Column-name aliases used by the auto-detection, per canonical field.
FIELD_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "sku": ("sku", "skuid", "sku_id", "productsku", "itemsku", "productcode", "itemid"),
    "grade": (
        "grade",
        "condition",
        "conditiongrade",
        "itemcondition",
        "conditionid",
        "gradea",
        "conditionlabel",
    ),
    "channel": (
        "channel",
        "disposition",
        "dispositionchannel",
        "saleschannel",
        "route",
        "channelname",
    ),
    "price": (
        "price",
        "saleprice",
        "amount",
        "netprice",
        "grossprice",
        "transactionamount",
        "realizedprice",
    ),
    "sold_at": ("soldat", "date", "solddate", "transactiondate", "salestimestamp", "timestamp"),
    "quantity": ("quantity", "qty", "units", "unitssold", "count"),
}

#: How many rejected rows the result carries. The counts always describe
#: every row; only the detail is capped.
MAX_REPORTED_REJECTIONS: Final[int] = 200


def file_hash(content: bytes) -> str:
    """Return the SHA-256 of the uploaded bytes.

    Args:
        content: The raw file content.

    Returns:
        The hex digest.
    """
    return hashlib.sha256(content).hexdigest()


def _normalise_header(name: str) -> str:
    """Return a header name in a comparable form."""
    return name.strip().lower().replace(" ", "").replace("_", "").replace("-", "")


def auto_detect_mapping(columns: Sequence[str]) -> ColumnMapping | None:
    """Guess which column holds which field.

    Args:
        columns: The headers of the file.

    Returns:
        The mapping, or ``None`` when a required field could not be found.
        A partial guess is not useful - a wrong mapping silently imports the
        wrong data, so nothing is returned unless everything lines up.
    """
    normalised = {_normalise_header(column): column for column in columns}

    resolved: dict[str, str] = {}
    for field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in normalised:
                resolved[field] = normalised[alias]
                break

    required = ("sku", "grade", "channel", "price", "sold_at")
    if any(field not in resolved for field in required):
        return None

    return ColumnMapping(
        sku=resolved["sku"],
        grade=resolved["grade"],
        channel=resolved["channel"],
        price=resolved["price"],
        sold_at=resolved["sold_at"],
        quantity=resolved.get("quantity"),
    )


def preview_sales_file(content: bytes, filename: str) -> ImportPreview:
    """Describe a file without importing it.

    Args:
        content: The raw file content.
        filename: The uploaded filename.

    Returns:
        The preview: the columns, the suggested mapping, the row count and the
        file hash.
    """
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    columns = list(reader.fieldnames or [])
    rows = list(reader)

    return ImportPreview(
        columns=columns,
        suggested_mapping=auto_detect_mapping(columns),
        row_count=len(rows),
        filename=filename,
        file_hash=file_hash(content),
    )


@dataclass(frozen=True, slots=True)
class SalesRow:
    """A validated row of a partner sales file.

    Attributes:
        row_number: The 1-based line number in the file.
        sku_id: The SKU the sale refers to.
        grade: The normalised grade.
        channel: The normalised channel.
        price: The sale price.
        sold_at: When the sale happened.
        quantity: How many units were sold.
    """

    row_number: int
    sku_id: UUID
    grade: str
    channel: str
    price: float
    sold_at: datetime
    quantity: int = 1


@dataclass(slots=True)
class ParseOutcome:
    """The result of parsing and validating a sales file.

    Attributes:
        rows: The accepted rows.
        rejected: The rejected rows, with reasons.
        total: How many data rows the file had.
        mapping: The mapping that was used.
    """

    rows: list[SalesRow]
    rejected: list[RejectedRow]
    total: int
    mapping: ColumnMapping


def _parse_date(raw: str) -> datetime:
    """Parse a date from a partner file.

    Args:
        raw: The raw value.

    Returns:
        The parsed timestamp.

    Raises:
        ValueError: If the value is not a date we understand.
    """
    text = raw.strip()
    if not text:
        raise ValueError("empty date")

    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text).replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValueError(f"unrecognised date {text!r}") from exc


def _resolve_channel(raw: str) -> str:
    """Map a partner's channel name onto a canonical channel.

    Args:
        raw: The raw value.

    Returns:
        The canonical channel.

    Raises:
        ValueError: If the channel is not recognised.
    """
    key = raw.strip().upper().replace(" ", "_").replace("-", "_")
    if key in CANONICAL_CHANNELS:
        return key

    aliases = {
        "OPEN_BOX": "RESELL_OPEN_BOX",
        "OPENBOX": "RESELL_OPEN_BOX",
        "RESELL": "RESELL_OPEN_BOX",
        "REFURB": "RESELL_REFURB",
        "REFURBISHED": "RESELL_REFURB",
        "REPAIR": "RESELL_REFURB",
        "PARTS": "PARTS_HARVEST",
        "HARVEST": "PARTS_HARVEST",
        "CHARITY": "DONATE",
        "WASTE": "RECYCLE",
    }
    if key in aliases:
        return aliases[key]

    raise ValueError(f"unknown channel {raw!r}")


async def _resolve_sku(session: AsyncSession, raw: str) -> UUID:
    """Find the SKU a row refers to.

    The partner may give the SKU id, or a key of the form
    ``family|model_name``.

    Args:
        session: Database session.
        raw: The raw value.

    Returns:
        The SKU id.

    Raises:
        ValueError: If the SKU cannot be found.
    """
    from secondroute.identity.models import SKU

    text = raw.strip()
    if not text:
        raise ValueError("empty SKU")

    try:
        candidate = UUID(text)
    except ValueError:
        candidate = None

    if candidate is not None:
        found = await session.get(SKU, candidate)
        if found is None:
            raise ValueError(f"unknown SKU {text!r}")
        return UUID(str(found.id))

    if "|" in text:
        family, _, model_name = text.partition("|")
        result = await session.execute(
            select(SKU).where(
                SKU.family == family.strip(),
                SKU.model_name == model_name.strip(),
            )
        )
        found = result.scalars().first()
        if found is None:
            raise ValueError(f"unknown SKU {text!r}")
        return UUID(str(found.id))

    result = await session.execute(select(SKU).where(SKU.model_name == text))
    found = result.scalars().first()
    if found is None:
        raise ValueError(f"unknown SKU {text!r}")
    return UUID(str(found.id))


async def parse_sales_csv(
    session: AsyncSession,
    content: bytes,
    mapping: ColumnMapping,
) -> ParseOutcome:
    """Parse and validate a sales file.

    Args:
        session: Database session, used to resolve SKUs.
        content: The raw file content.
        mapping: Which column holds which field.

    Returns:
        The accepted rows and the rejected rows with reasons.
    """
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    rows: list[SalesRow] = []
    rejected: list[RejectedRow] = []
    total = 0

    for index, raw_row in enumerate(reader):
        total += 1
        row_number = index + 2  # Line 1 is the header.
        raw = {key: value for key, value in raw_row.items() if key is not None}

        try:
            sku_id = await _resolve_sku(session, raw.get(mapping.sku, ""))
            grade = normalize_grade(raw.get(mapping.grade))
            if grade is None:
                raise ValueError(f"unrecognised grade {raw.get(mapping.grade, '')!r}")
            channel = _resolve_channel(raw.get(mapping.channel, ""))
            price_raw = raw.get(mapping.price, "").strip().replace(",", "").replace("$", "")
            price = float(price_raw)
            if price <= 0:
                raise ValueError(f"price must be positive, got {price_raw!r}")
            sold_at = _parse_date(raw.get(mapping.sold_at, ""))
            quantity = 1
            if mapping.quantity:
                quantity_raw = raw.get(mapping.quantity, "").strip()
                if quantity_raw:
                    quantity = int(float(quantity_raw))
                    if quantity <= 0:
                        raise ValueError(f"quantity must be positive, got {quantity_raw!r}")
        except (ValueError, TypeError) as exc:
            rejected.append(
                RejectedRow(
                    row_number=row_number,
                    reason=_reason_for(exc),
                    detail=str(exc),
                    raw=raw,
                )
            )
            continue

        rows.append(
            SalesRow(
                row_number=row_number,
                sku_id=sku_id,
                grade=grade,
                channel=channel,
                price=price,
                sold_at=sold_at,
                quantity=quantity,
            )
        )

    return ParseOutcome(rows=rows, rejected=rejected, total=total, mapping=mapping)


def _reason_for(exc: Exception) -> str:
    """Turn an exception into a short, stable rejection reason."""
    message = str(exc)
    reasons = (
        ("unknown SKU", "unknown_sku"),
        ("unrecognised grade", "invalid_grade"),
        ("unknown channel", "invalid_channel"),
        ("price must be positive", "invalid_price"),
        ("quantity must be positive", "invalid_quantity"),
    )
    for marker, reason in reasons:
        if message.startswith(marker):
            return reason
    if "date" in message:
        return "invalid_date"
    return "invalid_row"


async def import_sales(
    session: AsyncSession,
    content: bytes,
    *,
    filename: str,
    source: str,
    mapping: ColumnMapping | None = None,
    dry_run: bool = False,
    import_kind: str = "sales",
) -> ImportResult:
    """Import a partner sales file.

    Args:
        session: Database session.
        content: The raw file content.
        filename: The uploaded filename.
        source: The partner's name. This becomes the price observation source.
        mapping: Which column holds which field. Auto-detected when omitted.
        dry_run: When true, nothing is written but the counts are the same.
        import_kind: What kind of import this is.

    Returns:
        The result: the counts, the rejected rows and the mapping used.

    Raises:
        ValueError: When the file cannot be mapped or the header is missing.
    """
    digest = file_hash(content)

    existing = await session.execute(
        select(ImportFile).where(
            ImportFile.file_hash == digest,
            ImportFile.import_kind == import_kind,
        )
    )
    previous = existing.scalars().first()
    if previous is not None:
        logger.info("sales_import_skipped_already_imported", file_hash=digest[:12])
        return ImportResult(
            dry_run=dry_run,
            rows_total=previous.rows_imported + previous.rows_rejected,
            rows_imported=previous.rows_imported,
            rows_rejected=previous.rows_rejected,
            mapping=mapping,
            file_hash=digest,
            already_imported=True,
            import_id=previous.id,
            message=(
                f"This file was already imported on "
                f"{previous.imported_at.isoformat()}. Nothing changed."
            ),
        )

    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    columns = list(reader.fieldnames or [])
    if not columns:
        raise ValueError("the file has no header row")

    resolved = mapping or auto_detect_mapping(columns)
    if resolved is None:
        raise ValueError(
            "could not work out which column holds which field; pass an explicit mapping"
        )

    missing = [column for column in resolved.columns() if column not in columns]
    if missing:
        raise ValueError(f"the file has no column named {', '.join(sorted(missing))}")

    outcome = await parse_sales_csv(session, content, resolved)

    if dry_run:
        logger.info(
            "sales_import_dry_run",
            rows_total=outcome.total,
            rows_imported=len(outcome.rows),
            rows_rejected=len(outcome.rejected),
        )
        return ImportResult(
            dry_run=True,
            rows_total=outcome.total,
            rows_imported=len(outcome.rows),
            rows_rejected=len(outcome.rejected),
            rejected=outcome.rejected[:MAX_REPORTED_REJECTIONS],
            mapping=resolved,
            file_hash=digest,
            message=(
                f"Dry run: {len(outcome.rows)} of {outcome.total} rows would be imported, "
                f"{len(outcome.rejected)} would be rejected."
            ),
        )

    for row in outcome.rows:
        session.add(
            PriceObservation(
                sku_id=row.sku_id,
                grade=row.grade,
                channel=row.channel,
                price=row.price,
                currency="USD",
                source=source,
                observed_at=row.sold_at,
                weight=1.0,
                is_synthetic=False,
                as_of=row.sold_at.date(),
            )
        )

    record = ImportFile(
        file_hash=digest,
        filename=filename,
        source=source,
        status="completed",
        rows_imported=len(outcome.rows),
        rows_rejected=len(outcome.rejected),
        import_kind=import_kind,
        report_json="{}",
    )
    session.add(record)
    await session.flush()

    logger.info(
        "sales_import_completed",
        file_hash=digest[:12],
        source=source,
        rows_total=outcome.total,
        rows_imported=len(outcome.rows),
        rows_rejected=len(outcome.rejected),
    )

    return ImportResult(
        dry_run=False,
        rows_total=outcome.total,
        rows_imported=len(outcome.rows),
        rows_rejected=len(outcome.rejected),
        rejected=outcome.rejected[:MAX_REPORTED_REJECTIONS],
        mapping=resolved,
        file_hash=digest,
        already_imported=False,
        import_id=record.id,
        message=(
            f"Imported {len(outcome.rows)} of {outcome.total} rows; "
            f"{len(outcome.rejected)} rejected."
        ),
    )
