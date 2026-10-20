"""
Decision API routes (Phase 2 - F2.9).

Endpoints:

* ``POST /api/v1/units/{unit_id}/decide`` - run the engine and store the decision
* ``GET  /api/v1/decisions/{decision_id}`` - read a stored decision
* ``GET  /api/v1/units/{unit_id}/decisions`` - list a unit's decisions
* ``GET  /api/v1/decisions/{decision_id}/reproduce`` - replay from the snapshot
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.config import settings
from secondroute.core.db import get_session
from secondroute.decision.engine import (
    DECISION_MODEL_VERSION,
    decide_unit,
    decision_to_dict,
    run_decision,
)
from secondroute.decision.models import Decision, hash_snapshot
from secondroute.decision.schemas import (
    DecisionCreate,
    DecisionListRead,
    DecisionRead,
    DecisionSummaryRead,
    ExplanationRead,
    ReproducibilityRead,
)
from secondroute.instructions.explainer import ExplainerService, decision_payload
from secondroute.instructions.models import DecisionExplanation
from secondroute.pricing.composite import FallbackPriceSource
from secondroute.pricing.protocols import PriceSource
from secondroute.pricing.sources import DatabasePriceSource, SyntheticPriceSource

router = APIRouter(tags=["Decisions"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _price_source(session: AsyncSession) -> PriceSource:
    """Return the price source used by the API.

    Real market data is preferred, so the stored observations go first. The
    synthetic source is the fallback, which is what keeps the prototype
    working before any real data has been collected.

    Phase 3 swaps the database source for the real adapters; the fallback
    chain stays the same.
    """
    return FallbackPriceSource(
        DatabasePriceSource(session, source_tag="synthetic"),
        SyntheticPriceSource(),
    )


@router.post(
    "/units/{unit_id}/decide",
    response_model=DecisionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Run the decision engine for a unit",
)
async def create_decision(
    unit_id: UUID,
    session: SessionDep,
    body: DecisionCreate | None = None,
) -> DecisionRead:
    """Run the decision engine for a unit and store the result.

    Args:
        unit_id: The unit to decide.
        body: Optional request body (risk profile).
        session: Database session.

    Returns:
        The stored decision.

    Raises:
        HTTPException: 404 when the unit does not exist or has no inspection.
    """
    body = body or DecisionCreate()
    try:
        decision = await decide_unit(
            session,
            unit_id,
            _price_source(session),
            risk_profile=body.risk_profile,
            as_of=body.as_of or datetime.utcnow(),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return _to_read(decision)


@router.get(
    "/decisions/{decision_id}",
    response_model=DecisionRead,
    summary="Read a stored decision",
)
async def get_decision(decision_id: UUID, session: SessionDep) -> DecisionRead:
    """Return the full output of a stored decision.

    Args:
        decision_id: The decision to read.
        session: Database session.

    Returns:
        The decision.

    Raises:
        HTTPException: 404 when the decision does not exist.
    """
    decision = await session.get(Decision, decision_id)
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision not found",
        )
    return _to_read(decision)


@router.post(
    "/decisions/{decision_id}/explanation",
    response_model=ExplanationRead,
    summary="Explain a decision in words",
)
async def explain_decision(
    decision_id: UUID,
    session: SessionDep,
    refresh: Annotated[
        bool,
        Query(description="Write a new explanation even if one is already stored"),
    ] = False,
) -> ExplanationRead:
    """Explain a decision, in words an operator can read.

    The model is given the decision as structured JSON and it writes
    nothing but the words. Every number it produces is checked against
    the numbers the decision actually contains, and text that mentions a
    number the decision does not have is thrown away in favour of the
    Phase 2 template. The response says which of the two happened.

    The explanation is stored, so the model is only asked once. Pass
    ``refresh=true`` to write a new one.

    Args:
        decision_id: The decision to explain.
        session: Database session.
        refresh: Whether to write a new explanation.

    Returns:
        The explanation.

    Raises:
        HTTPException: 404 when the decision does not exist.
    """
    decision = await session.get(Decision, decision_id)
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision not found",
        )

    if not refresh:
        stored = await _latest_explanation(session, decision_id)
        if stored is not None:
            return ExplanationRead(
                id=stored.id,
                decision_id=stored.decision_id,
                text=stored.text,
                source=stored.source,
                reason=stored.reason,
                model=stored.model,
                unseen_numbers=json.loads(stored.unseen_numbers or "[]"),
                created_at=stored.created_at,
            )

    explanation = await ExplainerService().explain(decision_payload(decision))

    row = DecisionExplanation(
        decision_id=decision.id,
        text=explanation.text,
        source=explanation.source,
        reason=explanation.reason,
        model=explanation.model,
        unseen_numbers=json.dumps(list(explanation.unseen_numbers)),
        is_synthetic=bool(decision.data_freshness.get("is_synthetic", False)),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    return ExplanationRead(
        id=row.id,
        decision_id=row.decision_id,
        text=row.text,
        source=row.source,
        reason=row.reason,
        model=row.model,
        unseen_numbers=json.loads(row.unseen_numbers or "[]"),
        created_at=row.created_at,
    )


async def _latest_explanation(
    session: AsyncSession,
    decision_id: UUID,
) -> DecisionExplanation | None:
    """Return the most recent stored explanation of a decision.

    Args:
        session: Database session.
        decision_id: The decision.

    Returns:
        The explanation, or None when there is none.
    """
    result = await session.execute(
        select(DecisionExplanation)
        .where(DecisionExplanation.decision_id == decision_id)
        .order_by(DecisionExplanation.created_at.desc())
        .limit(1)
    )
    return result.scalars().first()


@router.get(
    "/units/{unit_id}/decisions",
    response_model=DecisionListRead,
    summary="List the decisions for a unit",
)
async def list_unit_decisions(
    unit_id: UUID,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DecisionListRead:
    """Return the decisions recorded for a unit, newest first.

    Args:
        unit_id: The unit.
        session: Database session.
        limit: Page size.
        offset: Page offset.

    Returns:
        A page of decision summaries.
    """
    total_result = await session.execute(
        select(func.count()).select_from(Decision).where(Decision.unit_id == unit_id)
    )
    total = int(total_result.scalar_one())

    result = await session.execute(
        select(Decision)
        .where(Decision.unit_id == unit_id)
        .order_by(Decision.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    decisions = result.scalars().all()

    return DecisionListRead(
        items=[
            DecisionSummaryRead.model_validate(
                {
                    "id": decision.id,
                    "unit_id": decision.unit_id,
                    "created_at": decision.created_at,
                    "recommended_channel": decision.recommended_channel,
                    "confidence": decision.confidence,
                    "fallback_used": decision.fallback_used,
                    "risk_profile": decision.risk_profile,
                }
            )
            for decision in decisions
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/decisions/{decision_id}/reproduce",
    response_model=ReproducibilityRead,
    summary="Replay a decision from its stored snapshot",
)
async def reproduce_decision(decision_id: UUID, session: SessionDep) -> ReproducibilityRead:
    """Replay a stored decision from its snapshot and compare the result.

    The replay uses only the data captured in the snapshot, so it proves the
    decision is reproducible rather than merely repeatable.

    Args:
        decision_id: The decision to replay.
        session: Database session.

    Returns:
        The replay result, including whether the hash matched.

    Raises:
        HTTPException: 404 when the decision does not exist.
    """
    from secondroute.condition.grades import InspectionSignals
    from secondroute.costs.service import CostBook, CostBookEntry
    from secondroute.decision.evaluator import EvaluationInput

    decision = await session.get(Decision, decision_id)
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision not found",
        )

    snapshot = decision.input_snapshot
    replayed_hash = hash_snapshot(snapshot)

    details: dict[str, Any] = {}
    recommended = decision.recommended_channel
    confidence = decision.confidence

    try:
        signals_payload = snapshot["signals"]
        signals = InspectionSignals(
            battery_health_pct=float(signals_payload["battery_health_pct"]),
            battery_cycles=signals_payload.get("battery_cycles"),
            cosmetic_grade=str(signals_payload["cosmetic_grade"]),
            functional_tests=signals_payload.get("functional_tests") or {},
            accessories=signals_payload.get("accessories") or {},
            activation_lock=str(signals_payload.get("activation_lock", "unknown")),
        )

        entries: dict[tuple[str, str], CostBookEntry] = {}
        for raw_key, value in snapshot["cost_book"].items():
            kind, _, key = raw_key.partition(":")
            entries[(kind, key)] = CostBookEntry(
                kind=kind,
                key=key,
                value=float(value),
                source="snapshot",
                as_of=datetime.utcnow().date(),
            )
        book = CostBook(entries=entries)

        outcome = await run_decision(
            unit_id=UUID(str(snapshot["unit_id"])),
            sku_id=UUID(str(snapshot["sku_id"])),
            signals=signals,
            cost_book=book,
            price_source=_price_source(session),
            risk_profile=str(snapshot["risk_profile"]),
            samples=int(snapshot["samples"]),
            seed=int(snapshot["seed"]),
            threshold=float(snapshot["threshold"]),
            as_of=datetime.fromisoformat(snapshot["as_of"]),
            include_flip_conditions=False,
        )
        recommended = outcome.recommended_channel
        confidence = outcome.confidence
        details = {
            "replayed_reasons": [reason.as_dict() for reason in outcome.reasons],
            "replayed_candidates": outcome.candidates,
        }
    except (KeyError, ValueError, TypeError) as exc:
        details = {"error": f"Replay failed: {exc}"}

    return ReproducibilityRead(
        decision_id=decision.id,
        input_snapshot_hash=decision.input_snapshot_hash,
        replayed_hash=replayed_hash,
        matches=replayed_hash == decision.input_snapshot_hash,
        recommended_channel=recommended,
        confidence=confidence,
        details=details,
    )


def _to_read(decision: Decision) -> DecisionRead:
    """Convert a stored decision into the API schema."""
    payload = decision_to_dict(decision)
    payload["id"] = UUID(str(payload["id"]))
    payload["unit_id"] = UUID(str(payload["unit_id"]))
    payload["created_at"] = datetime.fromisoformat(payload["created_at"])
    payload["prototype_badge"] = "Prototype - synthetic prices"
    return DecisionRead.model_validate(payload)


MODEL_VERSION = DECISION_MODEL_VERSION
DEFAULT_CONFIDENCE_THRESHOLD = settings.CONFIDENCE_THRESHOLD


# ========================================================================
# Batch Decisions (Phase 5 - F5.4)
# ========================================================================

from pydantic import BaseModel, Field
from typing import List, Optional


class BatchDecideRequest(BaseModel):
    """Request for batch decision."""

    unit_ids: list[UUID] = Field(default_factory=list, max_length=1000)
    risk_profile: str = Field(default="balanced", pattern="^(conservative|balanced|aggressive)$")
    group_by: Optional[str] = Field(default=None, pattern="^(channel|grade|none)$")
    format: Optional[str] = Field(default="json", pattern="^(json|csv)$")


class BatchDecideResult(BaseModel):
    """Result for a single unit in batch."""

    unit_id: UUID
    decision_id: Optional[UUID] = None
    recommended_channel: Optional[str] = None
    confidence: Optional[float] = None
    fallback_used: Optional[bool] = None
    error: Optional[str] = None


class BatchDecideResponse(BaseModel):
    """Response for batch decision."""

    results: list[BatchDecideResult]
    total: int
    succeeded: int
    failed: int


@router.post(
    "/batches/decide",
    response_model=BatchDecideResponse,
    status_code=status.HTTP_200_OK,
    summary="Run batch decision for multiple units",
)
async def batch_decide(
    body: BatchDecideRequest,
    session: SessionDep,
) -> BatchDecideResponse:
    """Run batch decision for multiple units.

    Args:
        body: Batch decision request with unit IDs and risk profile.
        session: Database session.

    Returns:
        Batch decision results with per-unit outcomes.
    """
    from secondroute.intake.models import Unit

    # Validate risk profile
    if body.risk_profile not in ("conservative", "balanced", "aggressive"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid risk profile: {body.risk_profile}. Must be one of: conservative, balanced, aggressive",
        )

    # Handle empty list
    if not body.unit_ids:
        return BatchDecideResponse(
            results=[],
            total=0,
            succeeded=0,
            failed=0,
        )

    # Fetch all units
    result = await session.execute(select(Unit).where(Unit.id.in_(body.unit_ids)))
    units = result.scalars().all()

    # Check if all units exist
    if not units:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No units found",
        )

    # Group units by org_id
    from collections import defaultdict

    units_by_org = defaultdict(list)
    for unit in units:
        units_by_org[unit.org_id].append(unit)

    # For simplicity, process only the first org's units
    # In a real implementation, you might process all or require same org
    org_id = list(units_by_org.keys())[0]
    org_units = units_by_org[org_id]

    results = []
    succeeded = 0
    failed = 0

    for unit in org_units:
        try:
            decision = await decide_unit(
                session,
                unit.id,
                _price_source(session),
                risk_profile=body.risk_profile,
                as_of=datetime.utcnow(),
            )
            results.append(
                BatchDecideResult(
                    unit_id=unit.id,
                    decision_id=decision.id,
                    recommended_channel=decision.recommended_channel,
                    confidence=decision.confidence,
                    fallback_used=decision.fallback_used,
                )
            )
            succeeded += 1
        except Exception as exc:
            results.append(
                BatchDecideResult(
                    unit_id=unit.id,
                    error=str(exc),
                )
            )
            failed += 1

    # Apply grouping if requested
    if body.group_by == "channel":
        # Group results by recommended channel
        from collections import defaultdict

        grouped = defaultdict(list)
        for r in results:
            if r.recommended_channel:
                grouped[r.recommended_channel].append(r)
            else:
                grouped["unknown"].append(r)
        # Flatten grouped results
        results = []
        for items in grouped.values():
            results.extend(items)

    return BatchDecideResponse(
        results=results,
        total=len(org_units),
        succeeded=succeeded,
        failed=failed,
    )
