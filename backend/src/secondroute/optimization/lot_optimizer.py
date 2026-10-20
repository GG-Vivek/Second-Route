"""
Lot and batch optimization for Phase 7 (F7.2).

Groups units by destination (liquidator lot, refurb batch, shipment) to
optimize shipping and lot discounts. Reduces total logistics cost versus
per-unit baseline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence
from uuid import UUID

import structlog
from pydantic import BaseModel, ConfigDict

logger = structlog.get_logger(__name__)


@dataclass
class UnitInfo:
    """Information about a unit for optimization.

    Attributes:
        unit_id: Unit identifier.
        destination: Target destination (e.g., "liquidator", "refurb", "recycle").
        weight_kg: Weight in kilograms.
        value: Estimated value in USD.
        sku_family: SKU family.
        grade: Condition grade.
    """

    unit_id: UUID
    destination: str
    weight_kg: float
    value: float
    sku_family: str = ""
    grade: str = "B"


@dataclass
class LotGroup:
    """A group of units going to the same destination.

    Attributes:
        destination: Target destination.
        units: List of unit IDs in this group.
        total_weight_kg: Total weight of the group.
        total_value: Total value of the group.
        logistics_cost: Optimized logistics cost for the group.
        per_unit_cost: Cost per unit in the group.
        discount_applied: Discount applied (0-1).
    """

    destination: str
    units: list[UUID] = field(default_factory=list)
    total_weight_kg: float = 0.0
    total_value: float = 0.0
    logistics_cost: float = 0.0
    per_unit_cost: float = 0.0
    discount_applied: float = 0.0

    @property
    def unit_count(self) -> int:
        return len(self.units)


@dataclass
class LotOptimizationResult:
    """Result of lot optimization.

    Attributes:
        groups: List of optimized lot groups.
        total_logistics_cost: Total optimized logistics cost.
        baseline_cost: Total cost if shipped per-unit.
        savings: Savings from optimization.
        savings_pct: Percentage savings.
    """

    groups: list[LotGroup] = field(default_factory=list)
    total_logistics_cost: float = 0.0
    baseline_cost: float = 0.0
    savings: float = 0.0
    savings_pct: float = 0.0


class LotOptimizer:
    """Optimizer for grouping units into lots/batches.

    Groups units by destination to optimize shipping costs through:
    - Volume discounts for larger lots
    - Shared shipping for same destination
    - Weight-based pricing tiers
    """

    # Shipping rate per kg by destination
    SHIPPING_RATES: dict[str, float] = {
        "liquidator": 2.0,  # $/kg
        "refurb": 1.5,
        "recycle": 0.5,
        "donate": 0.3,
        "resell": 2.5,
    }

    # Volume discounts (min units -> discount %)
    VOLUME_DISCOUNTS: list[tuple[int, float]] = [
        (1, 0.0),  # No discount for single unit
        (5, 0.05),  # 5% for 5+ units
        (10, 0.10),  # 10% for 10+ units
        (20, 0.15),  # 15% for 20+ units
        (50, 0.20),  # 20% for 50+ units
    ]

    # Minimum lot size for shipping discount
    MIN_LOT_SIZE = 3

    # Fixed cost per shipment (regardless of size)
    FIXED_SHIPMENT_COST = 5.0

    def __init__(
        self,
        shipping_rates: dict[str, float] | None = None,
        volume_discounts: list[tuple[int, float]] | None = None,
    ) -> None:
        self.shipping_rates = shipping_rates or self.SHIPPING_RATES
        self.volume_discounts = volume_discounts or self.VOLUME_DISCOUNTS

    def _get_volume_discount(self, unit_count: int) -> float:
        """Get volume discount for a given unit count."""
        discount = 0.0
        for min_units, disc in sorted(self.volume_discounts):
            if unit_count >= min_units:
                discount = disc
        return discount

    def _compute_baseline_cost(self, units: list[UnitInfo]) -> float:
        """Compute per-unit shipping cost (baseline)."""
        total = 0.0
        for unit in units:
            rate = self.shipping_rates.get(unit.destination, 2.0)
            total += rate * unit.weight_kg + self.FIXED_SHIPMENT_COST
        return total

    def _compute_group_cost(self, group: LotGroup, rate: float) -> float:
        """Compute optimized cost for a group."""
        weight_cost = rate * group.total_weight_kg
        discount = self._get_volume_discount(group.unit_count)
        discounted_weight_cost = weight_cost * (1 - discount)
        return discounted_weight_cost + self.FIXED_SHIPMENT_COST

    def optimize(
        self,
        units: list[UnitInfo],
    ) -> LotOptimizationResult:
        """Optimize logistics by grouping units by destination.

        Args:
            units: List of units to optimize.

        Returns:
            LotOptimizationResult with optimized groups and savings.
        """
        # Compute baseline (per-unit shipping)
        baseline_cost = self._compute_baseline_cost(units)

        # Group units by destination
        groups_by_destination: dict[str, list[UnitInfo]] = {}
        for unit in units:
            groups_by_destination.setdefault(unit.destination, []).append(unit)

        # Create optimized groups
        optimized_groups = []
        total_optimized_cost = 0.0

        for destination, dest_units in groups_by_destination.items():
            rate = self.shipping_rates.get(destination, 2.0)

            # Sort by value (highest first) for better lot composition
            dest_units.sort(key=lambda u: u.value, reverse=True)

            # Create group
            group = LotGroup(
                destination=destination,
                units=[u.unit_id for u in dest_units],
                total_weight_kg=sum(u.weight_kg for u in dest_units),
                total_value=sum(u.value for u in dest_units),
            )

            # Compute cost with volume discount
            group.logistics_cost = self._compute_group_cost(group, rate)
            group.discount_applied = self._get_volume_discount(group.unit_count)
            group.per_unit_cost = (
                group.logistics_cost / group.unit_count if group.unit_count > 0 else 0.0
            )

            optimized_groups.append(group)
            total_optimized_cost += group.logistics_cost

        # Compute savings
        savings = baseline_cost - total_optimized_cost
        savings_pct = (savings / baseline_cost * 100) if baseline_cost > 0 else 0.0

        return LotOptimizationResult(
            groups=optimized_groups,
            total_logistics_cost=total_optimized_cost,
            baseline_cost=baseline_cost,
            savings=savings,
            savings_pct=savings_pct,
        )

    def optimize_with_splitting(
        self,
        units: list[UnitInfo],
        max_lot_size: int = 20,
    ) -> LotOptimizationResult:
        """Optimize with lot splitting for very large groups.

        Splits large groups into smaller lots to balance shipping costs
        and handling.

        Args:
            units: List of units to optimize.
            max_lot_size: Maximum units per lot.

        Returns:
            LotOptimizationResult with optimized groups.
        """
        baseline_cost = self._compute_baseline_cost(units)

        # Group by destination
        groups_by_destination: dict[str, list[UnitInfo]] = {}
        for unit in units:
            groups_by_destination.setdefault(unit.destination, []).append(unit)

        optimized_groups = []
        total_optimized_cost = 0.0

        for destination, dest_units in groups_by_destination.items():
            rate = self.shipping_rates.get(destination, 2.0)

            # Sort by value
            dest_units.sort(key=lambda u: u.value, reverse=True)

            # Split into lots
            for i in range(0, len(dest_units), max_lot_size):
                lot_units = dest_units[i : i + max_lot_size]

                group = LotGroup(
                    destination=destination,
                    units=[u.unit_id for u in lot_units],
                    total_weight_kg=sum(u.weight_kg for u in lot_units),
                    total_value=sum(u.value for u in lot_units),
                )

                group.logistics_cost = self._compute_group_cost(group, rate)
                group.discount_applied = self._get_volume_discount(group.unit_count)
                group.per_unit_cost = (
                    group.logistics_cost / group.unit_count if group.unit_count > 0 else 0.0
                )

                optimized_groups.append(group)
                total_optimized_cost += group.logistics_cost

        savings = baseline_cost - total_optimized_cost
        savings_pct = (savings / baseline_cost * 100) if baseline_cost > 0 else 0.0

        return LotOptimizationResult(
            groups=optimized_groups,
            total_logistics_cost=total_optimized_cost,
            baseline_cost=baseline_cost,
            savings=savings,
            savings_pct=savings_pct,
        )
