"""
Intake module for Phase 1.

Provides unit intake and inspection record functionality.
"""

from secondroute.intake.api import router as intake_router
from secondroute.intake.models import (
    Inspection,
    OrderChannel,
    Photo,
    ReturnReasonCode,
    Unit,
    UnitStatus,
)
from secondroute.intake.schemas import (
    InspectionCreate,
    InspectionRead,
    PhotoCreate,
    PhotoRead,
    UnitCreate,
    UnitDetailRead,
    UnitRead,
    UnitStatusUpdate,
)

__all__ = [
    "intake_router",
    "Unit",
    "Inspection",
    "Photo",
    "UnitStatus",
    "ReturnReasonCode",
    "OrderChannel",
    "UnitCreate",
    "UnitRead",
    "UnitDetailRead",
    "UnitStatusUpdate",
    "InspectionCreate",
    "InspectionRead",
    "PhotoCreate",
    "PhotoRead",
]
