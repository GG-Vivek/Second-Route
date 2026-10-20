"""
Decision engine orchestrator (Phase 2 - F2.9).

Ties the pieces together:

    inspection -> grade distribution -> eligibility -> Monte Carlo evaluation
    -> certainty-equivalent ranking -> confidence gate -> reasons
    -> flip conditions -> action steps -> stored decision

The engine is deterministic. Given the same snapshot (unit, inspection, cost
book, risk profile, samples, seed) it produces the same recommendation, the
same confidence and the same hash.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.condition.grades import (
    GRADES,
    GradeDistribution,
    InspectionSignals,
    channel_eligibility,
    grade_distribution,
)
from secondroute.core.config import settings
from secondroute.core.logging import get_logger
from secondroute.costs.models import CostKind
from secondroute.costs.service import CostBook, load_cost_book
from secondroute.decision.confidence import (
    SAFE_DEFAULT,
    apply_confidence_gate,
)
from secondroute.decision.evaluator import (
    DECISION_CHANNELS,
    ChannelEvaluation,
    EvaluationInput,
    EvaluationResult,
    evaluate_channels,
)
from secondroute.decision.explanations import (
    FlipCondition,
    Reason,
    Recommendation,
    build_flip_conditions,
    build_reasons,
)
from secondroute.decision.hold import HoldPriceSource
from secondroute.decision.models import Decision, hash_snapshot
from secondroute.decision.parts import build_parts_source
from secondroute.decision.utility import certainty_equivalent, rank_channels
from secondroute.ingest.launch import (
    get_decay_param,
    hold_decision,
    list_launch_events,
)
from secondroute.instructions.templates import ActionStep, action_steps_for
from secondroute.pricing.composite import CompositePriceSource
from secondroute.pricing.protocols import PriceSource

logger = get_logger(__name__)

__all__ = [
    "DECISION_MODEL_VERSION",
    "DecisionOutcome",
    "decide_unit",
    "run_decision",
]

#: Version of the decision engine. Stored on every decision.
DECISION_MODEL_VERSION = "decision-v1"

#: Number of samples used for the flip-condition sensitivity search. Lower
#: than the main evaluation because the search runs many evaluations.
FLIP_SEARCH_SAMPLES = 2_000


@dataclass(slots=True)
class DecisionOutcome:
    """Everything a decision produced, before or after persistence."""

    recommended_channel: str
    fallback_used: bool
    fallback_channel: str | None
    confidence: float
    within_margin_share: float
    risk_profile: str
    model_version: str
    candidates: list[dict[str, Any]] = field(default_factory=list)
    reasons: list[Reason] = field(default_factory=list)
    flip_conditions: list[FlipCondition] = field(default_factory=list)
    action_steps: list[ActionStep] = field(default_factory=list)
    data_freshness: dict[str, Any] = field(default_factory=dict)
    input_snapshot: dict[str, Any] = field(default_factory=dict)
    input_snapshot_hash: str = ""
    grade_distribution: dict[str, float] = field(default_factory=dict)
    evaluation: EvaluationResult | None = None

    @property
    def probability_best(self) -> dict[str, float]:
        """Probability each channel has the best net."""
        return self.evaluation.probability_best if self.evaluation else {}


def _signal_payload(signals: InspectionSignals) -> dict[str, Any]:
    """Return the canonical representation of the inspection signals."""
    return {
        "battery_health_pct": signals.battery_health_pct,
        "battery_cycles": signals.battery_cycles,
        "cosmetic_grade": signals.cosmetic_grade,
        "functional_tests": dict(signals.functional_tests),
        "accessories": dict(signals.accessories),
        "activation_lock": signals.activation_lock,
    }


def _dominant_grade(signals: InspectionSignals) -> str:
    """The grade with the highest probability for a unit.

    Used to pick the decay parameters: the decay is fitted per grade, and the
    grade a unit is most likely to be is the one whose decay applies.
    """
    distribution = grade_distribution(signals)
    return distribution.most_likely


def _stale_sources(price_source: Any) -> set[str]:
    """The stale sources behind a price source, when it knows.

    A price source that does not track its own freshness simply has no stale
    sources - it cannot be blamed for what it does not know.
    """
    stale = getattr(price_source, "stale_sources", None)
    if not stale:
        return set()
    return {str(name) for name in stale}


def _degraded_confidence(confidence: float, stale: set[str]) -> float:
    """Reduce the confidence when a source is stale.

    Args:
        confidence: The confidence the gate produced.
        stale: The stale sources.

    Returns:
        The confidence, reduced when a source is stale.
    """
    if not stale:
        return confidence
    return confidence * settings.CONFIDENCE_DEGRADATION_FACTOR


def _cost_book_payload(book: CostBook) -> dict[str, Any]:
    """Return the canonical representation of the cost book."""
    return {f"{kind}:{key}": entry.value for (kind, key), entry in sorted(book.entries.items())}


def _freshness_payload(
    evaluations: Sequence[ChannelEvaluation], book: CostBook, warnings: list[str]
) -> dict[str, Any]:
    """Return the data freshness and provenance payload."""
    price_sources: dict[str, str] = {}
    price_as_of: dict[str, str] = {}
    for evaluation in evaluations:
        for grade, source in evaluation.price_sources.items():
            price_sources[f"{evaluation.channel}:{grade}"] = source
        for grade, as_of in evaluation.price_as_of.items():
            price_as_of[f"{evaluation.channel}:{grade}"] = as_of

    cost_sources: dict[str, str] = {}
    cost_as_of: dict[str, str] = {}
    for (kind, key), entry in sorted(book.entries.items()):
        cost_sources[f"{kind}:{key}"] = entry.source
        cost_as_of[f"{kind}:{key}"] = entry.as_of.isoformat()

    return {
        "price_sources": price_sources,
        "price_as_of": price_as_of,
        "cost_sources": cost_sources,
        "cost_as_of": cost_as_of,
        "is_synthetic": True,
        "warnings": warnings,
    }


def _candidate_payloads(result: EvaluationResult, risk_profile: str) -> list[dict[str, Any]]:
    """Return the JSON payload for every evaluated channel."""
    payloads: list[dict[str, Any]] = []
    for evaluation in result.channels:
        payload = evaluation.as_dict()
        payload["probability_best"] = round(result.probability_best.get(evaluation.channel, 0.0), 6)
        payload["certainty_equivalent"] = round(
            certainty_equivalent(evaluation.mean, evaluation.stddev, risk_profile), 2
        )
        payloads.append(payload)
    return payloads


async def run_decision(
    *,
    unit_id: UUID,
    sku_id: UUID,
    signals: InspectionSignals,
    cost_book: CostBook,
    price_source: PriceSource,
    risk_profile: str = "balanced",
    samples: int | None = None,
    seed: int | None = None,
    threshold: float | None = None,
    as_of: datetime | None = None,
    channels: tuple[str, ...] = DECISION_CHANNELS,
    include_flip_conditions: bool = True,
    extra_eligibility: dict[str, tuple[bool, str | None]] | None = None,
) -> DecisionOutcome:
    """Run the decision engine for one unit.

    Args:
        unit_id: Unit the decision is for.
        sku_id: SKU of the unit.
        signals: Inspection signals.
        cost_book: The cost values to use.
        price_source: Where sale prices come from.
        risk_profile: Risk profile used to rank channels.
        samples: Monte Carlo samples (default from configuration).
        seed: RNG seed (default from configuration).
        threshold: Confidence threshold (default from configuration).
        as_of: Timestamp used to look up prices.
        channels: Channels to evaluate.
        include_flip_conditions: Whether to run the sensitivity search.
        extra_eligibility: Channel eligibility decided outside the grade
            rules - the launch calendar decides whether HOLD is on the table.

    Returns:
        The decision outcome.
    """
    samples = samples if samples is not None else settings.MONTE_CARLO_SAMPLES
    seed = seed if seed is not None else settings.RNG_SEED
    threshold = threshold if threshold is not None else settings.CONFIDENCE_THRESHOLD
    as_of = as_of or datetime.utcnow()

    distribution: GradeDistribution = grade_distribution(signals)
    eligibility = channel_eligibility(signals, distribution)
    if extra_eligibility:
        eligibility.update(extra_eligibility)

    evaluation_input = EvaluationInput(
        sku_id=sku_id,
        signals=signals,
        cost_book=cost_book,
        channels=channels,
        as_of=as_of,
        eligibility=eligibility,
    )

    result = await evaluate_channels(
        evaluation_input,
        price_source,
        samples=samples,
        seed=seed,
        as_of=as_of,
    )

    eligible = result.eligible_channels
    if not eligible:
        raise ValueError("No eligible channel for this unit")

    ranked = rank_channels(result.channels, risk_profile)
    recommended_channel, _ = ranked[0]
    runner_up_channel = ranked[1][0] if len(ranked) > 1 else None

    recommended_index = result.joint_index(recommended_channel)

    gated_channel, fallback_used, confidence_result = apply_confidence_gate(
        result.channels,
        result.joint_draws,
        recommended_index,
        recommended_channel,
        threshold=threshold,
    )

    fallback_channel: str | None = None
    if fallback_used:
        fallback_channel = confidence_result.fallback_channel

    recommended_eval = result.by_channel(recommended_channel)
    runner_up_eval = result.by_channel(runner_up_channel) if runner_up_channel else None
    reasons = (
        build_reasons(recommended_eval, runner_up_eval) if recommended_eval is not None else []
    )

    flip_conditions: list[FlipCondition] = []
    if include_flip_conditions:

        async def recommender(perturbed: EvaluationInput) -> Recommendation:
            """Re-evaluate a perturbed input and return its recommendation."""
            perturbed_result = await evaluate_channels(
                perturbed,
                price_source,
                samples=FLIP_SEARCH_SAMPLES,
                seed=seed,
                as_of=as_of,
            )
            perturbed_ranked = rank_channels(perturbed_result.channels, risk_profile)
            if not perturbed_ranked:
                return Recommendation(
                    channel=SAFE_DEFAULT, gated_channel=SAFE_DEFAULT, fallback_used=True
                )
            perturbed_channel = perturbed_ranked[0][0]
            perturbed_index = perturbed_result.joint_index(perturbed_channel)
            perturbed_gate, perturbed_fallback, _ = apply_confidence_gate(
                perturbed_result.channels,
                perturbed_result.joint_draws,
                perturbed_index,
                perturbed_channel,
                threshold=threshold,
            )
            return Recommendation(
                channel=perturbed_channel,
                gated_channel=perturbed_gate,
                fallback_used=perturbed_fallback,
            )

        flip_conditions = await build_flip_conditions(
            evaluation_input,
            recommender,
            recommended_channel,
        )

    action_steps = action_steps_for(gated_channel, fallback_channel)

    warnings: list[str] = []
    if fallback_used:
        warnings.append(
            "Confidence below the configured threshold - the recommendation falls back "
            "to the most conservative channel available."
        )

    # A stale price source makes the recommendation less trustworthy, so the
    # confidence comes down and the card says why.
    stale = _stale_sources(price_source)
    if stale:
        warnings.append(
            "Some price sources are stale ("
            + ", ".join(sorted(stale))
            + f"); the confidence has been reduced by "
            f"{settings.CONFIDENCE_DEGRADATION_FACTOR:.0%}."
        )

    warnings.append("Prices are synthetic. This is a prototype, not a money claim.")

    snapshot = {
        "unit_id": str(unit_id),
        "sku_id": str(sku_id),
        "signals": _signal_payload(signals),
        "grade_distribution": {
            grade: round(distribution.probabilities[grade], 8) for grade in GRADES
        },
        "eligibility": {
            channel: {"eligible": eligible_flag, "reason": reason}
            for channel, (eligible_flag, reason) in sorted(eligibility.items())
        },
        "cost_book": _cost_book_payload(cost_book),
        "channels": list(channels),
        "risk_profile": risk_profile,
        "samples": samples,
        "seed": seed,
        "threshold": threshold,
        "model_version": DECISION_MODEL_VERSION,
        "as_of": as_of.isoformat(),
    }

    return DecisionOutcome(
        recommended_channel=gated_channel,
        fallback_used=fallback_used,
        fallback_channel=fallback_channel,
        confidence=_degraded_confidence(confidence_result.confidence, _stale_sources(price_source)),
        within_margin_share=confidence_result.within_margin_share,
        risk_profile=risk_profile,
        model_version=DECISION_MODEL_VERSION,
        candidates=_candidate_payloads(result, risk_profile),
        reasons=reasons,
        flip_conditions=flip_conditions,
        action_steps=action_steps,
        data_freshness=_freshness_payload(result.channels, cost_book, warnings),
        input_snapshot=snapshot,
        input_snapshot_hash=hash_snapshot(snapshot),
        grade_distribution=dict(distribution.probabilities),
        evaluation=result,
    )


async def decide_unit(
    session: AsyncSession,
    unit_id: UUID,
    price_source: PriceSource,
    *,
    risk_profile: str = "balanced",
    samples: int | None = None,
    seed: int | None = None,
    threshold: float | None = None,
    as_of: datetime | None = None,
    include_flip_conditions: bool = True,
) -> Decision:
    """Run a decision for a unit and store it.

    Args:
        session: Database session.
        unit_id: Unit to decide.
        price_source: Where sale prices come from.
        risk_profile: Risk profile used to rank channels.
        samples: Monte Carlo samples.
        seed: RNG seed.
        threshold: Confidence threshold.
        as_of: Timestamp used to look up prices.
        include_flip_conditions: Whether to run the sensitivity search.

    Returns:
        The stored decision.

    Raises:
        ValueError: If the unit does not exist or has no inspection.
    """
    from secondroute.identity.models import SKU
    from secondroute.intake.models import Inspection, Unit

    unit = await session.get(Unit, unit_id)
    if unit is None:
        raise ValueError(f"Unit {unit_id} not found")

    inspection_result = await session.execute(
        select(Inspection)
        .where(Inspection.unit_id == unit_id)
        .order_by(Inspection.created_at.desc())
        .limit(1)
    )
    inspection = inspection_result.scalar_one_or_none()
    if inspection is None:
        raise ValueError(f"Unit {unit_id} has no inspection record")

    sku = await session.get(SKU, unit.sku_id)
    family = sku.family if sku is not None else "MacBook Pro"

    signals = InspectionSignals.from_inspection(inspection)
    cost_book = await load_cost_book(session, unit.org_id)

    effective_price_source = price_source
    if hasattr(price_source, "with_family"):
        effective_price_source = price_source.with_family(family)  # type: ignore[attr-defined]

    # The parts channel has its own price source: the value of what is inside
    # the unit, not the value of the unit. Everything else keeps the source
    # the caller passed in.
    parts_source = await build_parts_source(session, unit.id, inspection)

    # HOLD is only on the table when the launch calendar says it is safe.
    launches = await list_launch_events(session, sku_family=family)
    decay = await get_decay_param(session, sku_family=family, grade=_dominant_grade(signals))
    hold = hold_decision(
        rate_per_day=decay.rate_per_day if decay else 0.0,
        launches=launches,
        today=(as_of or datetime.utcnow()).date(),
    )

    channel_sources: dict[str, Any] = {"PARTS_HARVEST": parts_source}
    if hold.offered:
        channel_sources["HOLD"] = HoldPriceSource(
            effective_price_source, hold.expected_change_p50, window_days=hold.window_days
        )

    effective_price_source = CompositePriceSource(channel_sources, effective_price_source)

    # The launch calendar decides whether HOLD is on the table.
    hold_eligibility: dict[str, tuple[bool, str | None]] = {"HOLD": (hold.offered, hold.reason)}

    outcome = await run_decision(
        unit_id=unit.id,
        sku_id=unit.sku_id,
        signals=signals,
        cost_book=cost_book,
        price_source=effective_price_source,
        risk_profile=risk_profile,
        samples=samples,
        seed=seed,
        threshold=threshold,
        as_of=as_of,
        include_flip_conditions=include_flip_conditions,
        extra_eligibility=hold_eligibility,
    )

    decision = Decision(
        unit_id=unit.id,
        org_id=unit.org_id,
        created_at=datetime.utcnow(),
        model_version=outcome.model_version,
        risk_profile=outcome.risk_profile,
        recommended_channel=outcome.recommended_channel,
        confidence=outcome.confidence,
        fallback_used=outcome.fallback_used,
        fallback_channel=outcome.fallback_channel,
        candidates_json=json.dumps(outcome.candidates),
        reasons_json=json.dumps([reason.as_dict() for reason in outcome.reasons]),
        flip_conditions_json=json.dumps([flip.as_dict() for flip in outcome.flip_conditions]),
        data_freshness_json=json.dumps(outcome.data_freshness),
        action_steps_json=json.dumps([step.as_dict() for step in outcome.action_steps]),
        input_snapshot_hash=outcome.input_snapshot_hash,
        input_snapshot_json=json.dumps(outcome.input_snapshot, sort_keys=True),
    )
    session.add(decision)
    await session.flush()

    logger.info(
        "decision_created",
        decision_id=str(decision.id),
        unit_id=str(unit.id),
        channel=decision.recommended_channel,
        confidence=round(decision.confidence, 4),
        fallback_used=decision.fallback_used,
    )
    return decision


def decision_to_dict(decision: Decision) -> dict[str, Any]:
    """Return a JSON-serialisable view of a stored decision."""
    return {
        "id": str(decision.id),
        "unit_id": str(decision.unit_id),
        "created_at": decision.created_at.isoformat(),
        "model_version": decision.model_version,
        "risk_profile": decision.risk_profile,
        "recommended_channel": decision.recommended_channel,
        "confidence": decision.confidence,
        "fallback_used": decision.fallback_used,
        "fallback_channel": decision.fallback_channel,
        "candidates": decision.candidates,
        "reasons": decision.reasons,
        "flip_conditions": decision.flip_conditions,
        "action_steps": decision.action_steps,
        "data_freshness": decision.data_freshness,
        "input_snapshot_hash": decision.input_snapshot_hash,
        "is_prototype": True,
    }


def cost_kind_keys() -> tuple[str, ...]:
    """Return every cost kind the engine reads."""
    return (
        CostKind.CHANNEL_FEE_PCT,
        CostKind.FIXED_FEE,
        CostKind.LOGISTICS_COST,
        CostKind.HANDLING_COST,
        CostKind.REPAIR_COST,
        CostKind.HOLDING_COST_PER_DAY,
        CostKind.EXPECTED_DAYS_TO_SELL,
    )
