"""
Default cost values (Phase 2 - F2.4).

These are the Phase 2 defaults. They are synthetic, clearly tagged as such,
and every one carries a source and an as-of date so the UI can show where the
number came from. Phase 3 replaces them with partner-sourced values through
the admin API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from secondroute.costs.models import CostKind

__all__ = ["DEFAULT_COSTS", "DEFAULT_COST_SOURCE", "CostSeed", "default_cost_seeds"]


DEFAULT_COST_SOURCE = "synthetic_defaults"
DEFAULT_COST_AS_OF = date(2025, 1, 1)


@dataclass(frozen=True, slots=True)
class CostSeed:
    """A single default cost value."""

    kind: str
    key: str
    value: float
    source: str = DEFAULT_COST_SOURCE
    as_of: date = DEFAULT_COST_AS_OF


#: Percentage of the sale price a channel takes as a fee.
_FEE_PCT: dict[str, float] = {
    "RESELL_OPEN_BOX": 0.12,
    "RESELL_REFURB": 0.15,
    "PARTS_HARVEST": 0.0,
    "HOLD": 0.0,
    "RECYCLE": 0.0,
    "DONATE": 0.0,
}

#: Fixed per-unit transaction fee.
_FIXED_FEE: dict[str, float] = {
    "RESELL_OPEN_BOX": 25.0,
    "RESELL_REFURB": 20.0,
    "PARTS_HARVEST": 0.0,
    "HOLD": 0.0,
    "RECYCLE": 6.0,
    "DONATE": 9.0,
}

#: Outbound logistics cost per unit.
_LOGISTICS: dict[str, float] = {
    "RESELL_OPEN_BOX": 28.0,
    "RESELL_REFURB": 24.0,
    "PARTS_HARVEST": 12.0,
    "HOLD": 0.0,
    "RECYCLE": 18.0,
    "DONATE": 22.0,
}

#: Handling cost per unit (photography, labelling, repacking, ...).
_HANDLING: dict[str, float] = {
    "RESELL_OPEN_BOX": 18.0,
    "RESELL_REFURB": 65.0,
    "PARTS_HARVEST": 25.0,
    "HOLD": 5.0,
    "RECYCLE": 8.0,
    "DONATE": 12.0,
}

#: Cost of holding a unit for one day.
_HOLDING_PER_DAY: dict[str, float] = {
    "RESELL_OPEN_BOX": 0.30,
    "RESELL_REFURB": 0.55,
    "PARTS_HARVEST": 0.10,
    "HOLD": 0.05,
    "RECYCLE": 0.20,
    "DONATE": 0.25,
}

#: Expected repair cost, by channel and grade.
_REPAIR: dict[tuple[str, str], float] = {
    ("RESELL_OPEN_BOX", "A"): 0.0,
    ("RESELL_OPEN_BOX", "B"): 15.0,
    ("RESELL_OPEN_BOX", "C"): 45.0,
    ("RESELL_OPEN_BOX", "D"): 120.0,
    ("RESELL_REFURB", "A"): 40.0,
    ("RESELL_REFURB", "B"): 90.0,
    ("RESELL_REFURB", "C"): 180.0,
    ("RESELL_REFURB", "D"): 320.0,
    ("PARTS_HARVEST", "A"): 0.0,
    ("PARTS_HARVEST", "B"): 0.0,
    ("PARTS_HARVEST", "C"): 0.0,
    ("PARTS_HARVEST", "D"): 0.0,
    ("HOLD", "A"): 0.0,
    ("HOLD", "B"): 0.0,
    ("HOLD", "C"): 0.0,
    ("HOLD", "D"): 0.0,
    ("RECYCLE", "A"): 0.0,
    ("RECYCLE", "B"): 0.0,
    ("RECYCLE", "C"): 0.0,
    ("RECYCLE", "D"): 0.0,
    ("DONATE", "A"): 0.0,
    ("DONATE", "B"): 0.0,
    ("DONATE", "C"): 0.0,
    ("DONATE", "D"): 0.0,
}

#: Expected days to sell, by channel and grade.
_DAYS_TO_SELL: dict[tuple[str, str], float] = {
    ("RESELL_OPEN_BOX", "A"): 3.0,
    ("RESELL_OPEN_BOX", "B"): 5.0,
    ("RESELL_OPEN_BOX", "C"): 9.0,
    ("RESELL_OPEN_BOX", "D"): 14.0,
    ("RESELL_REFURB", "A"): 6.0,
    ("RESELL_REFURB", "B"): 9.0,
    ("RESELL_REFURB", "C"): 15.0,
    ("RESELL_REFURB", "D"): 24.0,
    ("PARTS_HARVEST", "A"): 5.0,
    ("PARTS_HARVEST", "B"): 5.0,
    ("PARTS_HARVEST", "C"): 6.0,
    ("PARTS_HARVEST", "D"): 7.0,
    ("HOLD", "A"): 21.0,
    ("HOLD", "B"): 21.0,
    ("HOLD", "C"): 21.0,
    ("HOLD", "D"): 21.0,
    ("RECYCLE", "A"): 3.0,
    ("RECYCLE", "B"): 3.0,
    ("RECYCLE", "C"): 3.0,
    ("RECYCLE", "D"): 3.0,
    ("DONATE", "A"): 5.0,
    ("DONATE", "B"): 5.0,
    ("DONATE", "C"): 5.0,
    ("DONATE", "D"): 5.0,
}


def default_cost_seeds() -> list[CostSeed]:
    """Return every default cost seed, in a stable order."""
    seeds: list[CostSeed] = []

    for channel, value in _FEE_PCT.items():
        seeds.append(CostSeed(CostKind.CHANNEL_FEE_PCT, channel, value))
    for channel, value in _FIXED_FEE.items():
        seeds.append(CostSeed(CostKind.FIXED_FEE, channel, value))
    for channel, value in _LOGISTICS.items():
        seeds.append(CostSeed(CostKind.LOGISTICS_COST, channel, value))
    for channel, value in _HANDLING.items():
        seeds.append(CostSeed(CostKind.HANDLING_COST, channel, value))
    for channel, value in _HOLDING_PER_DAY.items():
        seeds.append(CostSeed(CostKind.HOLDING_COST_PER_DAY, channel, value))
    for (channel, grade), value in _REPAIR.items():
        seeds.append(CostSeed(CostKind.REPAIR_COST, f"{channel}:{grade}", value))
    for (channel, grade), value in _DAYS_TO_SELL.items():
        seeds.append(CostSeed(CostKind.EXPECTED_DAYS_TO_SELL, f"{channel}:{grade}", value))

    return seeds


#: Materialised default rows, useful for seeding in one call.
DEFAULT_COSTS: tuple[CostSeed, ...] = tuple(default_cost_seeds())
