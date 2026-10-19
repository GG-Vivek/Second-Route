"""
Identity module for Phase 1.

Provides SKU catalog and serial prefix lookup functionality.
"""

from secondroute.identity.api import router as identity_router
from secondroute.identity.models import SKU, SerialPrefix
from secondroute.identity.schemas import (
    SerialPrefixBase,
    SerialPrefixCreate,
    SerialPrefixRead,
    SKUBase,
    SKUCreate,
    SKULookupError,
    SKULookupResponse,
    SKURead,
)

__all__ = [
    "identity_router",
    "SKU",
    "SerialPrefix",
    "SKUBase",
    "SKUCreate",
    "SKURead",
    "SKULookupError",
    "SKULookupResponse",
    "SerialPrefixBase",
    "SerialPrefixCreate",
    "SerialPrefixRead",
]
