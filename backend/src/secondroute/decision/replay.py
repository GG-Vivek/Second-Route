"""Replay a stored decision from its snapshot (F8.4).

A decision is stored with the exact inputs it was made from. Replaying it
means running the engine again on those inputs alone, which is what proves
that the decision is reproducible rather than merely repeatable.

Two things use this: the reproducibility endpoint, and the distribution
endpoint, which needs the engine's Monte Carlo draws and therefore needs
the engine to run again.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.condition.grades import InspectionSignals
from secondroute.costs.service import CostBook, CostBookEntry
from secondroute.decision.engine import (
    DecisionOutcome,
    SignalInspection,
    build_price_context,
    run_decision,
)
from secondroute.decision.models import Decision
from secondroute.pricing.protocols import PriceSource

__all__ = ["SnapshotReplayError", "replay_from_snapshot"]


class SnapshotReplayError(Exception):
    """The stored snapshot cannot be replayed."""


def _signals_from(snapshot: dict[str, Any]) -> InspectionSignals:
    """Rebuild the inspection signals from the snapshot."""
    raw = snapshot.get("signals")
    if not isinstance(raw, dict):
        raise SnapshotReplayError("The snapshot has no signals.")

    try:
        return InspectionSignals(
            battery_health_pct=(
                None
                if raw.get("battery_health_pct") in (None, "")
                else float(raw["battery_health_pct"])
            ),
            battery_cycles=raw.get("battery_cycles"),
            cosmetic_grade=str(raw["cosmetic_grade"]),
            functional_tests=raw.get("functional_tests") or {},
            accessories=raw.get("accessories") or {},
            activation_lock=str(raw.get("activation_lock", "unknown")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SnapshotReplayError(f"The snapshot signals are malformed: {exc}") from exc


def _cost_book_from(snapshot: dict[str, Any]) -> CostBook:
    """Rebuild the cost book from the snapshot."""
    raw = snapshot.get("cost_book")
    if not isinstance(raw, dict):
        raise SnapshotReplayError("The snapshot has no cost book.")

    entries: dict[tuple[str, str], CostBookEntry] = {}
    for raw_key, value in raw.items():
        kind, _, key = str(raw_key).partition(":")
        try:
            entries[(kind, key)] = CostBookEntry(
                kind=kind,
                key=key,
                value=float(value),
                source="snapshot",
                as_of=datetime.now(UTC).date(),
            )
        except (TypeError, ValueError) as exc:
            raise SnapshotReplayError(f"The snapshot cost book is malformed: {exc}") from exc

    return CostBook(entries=entries)


async def replay_from_snapshot(
    session: AsyncSession,
    decision: Decision,
    price_source: PriceSource,
) -> DecisionOutcome:
    """Run the engine again on the inputs a decision was stored with.

    Args:
        session: Database session.
        decision: The stored decision. Its snapshot is the input.
        price_source: Where the sale prices come from.

    Returns:
        The outcome of the replay, including the Monte Carlo draws.

    Raises:
        SnapshotReplayError: When the snapshot is missing or malformed.
    """
    snapshot = decision.input_snapshot

    try:
        signals = _signals_from(snapshot)
        cost_book = _cost_book_from(snapshot)
        unit_id = UUID(str(snapshot["unit_id"]))
        sku_id = UUID(str(snapshot["sku_id"]))
        risk_profile = str(snapshot["risk_profile"])
        samples = int(snapshot["samples"])
        seed = int(snapshot["seed"])
        threshold = float(snapshot["threshold"])
        as_of = datetime.fromisoformat(str(snapshot["as_of"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise SnapshotReplayError(f"The snapshot is malformed: {exc}") from exc

    # The same context the live decision had: the price source bound to the
    # SKU family, the parts valuation, and the launch calendar. Without
    # these the replay would price a different unit than the one that was
    # decided.
    effective_price_source, hold_eligibility = await build_price_context(
        session,
        unit_id=unit_id,
        sku_id=sku_id,
        signals=signals,
        inspection_like=SignalInspection(signals),
        price_source=price_source,
        as_of=as_of,
    )

    return await run_decision(
        unit_id=unit_id,
        sku_id=sku_id,
        signals=signals,
        cost_book=cost_book,
        price_source=effective_price_source,
        risk_profile=risk_profile,
        samples=samples,
        seed=seed,
        threshold=threshold,
        as_of=as_of,
        include_flip_conditions=False,
        extra_eligibility=hold_eligibility,
    )
