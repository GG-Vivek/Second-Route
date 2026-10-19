"""
Shared fixtures for the Phase 2 decision engine tests.
"""

from __future__ import annotations

from datetime import date, datetime, timezone, UTC
from typing import Any
from uuid import UUID, uuid4

import pytest

from secondroute.condition.grades import InspectionSignals
from secondroute.costs.defaults import default_cost_seeds
from secondroute.costs.service import CostBook, CostBookEntry
from secondroute.decision.evaluator import EvaluationInput
from secondroute.pricing.protocols import PriceDistribution


def build_cost_book(overrides: dict[tuple[str, str], float] | None = None) -> CostBook:
    """Build a cost book from the defaults, with optional overrides.

    Args:
        overrides: ``(kind, key) -> value`` pairs to replace.

    Returns:
        The cost book.
    """
    entries: dict[tuple[str, str], CostBookEntry] = {}
    for seed in default_cost_seeds():
        entries[(seed.kind, seed.key)] = CostBookEntry(
            kind=seed.kind,
            key=seed.key,
            value=seed.value,
            source=seed.source,
            as_of=seed.as_of,
        )
    for (kind, key), value in (overrides or {}).items():
        entries[(kind, key)] = CostBookEntry(
            kind=kind,
            key=key,
            value=float(value),
            source="test_override",
            as_of=date(2025, 1, 1),
        )
    return CostBook(entries=entries)


class FixedPriceSource:
    """A price source that returns a fixed distribution per cell.

    Used to build exact fixtures: every channel/grade cell gets the same
    mean and spread unless overridden.
    """

    def __init__(
        self,
        means: dict[tuple[str, str], float],
        *,
        stddev: float = 0.0,
        source_tag: str = "fixture",
        observations: int = 32,
    ) -> None:
        self.means = means
        self.stddev = stddev
        self.source_tag = source_tag
        self.observations = observations
        self.calls: list[tuple[UUID, str, str]] = []

    async def get_distribution(
        self,
        sku_id: UUID,
        grade: str,
        channel: str,
        as_of: datetime,
    ) -> PriceDistribution:
        """Return the fixture distribution for one cell."""
        self.calls.append((sku_id, grade, channel))
        mean = self.means.get((grade, channel))
        if mean is None:
            mean = self.means.get((grade, "*"), 100.0)
        return PriceDistribution.from_parameters(
            mean=mean,
            stddev=self.stddev,
            source=self.source_tag,
            as_of=as_of,
            observations=self.observations,
            lognormal=False,
            minimum=0.0,
        )


@pytest.fixture
def cost_book() -> CostBook:
    """Return the default cost book."""
    return build_cost_book()


@pytest.fixture
def good_signals() -> InspectionSignals:
    """Return inspection signals for a healthy unit."""
    return InspectionSignals(
        battery_health_pct=95.0,
        battery_cycles=120,
        cosmetic_grade="A",
        functional_tests={
            "display": True,
            "keyboard": True,
            "ports": True,
            "audio": True,
            "camera": True,
        },
        accessories={"charger": True, "box": True, "cable": True},
        activation_lock="none",
    )


@pytest.fixture
def poor_signals() -> InspectionSignals:
    """Return inspection signals for a badly worn unit."""
    return InspectionSignals(
        battery_health_pct=68.0,
        battery_cycles=780,
        cosmetic_grade="D",
        functional_tests={
            "display": False,
            "keyboard": True,
            "ports": False,
            "audio": True,
            "camera": False,
        },
        accessories={"charger": False},
        activation_lock="none",
    )


@pytest.fixture
def locked_signals() -> InspectionSignals:
    """Return inspection signals for a unit with an activation lock."""
    return InspectionSignals(
        battery_health_pct=95.0,
        battery_cycles=100,
        cosmetic_grade="A",
        functional_tests={"display": True, "keyboard": True},
        accessories={"charger": True},
        activation_lock="present",
    )


@pytest.fixture
def sku_id() -> UUID:
    """Return a stable SKU id for the tests."""
    return UUID("11111111-2222-3333-4444-555555555555")


@pytest.fixture
def evaluation_input(
    cost_book: CostBook, good_signals: InspectionSignals, sku_id: UUID
) -> EvaluationInput:
    """Return a ready-to-evaluate input for a healthy unit."""
    return EvaluationInput(
        sku_id=sku_id,
        signals=good_signals,
        cost_book=cost_book,
        as_of=datetime(2025, 6, 1, tzinfo=UTC),
    )


def make_means(**overrides: dict[str, float]) -> dict[tuple[str, str], float]:
    """Build a ``(grade, channel) -> mean`` mapping.

    Args:
        overrides: ``channel -> {grade: mean}`` pairs.

    Returns:
        The flattened mapping.
    """
    means: dict[tuple[str, str], float] = {}
    for channel, grades in overrides.items():
        for grade, value in grades.items():
            means[(grade, channel)] = value
    return means


def as_float(value: Any) -> float:
    """Coerce a value to float for comparisons."""
    return float(value)
