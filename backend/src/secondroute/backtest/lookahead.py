"""
Look-ahead detection for the historical backtest (Phase 5 - F5.6).

A backtest is only worth reading if it could have been made at the time it
claims to describe. The detector walks the provenance recorded on every
decision and reports anything dated after the decision was made.

Three kinds of finding are distinguished:

``lookahead``
    A source used by the decision is dated *after* the decision was made.
    This is a leak: the decision used information from its own future.

``provenance``
    The decision records no timestamp for a source it used, so the absence
    of a leak cannot be proven. This is a gap in the audit trail rather
    than proof of a leak, but a no-look-ahead claim cannot be made either
    way, so it is reported alongside the leaks.

``malformed``
    A recorded timestamp cannot be parsed. This is a bug in the producer,
    not a leak, and it is reported so it does not pass silently.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping

__all__ = [
    "LookAheadError",
    "LookAheadFinding",
    "LookAheadReport",
    "check_decision",
    "check_decision_with_relations",
]


#: Finding kinds.
LEAK = "lookahead"
PROVENANCE = "provenance"
MALFORMED = "malformed"


@dataclass(frozen=True, slots=True)
class LookAheadFinding:
    """One problem found in a decision's provenance.

    Attributes:
        decision_id: The decision the finding belongs to.
        kind: One of ``lookahead``, ``provenance`` or ``malformed``.
        field: Which recorded field the finding is about.
        as_of: The timestamp of the offending source, when it is known.
        decision_time: When the decision was made.
        detail: A human-readable explanation.
    """

    decision_id: str
    kind: str
    field: str
    decision_time: datetime
    as_of: datetime | None = None
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of the finding."""
        return {
            "decision_id": self.decision_id,
            "kind": self.kind,
            "field": self.field,
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "decision_time": self.decision_time.isoformat(),
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class LookAheadReport:
    """The result of checking one or more decisions.

    Attributes:
        findings: Every finding, in the order they were found.
    """

    findings: tuple[LookAheadFinding, ...] = ()

    @property
    def has_leak(self) -> bool:
        """Whether any source was dated after the decision it fed."""
        return any(finding.kind == LEAK for finding in self.findings)

    @property
    def leaks(self) -> tuple[LookAheadFinding, ...]:
        """The findings that are actual look-ahead leaks."""
        return tuple(finding for finding in self.findings if finding.kind == LEAK)

    @property
    def is_clean(self) -> bool:
        """Whether the decision's provenance is fully verifiable and leak-free."""
        return not self.findings

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of the report."""
        return {
            "has_leak": self.has_leak,
            "is_clean": self.is_clean,
            "finding_count": len(self.findings),
            "findings": [finding.as_dict() for finding in self.findings],
        }


class LookAheadError(RuntimeError):
    """Raised when a backtest is asked to run over decisions that leak.

    Attributes:
        report: The findings that stopped the run.
    """

    def __init__(self, report: LookAheadReport) -> None:
        self.report = report
        leaks = report.leaks
        summary = ", ".join(f"{finding.decision_id}:{finding.field}" for finding in leaks[:5])
        super().__init__(
            f"Backtest refused: {len(leaks)} decision(s) used data dated after they "
            f"were made ({summary})"
        )


def _parse_timestamp(raw: Any) -> datetime | None:
    """Parse a recorded timestamp, returning ``None`` when it is unusable."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _check_timestamps(
    decision_id: str,
    decision_time: datetime,
    field_prefix: str,
    timestamps: Mapping[str, Any],
    findings: list[LookAheadFinding],
    *,
    require_provenance: bool,
) -> None:
    """Check a mapping of ``field -> timestamp`` against the decision time."""
    for field, raw in sorted(timestamps.items()):
        label = f"{field_prefix}:{field}" if field_prefix else field
        as_of = _parse_timestamp(raw)
        if as_of is None:
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                if require_provenance:
                    findings.append(
                        LookAheadFinding(
                            decision_id=decision_id,
                            kind=PROVENANCE,
                            field=label,
                            decision_time=decision_time,
                            detail=(
                                f"No as-of date recorded for {label}, so the absence of a "
                                f"look-ahead cannot be proven."
                            ),
                        )
                    )
                continue
            findings.append(
                LookAheadFinding(
                    decision_id=decision_id,
                    kind=MALFORMED,
                    field=label,
                    decision_time=decision_time,
                    detail=f"Recorded as-of date for {label} is not a timestamp: {raw!r}",
                )
            )
            continue

        if as_of > decision_time:
            findings.append(
                LookAheadFinding(
                    decision_id=decision_id,
                    kind=LEAK,
                    field=label,
                    as_of=as_of,
                    decision_time=decision_time,
                    detail=(
                        f"{label} is dated {as_of.isoformat()}, after the decision was made "
                        f"at {decision_time.isoformat()}."
                    ),
                )
            )


def check_decision(
    decision: Any,
    *,
    inspection_created_at: datetime | None = None,
    unit_received_at: datetime | None = None,
    require_provenance: bool = True,
) -> LookAheadReport:
    """Check one decision for look-ahead.

    The decision must record its provenance: the ``data_freshness`` payload
    holds the as-of date of every price and cost it used, and the input
    snapshot holds the moment the prices were looked up.

    Args:
        decision: The decision to check. Anything with ``id``, ``created_at``,
            ``data_freshness`` and ``input_snapshot`` works, so the checker
            is usable against stored decisions and against test doubles.
        inspection_created_at: When the inspection the decision was based on
            was recorded.
        unit_received_at: When the unit was received.
        require_provenance: Whether a missing as-of date is a finding. When
            ``False``, only recorded dates are checked and the gap is not
            reported.

    Returns:
        The findings. An empty report means the decision is clean.
    """
    decision_id = str(getattr(decision, "id", ""))
    decision_time: datetime = decision.created_at
    findings: list[LookAheadFinding] = []

    freshness = _as_mapping(getattr(decision, "data_freshness", None))
    snapshot = _as_mapping(getattr(decision, "input_snapshot", None))

    _check_timestamps(
        decision_id,
        decision_time,
        "price_as_of",
        _as_mapping(freshness.get("price_as_of")),
        findings,
        require_provenance=require_provenance,
    )
    _check_timestamps(
        decision_id,
        decision_time,
        "cost_as_of",
        _as_mapping(freshness.get("cost_as_of")),
        findings,
        require_provenance=require_provenance,
    )

    raw_snapshot_as_of = snapshot.get("as_of")
    if raw_snapshot_as_of is None:
        if require_provenance:
            findings.append(
                LookAheadFinding(
                    decision_id=decision_id,
                    kind=PROVENANCE,
                    field="snapshot:as_of",
                    decision_time=decision_time,
                    detail=(
                        "The decision records no as-of date for its input snapshot, so the "
                        "absence of a look-ahead cannot be proven."
                    ),
                )
            )
    else:
        snapshot_as_of = _parse_timestamp(raw_snapshot_as_of)
        if snapshot_as_of is None:
            findings.append(
                LookAheadFinding(
                    decision_id=decision_id,
                    kind=MALFORMED,
                    field="snapshot:as_of",
                    decision_time=decision_time,
                    detail=(
                        "The recorded snapshot as-of date is not a timestamp: "
                        f"{raw_snapshot_as_of!r}"
                    ),
                )
            )
        elif snapshot_as_of > decision_time:
            findings.append(
                LookAheadFinding(
                    decision_id=decision_id,
                    kind=LEAK,
                    field="snapshot:as_of",
                    as_of=snapshot_as_of,
                    decision_time=decision_time,
                    detail=(
                        f"The input snapshot is dated {snapshot_as_of.isoformat()}, after the "
                        f"decision was made at {decision_time.isoformat()}."
                    ),
                )
            )

    if inspection_created_at is not None and inspection_created_at > decision_time:
        findings.append(
            LookAheadFinding(
                decision_id=decision_id,
                kind=LEAK,
                field="inspection:created_at",
                as_of=inspection_created_at,
                decision_time=decision_time,
                detail=(
                    f"The inspection is dated {inspection_created_at.isoformat()}, after the "
                    f"decision was made at {decision_time.isoformat()}."
                ),
            )
        )

    if unit_received_at is not None and unit_received_at > decision_time:
        findings.append(
            LookAheadFinding(
                decision_id=decision_id,
                kind=LEAK,
                field="unit:received_at",
                as_of=unit_received_at,
                decision_time=decision_time,
                detail=(
                    f"The unit was received at {unit_received_at.isoformat()}, after the "
                    f"decision was made at {decision_time.isoformat()}."
                ),
            )
        )

    return LookAheadReport(findings=tuple(findings))


async def check_decision_with_relations(
    session: Any,
    decision: Any,
    *,
    require_provenance: bool = True,
) -> LookAheadReport:
    """Check one decision, looking up the inspection and unit it depends on.

    Args:
        session: Database session.
        decision: The decision to check.
        require_provenance: Whether a missing as-of date is a finding.

    Returns:
        The findings. An empty report means the decision is clean.
    """
    from secondroute.intake.models import Inspection, Unit

    inspection_created_at: datetime | None = None
    unit_received_at: datetime | None = None

    unit_id = getattr(decision, "unit_id", None)
    if unit_id is not None:
        unit = await session.get(Unit, unit_id)
        if unit is not None:
            unit_received_at = getattr(unit, "received_at", None)

    from sqlalchemy import select

    inspection_result = await session.execute(
        select(Inspection)
        .where(Inspection.unit_id == unit_id)
        .order_by(Inspection.created_at.desc())
        .limit(1)
    )
    inspection = inspection_result.scalar_one_or_none()
    if inspection is not None:
        inspection_created_at = getattr(inspection, "created_at", None)

    return check_decision(
        decision,
        inspection_created_at=inspection_created_at,
        unit_received_at=unit_received_at,
        require_provenance=require_provenance,
    )


def combine_reports(reports: Iterable[LookAheadReport]) -> LookAheadReport:
    """Merge several reports into one."""
    findings: list[LookAheadFinding] = []
    for report in reports:
        findings.extend(report.findings)
    return LookAheadReport(findings=tuple(findings))


def _as_mapping(value: Any) -> Mapping[str, Any]:
    """Return ``value`` as a mapping, treating anything else as empty."""
    if isinstance(value, Mapping):
        return value
    return {}
