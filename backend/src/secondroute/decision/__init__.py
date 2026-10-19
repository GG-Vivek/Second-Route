"""Decision engine (Phase 2 - F2.5 to F2.9)."""

from secondroute.decision.confidence import (
    SAFE_DEFAULT,
    ConfidenceResult,
    apply_confidence_gate,
    compute_confidence,
    highest_p10_channel,
)
from secondroute.decision.engine import (
    DECISION_MODEL_VERSION,
    DecisionOutcome,
    decide_unit,
    run_decision,
)
from secondroute.decision.evaluator import (
    PHASE2_CHANNELS,
    ChannelEvaluation,
    CostBreakdown,
    EvaluationInput,
    EvaluationResult,
    evaluate_channels,
)
from secondroute.decision.explanations import (
    FlipCondition,
    Reason,
    build_flip_conditions,
    build_reasons,
)
from secondroute.decision.models import Decision, hash_snapshot
from secondroute.decision.utility import (
    RISK_PROFILES,
    certainty_equivalent,
    lambda_for,
    rank_channels,
)

__all__ = [
    "DECISION_MODEL_VERSION",
    "ChannelEvaluation",
    "ConfidenceResult",
    "CostBreakdown",
    "Decision",
    "DecisionOutcome",
    "EvaluationInput",
    "EvaluationResult",
    "FlipCondition",
    "PHASE2_CHANNELS",
    "RISK_PROFILES",
    "Reason",
    "SAFE_DEFAULT",
    "apply_confidence_gate",
    "build_flip_conditions",
    "build_reasons",
    "certainty_equivalent",
    "compute_confidence",
    "decide_unit",
    "evaluate_channels",
    "hash_snapshot",
    "highest_p10_channel",
    "lambda_for",
    "rank_channels",
    "run_decision",
]
