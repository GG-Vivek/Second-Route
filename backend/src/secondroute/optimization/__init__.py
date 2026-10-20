"""
Lot and batch optimization for Phase 7 (F7.2).

Groups units by destination to optimize shipping and lot discounts.
"""

from secondroute.optimization.lot_optimizer import (
    LotOptimizer,
    LotGroup,
    LotOptimizationResult,
)

__all__ = [
    "LotOptimizer",
    "LotGroup",
    "LotOptimizationResult",
]
