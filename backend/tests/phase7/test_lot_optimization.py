"""
Tests for lot and batch optimization (Phase 7 - F7.2).
"""

import pytest
from uuid import uuid4

from secondroute.optimization.lot_optimizer import (
    LotOptimizer,
    UnitInfo,
    LotGroup,
    LotOptimizationResult,
)


class TestLotOptimizer:
    """Tests for LotOptimizer."""

    def test_optimize_reduces_cost(self) -> None:
        """Test that grouping reduces total logistics cost."""
        optimizer = LotOptimizer()

        # Create units going to the same destination
        units = [
            UnitInfo(
                unit_id=uuid4(),
                destination="liquidator",
                weight_kg=1.0,
                value=500.0,
            )
            for _ in range(10)
        ]

        result = optimizer.optimize(units)

        # Grouped cost should be less than per-unit baseline
        assert result.total_logistics_cost < result.baseline_cost
        assert result.savings > 0
        assert result.savings_pct > 0

    def test_optimize_multiple_destinations(self) -> None:
        """Test optimization with multiple destinations."""
        optimizer = LotOptimizer()

        units = [
            UnitInfo(unit_id=uuid4(), destination="liquidator", weight_kg=1.0, value=500.0)
            for _ in range(5)
        ] + [
            UnitInfo(unit_id=uuid4(), destination="refurb", weight_kg=1.0, value=300.0)
            for _ in range(5)
        ]

        result = optimizer.optimize(units)

        assert len(result.groups) == 2
        assert result.total_logistics_cost < result.baseline_cost
        assert result.savings > 0

    def test_volume_discount_applied(self) -> None:
        """Test that volume discounts are applied."""
        optimizer = LotOptimizer()

        # 10 units to same destination should get 10% discount
        units = [
            UnitInfo(unit_id=uuid4(), destination="liquidator", weight_kg=1.0, value=500.0)
            for _ in range(10)
        ]

        result = optimizer.optimize(units)

        assert len(result.groups) == 1
        group = result.groups[0]
        assert group.discount_applied == 0.10
        assert group.unit_count == 10

    def test_small_lot_no_discount(self) -> None:
        """Test that small lots get no discount."""
        optimizer = LotOptimizer()

        units = [
            UnitInfo(unit_id=uuid4(), destination="liquidator", weight_kg=1.0, value=500.0)
            for _ in range(2)
        ]

        result = optimizer.optimize(units)

        group = result.groups[0]
        assert group.discount_applied == 0.0

    def test_baseline_cost_calculation(self) -> None:
        """Test baseline cost calculation."""
        optimizer = LotOptimizer()

        units = [
            UnitInfo(unit_id=uuid4(), destination="liquidator", weight_kg=1.0, value=500.0),
            UnitInfo(unit_id=uuid4(), destination="refurb", weight_kg=1.0, value=300.0),
        ]

        baseline = optimizer._compute_baseline_cost(units)
        # Each unit: rate * weight + fixed cost
        # liquidator: 2.0 * 1.0 + 5.0 = 7.0
        # refurb: 1.5 * 1.0 + 5.0 = 6.5
        # Total: 13.5
        assert baseline == 13.5

    def test_group_cost_calculation(self) -> None:
        """Test group cost calculation."""
        optimizer = LotOptimizer()

        group = LotGroup(
            destination="liquidator",
            units=[uuid4() for _ in range(5)],
            total_weight_kg=5.0,
        )

        cost = optimizer._compute_group_cost(group, rate=2.0)
        # weight_cost = 2.0 * 5.0 = 10.0
        # discount = 5% (for 5+ units)
        # discounted = 10.0 * 0.95 = 9.5
        # total = 9.5 + 5.0 (fixed) = 14.5
        assert cost == 14.5

    def test_optimize_with_splitting(self) -> None:
        """Test optimization with lot splitting."""
        optimizer = LotOptimizer()

        units = [
            UnitInfo(unit_id=uuid4(), destination="liquidator", weight_kg=1.0, value=500.0)
            for _ in range(25)
        ]

        result = optimizer.optimize_with_splitting(units, max_lot_size=10)

        # Should create 3 lots (10 + 10 + 5)
        assert len(result.groups) == 3
        assert result.total_logistics_cost < result.baseline_cost

    def test_empty_units(self) -> None:
        """Test optimization with no units."""
        optimizer = LotOptimizer()
        result = optimizer.optimize([])

        assert result.total_logistics_cost == 0.0
        assert result.baseline_cost == 0.0
        assert result.savings == 0.0
        assert len(result.groups) == 0

    def test_single_unit(self) -> None:
        """Test optimization with a single unit."""
        optimizer = LotOptimizer()

        units = [
            UnitInfo(unit_id=uuid4(), destination="liquidator", weight_kg=1.0, value=500.0),
        ]

        result = optimizer.optimize(units)

        assert len(result.groups) == 1
        assert result.total_logistics_cost > 0
        # Single unit: no volume discount
        assert result.groups[0].discount_applied == 0.0

    def test_different_shipping_rates(self) -> None:
        """Test that different destinations use different rates."""
        optimizer = LotOptimizer()

        liquidator_units = [
            UnitInfo(unit_id=uuid4(), destination="liquidator", weight_kg=1.0, value=500.0)
            for _ in range(5)
        ]
        recycle_units = [
            UnitInfo(unit_id=uuid4(), destination="recycle", weight_kg=1.0, value=50.0)
            for _ in range(5)
        ]

        result = optimizer.optimize(liquidator_units + recycle_units)

        assert len(result.groups) == 2
        # Recycle should have lower shipping rate
        recycle_group = [g for g in result.groups if g.destination == "recycle"][0]
        liquidator_group = [g for g in result.groups if g.destination == "liquidator"][0]
        assert recycle_group.per_unit_cost < liquidator_group.per_unit_cost

    def test_custom_shipping_rates(self) -> None:
        """Test with custom shipping rates."""
        custom_rates = {"liquidator": 1.0, "refurb": 0.5}
        optimizer = LotOptimizer(shipping_rates=custom_rates)

        units = [
            UnitInfo(unit_id=uuid4(), destination="liquidator", weight_kg=1.0, value=500.0)
            for _ in range(5)
        ]

        result = optimizer.optimize(units)
        assert len(result.groups) == 1

    def test_lot_group_properties(self) -> None:
        """Test LotGroup properties."""
        group = LotGroup(
            destination="liquidator",
            units=[uuid4() for _ in range(5)],
            total_weight_kg=5.0,
            total_value=2500.0,
        )

        assert group.unit_count == 5
        assert group.destination == "liquidator"
