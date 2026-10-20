"""
Learning loop module for Phase 6.

Provides model registry, shadow mode, promotion gate, drift monitoring,
controlled exploration, and other learning features.
"""

from secondroute.learning.drift import (
    CalibrationDriftResult,
    DriftMonitor,
    PSIRResult,
)
from secondroute.learning.exploration import (
    DEFAULT_EXPLORATION_CAP,
    ExplorationEligibility,
    ExplorationService,
    HIGH_VALUE_THRESHOLD,
)
from secondroute.learning.promotion import (
    PromotionGate,
    PromotionRecord,
    PromotionResult,
)
from secondroute.learning.registry import ModelRegistry, ModelVersion, ModelVersionRecord
from secondroute.learning.shadow import (
    ShadowModeService,
    ShadowPrediction,
    ShadowResult,
)

__all__ = [
    "CalibrationDriftResult",
    "DEFAULT_EXPLORATION_CAP",
    "DriftMonitor",
    "ExplorationEligibility",
    "ExplorationService",
    "HIGH_VALUE_THRESHOLD",
    "ModelRegistry",
    "ModelVersion",
    "ModelVersionRecord",
    "PSIRResult",
    "PromotionGate",
    "PromotionRecord",
    "PromotionResult",
    "ShadowModeService",
    "ShadowPrediction",
    "ShadowResult",
]