"""
Fraud and wardrobing signals for Phase 7 (F7.3).

Flags for serial mismatch, component swap, and activation lock mismatch.
Flags go to a review queue. They never auto-reject a return.
"""

from secondroute.fraud.detector import (
    FraudDetector,
    FraudFlag,
    FraudFlagType,
    FraudReviewQueue,
)

__all__ = [
    "FraudDetector",
    "FraudFlag",
    "FraudFlagType",
    "FraudReviewQueue",
]
