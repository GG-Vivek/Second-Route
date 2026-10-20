"""
Partner integrations via open APIs for Phase 7 (F7.5).

Adapter pattern for partner integrations with contract tests and written agreements.
"""

from secondroute.integrations.adapter import (
    PartnerAdapter,
    PartnerConfig,
    PartnerIntegration,
    IntegrationContract,
    IntegrationResult,
)

__all__ = [
    "PartnerAdapter",
    "PartnerConfig",
    "PartnerIntegration",
    "IntegrationContract",
    "IntegrationResult",
]
