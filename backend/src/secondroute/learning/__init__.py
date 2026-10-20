"""
Learning loop module for Phase 6.

Provides model registry, shadow mode, promotion gate, drift monitoring, and other learning features.
"""

from secondroute.learning.drift import (
    DriftMonitor,
    PSIRResult,
    CalibrationDriftResult,
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
    "DriftMonitor",
    "PSIRResult",
    "CalibrationDriftResult",
    "ModelRegistry",
    "ModelVersion",
    "ModelVersionRecord",
    "PromotionGate",
    "PromotionRecord",
    "PromotionResult",
    "ShadowModeService",
    "ShadowPrediction",
    "ShadowResult",
]