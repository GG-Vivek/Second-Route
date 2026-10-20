"""
Learning loop module for Phase 6.

Provides model registry, shadow mode, promotion gate, and other learning features.
"""

from secondroute.learning.registry import ModelRegistry, ModelVersion, ModelVersionRecord
from secondroute.learning.shadow import (
    ShadowModeService,
    ShadowPrediction,
    ShadowResult,
)

__all__ = [
    "ModelRegistry",
    "ModelVersion",
    "ModelVersionRecord",
    "ShadowModeService",
    "ShadowPrediction",
    "ShadowResult",
]