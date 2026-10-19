"""
Synthetic returns generator (Phase 2 - F2.1).

Generates realistic returned-unit records so the decision engine can be
developed, tested and demoed before any real market data exists.

Every generated record carries ``is_synthetic = True`` so it can never be
silently mixed with real observations in reports (PLAN.md principle 4).

The generator is fully seeded: the same seed always produces byte-identical
output. See ``ml/synthetic/README.md`` for the documented distributions.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Final, Literal, Sequence, cast

import numpy as np
from numpy.typing import NDArray

__all__ = [
    "AccessorySet",
    "FunctionalTests",
    "SyntheticPriceObservation",
    "SyntheticReturn",
    "SyntheticReturnGenerator",
]

Grade = Literal["A", "B", "C", "D"]

#: Canonical grade order used everywhere (best to worst).
GRADES: Final[tuple[Grade, ...]] = ("A", "B", "C", "D")

#: Return reason mix observed in consumer-electronics returns.
RETURN_REASON_WEIGHTS: Final[dict[str, float]] = {
    "BUYER_REMORSE": 0.34,
    "DEFECTIVE": 0.22,
    "NOT_AS_DESCRIBED": 0.16,
    "NOLONGER_NEEDED": 0.12,
    "DAMAGED_IN_TRANSIT": 0.09,
    "IDENTIFICATION_ERROR": 0.04,
    "OTHER": 0.03,
}

#: Channel the unit was originally sold through.
ORDER_CHANNEL_WEIGHTS: Final[dict[str, float]] = {
    "ONLINE": 0.55,
    "RETAIL": 0.31,
    "MARKETPLACE": 0.14,
}

#: Cosmetic grade mix, before any battery-health adjustment.
COSMETIC_GRADE_WEIGHTS: Final[dict[str, float]] = {
    "A": 0.18,
    "B": 0.37,
    "C": 0.31,
    "D": 0.14,
}

#: Probability that a given accessory is present, by order channel.
ACCESSORY_PRESENT_PROBABILITY: Final[dict[str, float]] = {
    "charger": 0.94,
    "box": 0.78,
    "cable": 0.81,
    "adapter": 0.72,
    "documentation": 0.63,
}

#: Functional test names exercised on every unit.
FUNCTIONAL_TESTS: Final[tuple[str, ...]] = ("display", "keyboard", "ports", "audio", "camera")

#: Probability a functional test fails, by return reason.
FUNCTIONAL_FAILURE_PROBABILITY: Final[dict[str, float]] = {
    "BUYER_REMORSE": 0.02,
    "DEFECTIVE": 0.34,
    "NOT_AS_DESCRIBED": 0.17,
    "NOLONGER_NEEDED": 0.03,
    "DAMAGED_IN_TRANSIT": 0.27,
    "IDENTIFICATION_ERROR": 0.09,
    "OTHER": 0.08,
}

#: Baseline resale value per grade, before family multipliers.
GRADE_BASE_VALUE_USD: Final[dict[str, float]] = {
    "A": 1450.0,
    "B": 1150.0,
    "C": 780.0,
    "D": 420.0,
}

#: Channel-level share of the grade base value a buyer actually pays.
CHANNEL_VALUE_SHARE: Final[dict[str, float]] = {
    "RESELL_OPEN_BOX": 0.92,
    "RESELL_REFURB": 0.78,
    "RECYCLE": 0.06,
    "DONATE": 0.0,
}

#: Relative transaction price dispersion per channel (coefficient of variation).
CHANNEL_PRICE_CV: Final[dict[str, float]] = {
    "RESELL_OPEN_BOX": 0.12,
    "RESELL_REFURB": 0.18,
    "RECYCLE": 0.22,
    "DONATE": 0.0,
}

#: Channels the Phase 2 decision engine can recommend.
SYNTHETIC_CHANNELS: Final[tuple[str, ...]] = (
    "RESELL_OPEN_BOX",
    "RESELL_REFURB",
    "RECYCLE",
    "DONATE",
)


@dataclass(frozen=True, slots=True)
class SyntheticReturn:
    """One synthetic returned unit.

    Mirrors the fields the Phase 1 inspection record captures so synthetic
    rows can drive the decision engine end to end.
    """

    index: int
    family: str
    model_name: str
    year: int
    storage_gb: int
    ram_gb: int
    color: str
    region: str
    serial: str
    return_reason: str
    order_channel: str
    battery_health_pct: float
    battery_cycles: int
    cosmetic_grade: Grade
    functional_tests: dict[str, bool]
    accessories: dict[str, bool]
    activation_lock: str
    received_at: datetime
    is_synthetic: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        data = asdict(self)
        data["received_at"] = self.received_at.isoformat()
        return data

    def to_json(self) -> str:
        """Return a canonical JSON representation (stable key ordering)."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class SyntheticPriceObservation:
    """One synthetic price observation for a (family, grade, channel) cell."""

    family: str
    grade: Grade
    channel: str
    price: float
    currency: str
    observed_at: datetime
    weight: float
    is_synthetic: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        data = asdict(self)
        data["observed_at"] = self.observed_at.isoformat()
        return data


@dataclass(frozen=True, slots=True)
class _SkuProfile:
    """Static description of a synthetic SKU family."""

    family: str
    model_name: str
    year: int
    storage_gb: int
    ram_gb: int
    color: str
    region: str
    value_multiplier: float


@dataclass(frozen=True, slots=True)
class _ReturnPlan:
    """Per-unit plan shared by the inspection fields."""

    sku: _SkuProfile
    return_reason: str
    order_channel: str
    battery_health_pct: float
    battery_cycles: int
    cosmetic_grade: Grade
    functional_tests: dict[str, bool]
    accessories: dict[str, bool]
    activation_lock: str
    received_at: datetime
    serial: str = field(default="", compare=False)


class SyntheticReturnGenerator:
    """Seeded generator for synthetic returned units and price observations.

    Args:
        seed: Master seed. The same seed always yields identical output.
        start_date: First ``received_at`` date in the generated window.
        horizon_days: Number of days the generated window spans.

    Example:
        >>> gen = SyntheticReturnGenerator(seed=42)
        >>> rows = gen.generate(100)
        >>> hash_a = gen.dataset_hash(rows)
        >>> rows2 = SyntheticReturnGenerator(seed=42).generate(100)
        >>> gen.dataset_hash(rows2) == hash_a
        True
    """

    def __init__(
        self,
        seed: int = 42,
        start_date: date = date(2025, 1, 1),
        horizon_days: int = 365,
    ) -> None:
        self.seed = seed
        self.start_date = start_date
        self.horizon_days = horizon_days
        self._rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, count: int) -> list[SyntheticReturn]:
        """Generate ``count`` synthetic returns.

        Args:
            count: Number of rows to generate.

        Returns:
            A list of :class:`SyntheticReturn` records.

        Raises:
            ValueError: If ``count`` is negative.
        """
        if count < 0:
            raise ValueError("count must be non-negative")

        plans = self._plan(count)
        rows: list[SyntheticReturn] = []
        for index, plan in enumerate(plans):
            rows.append(
                SyntheticReturn(
                    index=index,
                    family=plan.sku.family,
                    model_name=plan.sku.model_name,
                    year=plan.sku.year,
                    storage_gb=plan.sku.storage_gb,
                    ram_gb=plan.sku.ram_gb,
                    color=plan.sku.color,
                    region=plan.sku.region,
                    serial=plan.serial,
                    return_reason=plan.return_reason,
                    order_channel=plan.order_channel,
                    battery_health_pct=round(plan.battery_health_pct, 1),
                    battery_cycles=plan.battery_cycles,
                    cosmetic_grade=plan.cosmetic_grade,
                    functional_tests=dict(plan.functional_tests),
                    accessories=dict(plan.accessories),
                    activation_lock=plan.activation_lock,
                    received_at=plan.received_at,
                )
            )
        return rows

    def generate_price_observations(
        self,
        observations_per_cell: int = 40,
        as_of: datetime | None = None,
    ) -> list[SyntheticPriceObservation]:
        """Generate synthetic price observations for every (family, grade, channel).

        Args:
            observations_per_cell: How many observations to draw per cell.
            as_of: Timestamp applied to every observation. Defaults to the
                end of the generated window.

        Returns:
            A list of :class:`SyntheticPriceObservation` records.
        """
        if observations_per_cell <= 0:
            raise ValueError("observations_per_cell must be positive")

        as_of = as_of or self._window_end()
        rng = np.random.default_rng(self._derive_seed("prices"))
        rows: list[SyntheticPriceObservation] = []

        for sku in self._sku_profiles():
            for grade in GRADES:
                base = GRADE_BASE_VALUE_USD[grade] * sku.value_multiplier
                for channel in SYNTHETIC_CHANNELS:
                    mean = base * CHANNEL_VALUE_SHARE[channel]
                    cv = CHANNEL_PRICE_CV[channel]
                    if mean <= 0 or cv <= 0:
                        prices = np.full(observations_per_cell, mean)
                    else:
                        prices = rng.lognormal(
                            mean=np.log(mean) - (cv**2) / 2,
                            sigma=cv,
                            size=observations_per_cell,
                        )
                    weights = rng.uniform(0.5, 1.0, size=observations_per_cell)
                    for price, weight in zip(prices, weights, strict=True):
                        rows.append(
                            SyntheticPriceObservation(
                                family=sku.family,
                                grade=grade,
                                channel=channel,
                                price=round(float(price), 2),
                                currency="USD",
                                observed_at=as_of,
                                weight=round(float(weight), 4),
                            )
                        )
        return rows

    @staticmethod
    def dataset_hash(rows: Sequence[SyntheticReturn]) -> str:
        """Return a stable SHA-256 hash for a generated dataset.

        The hash is computed over the canonical JSON of every row, so it is
        independent of dict ordering and reproducible across runs and
        platforms.
        """
        hasher = hashlib.sha256()
        for row in rows:
            hasher.update(row.to_json().encode("utf-8"))
            hasher.update(b"\n")
        return hasher.hexdigest()

    @staticmethod
    def price_dataset_hash(rows: Sequence[SyntheticPriceObservation]) -> str:
        """Return a stable SHA-256 hash for a generated price dataset."""
        hasher = hashlib.sha256()
        for row in rows:
            hasher.update(
                json.dumps(row.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
            )
            hasher.update(b"\n")
        return hasher.hexdigest()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _derive_seed(self, label: str) -> int:
        """Derive a stable sub-seed from the master seed and a label."""
        digest = hashlib.sha256(f"{self.seed}:{label}".encode()).digest()
        return int.from_bytes(digest[:8], "big")

    def _window_end(self) -> datetime:
        """Return the end of the generated window as an aware datetime."""
        end = self.start_date + timedelta(days=self.horizon_days)
        return datetime(end.year, end.month, end.day, tzinfo=timezone.utc)

    def _sku_profiles(self) -> list[_SkuProfile]:
        """Return the static SKU catalogue used by the generator."""
        return [
            _SkuProfile(
                family="MacBook Pro",
                model_name="M3 Pro",
                year=2023,
                storage_gb=512,
                ram_gb=18,
                color="Space Gray",
                region="US",
                value_multiplier=1.00,
            ),
            _SkuProfile(
                family="MacBook Pro",
                model_name="M3 Pro",
                year=2023,
                storage_gb=1024,
                ram_gb=18,
                color="Space Gray",
                region="US",
                value_multiplier=1.18,
            ),
            _SkuProfile(
                family="MacBook Pro",
                model_name="M3 Max",
                year=2023,
                storage_gb=1024,
                ram_gb=36,
                color="Space Gray",
                region="US",
                value_multiplier=1.62,
            ),
            _SkuProfile(
                family="MacBook Air",
                model_name="M2",
                year=2022,
                storage_gb=256,
                ram_gb=8,
                color="Midnight",
                region="US",
                value_multiplier=0.58,
            ),
            _SkuProfile(
                family="MacBook Air",
                model_name="M2",
                year=2022,
                storage_gb=512,
                ram_gb=8,
                color="Midnight",
                region="US",
                value_multiplier=0.66,
            ),
            _SkuProfile(
                family="ThinkPad X1 Carbon",
                model_name="Gen 11",
                year=2023,
                storage_gb=512,
                ram_gb=16,
                color="Black",
                region="US",
                value_multiplier=0.72,
            ),
            _SkuProfile(
                family="Dell XPS 13",
                model_name="Plus 9310",
                year=2022,
                storage_gb=512,
                ram_gb=16,
                color="Platinum",
                region="US",
                value_multiplier=0.61,
            ),
        ]

    def _plan(self, count: int) -> list[_ReturnPlan]:
        """Build the per-unit plan used to materialise the rows."""
        skus = self._sku_profiles()
        rng = np.random.default_rng(self._derive_seed("units"))

        reasons = list(RETURN_REASON_WEIGHTS)
        reason_probs = np.array([RETURN_REASON_WEIGHTS[r] for r in reasons])
        reason_probs = reason_probs / reason_probs.sum()

        channels = list(ORDER_CHANNEL_WEIGHTS)
        channel_probs = np.array([ORDER_CHANNEL_WEIGHTS[c] for c in channels])
        channel_probs = channel_probs / channel_probs.sum()

        grades = list(COSMETIC_GRADE_WEIGHTS)
        grade_probs = np.array([COSMETIC_GRADE_WEIGHTS[g] for g in grades])
        grade_probs = grade_probs / grade_probs.sum()

        sku_idx = rng.integers(0, len(skus), size=count)
        reason_idx = rng.choice(len(reasons), size=count, p=reason_probs)
        channel_idx = rng.choice(len(channels), size=count, p=channel_probs)
        grade_idx = rng.choice(len(grades), size=count, p=grade_probs)

        # Battery health: base level shifted down by defect/damage reasons.
        battery_base = rng.normal(94.0, 4.5, size=count)
        reason_penalty = np.array(
            [
                {"DEFECTIVE": 6.0, "DAMAGED_IN_TRANSIT": 3.5}.get(reasons[i], 0.0)
                for i in reason_idx
            ]
        )
        battery = np.clip(battery_base - reason_penalty, 55.0, 100.0)

        # Cycle count correlates negatively with battery health.
        cycles = np.clip(
            rng.gamma(shape=4.0, scale=45.0, size=count) + (100.0 - battery) * 2.4,
            5,
            1200,
        ).astype(int)

        # Failure probability rises as battery health drops.
        base_fail = np.array([FUNCTIONAL_FAILURE_PROBABILITY[reasons[i]] for i in reason_idx])
        fail_p = np.clip(base_fail + (95.0 - battery) * 0.006, 0.0, 0.85)

        accessory_names = list(ACCESSORY_PRESENT_PROBABILITY)
        accessory_p = np.array([ACCESSORY_PRESENT_PROBABILITY[a] for a in accessory_names])

        day_offsets = rng.integers(0, self.horizon_days, size=count)

        plans: list[_ReturnPlan] = []
        for i in range(count):
            sku = skus[int(sku_idx[i])]
            reason = reasons[int(reason_idx[i])]
            order_channel = channels[int(channel_idx[i])]

            functional_tests = {
                name: bool(rng.random() >= fail_p[i]) for name in FUNCTIONAL_TESTS
            }
            accessories = {
                name: bool(rng.random() < accessory_p[j])
                for j, name in enumerate(accessory_names)
            }

            activation_lock = "none"
            if reason == "IDENTIFICATION_ERROR" and rng.random() < 0.45:
                activation_lock = "present"

            received = datetime(
                self.start_date.year,
                self.start_date.month,
                self.start_date.day,
                tzinfo=timezone.utc,
            ) + timedelta(days=int(day_offsets[i]))

            serial = f"SYN{int(sku_idx[i]):02d}{i:06d}{int(rng.integers(0, 999999)):06d}"

            plans.append(
                _ReturnPlan(
                    sku=sku,
                    return_reason=reason,
                    order_channel=order_channel,
                    battery_health_pct=float(battery[i]),
                    battery_cycles=int(cycles[i]),
                    cosmetic_grade=cast(Grade, grades[int(grade_idx[i])]),
                    functional_tests=functional_tests,
                    accessories=accessories,
                    activation_lock=activation_lock,
                    received_at=received,
                    serial=serial,
                )
            )
        return plans

    def battery_health_array(self, rows: Sequence[SyntheticReturn]) -> NDArray[np.float64]:
        """Return the battery-health values of ``rows`` as a float array."""
        return np.array([row.battery_health_pct for row in rows], dtype=np.float64)
