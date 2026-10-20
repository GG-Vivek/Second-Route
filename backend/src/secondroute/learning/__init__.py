"""
Learning loop module for Phase 6.

Provides model registry, shadow mode, promotion gate, drift monitoring,
controlled exploration, Thompson sampling, off-policy evaluation, photo
condition assist and the monthly expert review.
"""

from secondroute.learning.bandit import (
    BanditArm,
    BanditState,
    ThompsonSampler,
    simulate_bandit,
    simulate_random_choice,
)
from secondroute.learning.drift import (
    CalibrationDriftResult,
    DriftMonitor,
    PSIRResult,
)
from secondroute.learning.expert_review import (
    DEFAULT_SAMPLE_SIZE,
    ExpertReviewLabel,
    ExpertReviewService,
    ExpertReviewSummary,
    ReviewSample,
)
from secondroute.learning.exploration import (
    DEFAULT_EXPLORATION_CAP,
    ExplorationEligibility,
    ExplorationService,
    HIGH_VALUE_THRESHOLD,
)
from secondroute.learning.off_policy import (
    LoggedDecision,
    OffPolicyEvaluator,
    PolicyValue,
    simulate_off_policy_evaluation,
)
from secondroute.learning.photo_assist import (
    ALLOWED_MODEL_LICENSES,
    DamageDetector,
    MAX_GRADE_CHANGE,
    PhotoAssistResult,
    PhotoConditionAssist,
    PhotoQualityChecker,
    PhotoQualityResult,
    SerialReader,
)
from secondroute.learning.promotion import (
    PromotionGate,
    PromotionRecord,
    PromotionResult,
)
from secondroute.learning.registry import (
    ModelRegistry,
    ModelVersion,
    ModelVersionRecord,
    compute_training_data_hash,
)
from secondroute.learning.shadow import (
    ShadowModeService,
    ShadowPrediction,
    ShadowResult,
)

__all__ = [
    "ALLOWED_MODEL_LICENSES",
    "BanditArm",
    "BanditState",
    "CalibrationDriftResult",
    "DEFAULT_EXPLORATION_CAP",
    "DEFAULT_SAMPLE_SIZE",
    "DamageDetector",
    "DriftMonitor",
    "ExplorationEligibility",
    "ExplorationService",
    "ExpertReviewLabel",
    "ExpertReviewService",
    "ExpertReviewSummary",
    "HIGH_VALUE_THRESHOLD",
    "LoggedDecision",
    "MAX_GRADE_CHANGE",
    "ModelRegistry",
    "ModelVersion",
    "ModelVersionRecord",
    "OffPolicyEvaluator",
    "PSIRResult",
    "PhotoAssistResult",
    "PhotoConditionAssist",
    "PhotoQualityChecker",
    "PhotoQualityResult",
    "PolicyValue",
    "PromotionGate",
    "PromotionRecord",
    "PromotionResult",
    "ReviewSample",
    "SerialReader",
    "ShadowModeService",
    "ShadowPrediction",
    "ShadowResult",
    "ThompsonSampler",
    "compute_training_data_hash",
    "simulate_bandit",
    "simulate_off_policy_evaluation",
    "simulate_random_choice",
]
