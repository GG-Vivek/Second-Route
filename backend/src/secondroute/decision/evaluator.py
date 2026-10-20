"""
Monte Carlo channel evaluator (Phase 2 - F2.5).

For every eligible channel the evaluator draws samples from the sale price,
fee, repair, logistics and holding distributions and computes the net value
distribution (p10 / p50 / p90), the expected value, the dispersion and the
probability that the channel is the best of the set.

The whole evaluation is seeded: the same seed and the same inputs always
produce exactly the same numbers. That is what makes a decision reproducible
from its stored snapshot (F2.9).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Final, Sequence
from uuid import UUID

import numpy as np
from numpy.typing import NDArray

from secondroute.condition.grades import GRADES, GradeDistribution, InspectionSignals
from secondroute.core.logging import get_logger
from secondroute.costs.models import CostKind
from secondroute.costs.service import CostBook
from secondroute.pricing.protocols import (
    PriceDistribution,
    PriceSource,
    PriceSourceNotFoundError,
)

logger = get_logger(__name__)

__all__ = [
    "DECISION_CHANNELS",
    "PHASE2_CHANNELS",
    "ChannelEvaluation",
    "CostBreakdown",
    "EvaluationInput",
    "EvaluationResult",
    "evaluate_channels",
]

#: Relative dispersion of each cost component (coefficient of variation).
COST_CV: Final[dict[str, float]] = {
    CostKind.FIXED_FEE: 0.12,
    CostKind.LOGISTICS_COST: 0.15,
    CostKind.HANDLING_COST: 0.18,
    CostKind.REPAIR_COST: 0.30,
    CostKind.EXPECTED_DAYS_TO_SELL: 0.25,
}

#: Cost components that are deterministic (no uncertainty modelled).
DETERMINISTIC_COSTS: Final[frozenset[str]] = frozenset(
    {CostKind.CHANNEL_FEE_PCT, CostKind.HOLDING_COST_PER_DAY}
)

#: The channels the Phase 2 decision engine evaluated.
PHASE2_CHANNELS: Final[tuple[str, ...]] = (
    "RESELL_OPEN_BOX",
    "RESELL_REFURB",
    "RECYCLE",
    "DONATE",
)

#: Every channel the engine can recommend.
#:
#: ``PARTS_HARVEST`` arrived in Phase 3 (F3.6). It is always eligible: there
#: is always something to harvest, and the parts valuation decides whether it
#: is worth doing.
DECISION_CHANNELS: Final[tuple[str, ...]] = (
    "RESELL_OPEN_BOX",
    "RESELL_REFURB",
    "PARTS_HARVEST",
    "RECYCLE",
    "DONATE",
)


@dataclass(frozen=True, slots=True)
class CostBreakdown:
    """Expected cost components for one channel.

    Attributes:
        sale_price: Expected sale price.
        fees: Platform and transaction fees.
        logistics: Outbound logistics.
        handling: Handling, photography, labelling.
        repair: Expected repair spend.
        holding: Cost of holding the unit until it sells.
        total_cost: Sum of every cost component.
        net: ``sale_price - total_cost``.
    """

    sale_price: float
    fees: float
    logistics: float
    handling: float
    repair: float
    holding: float

    @property
    def total_cost(self) -> float:
        """Total expected cost."""
        return self.fees + self.logistics + self.handling + self.repair + self.holding

    @property
    def net(self) -> float:
        """Expected net value."""
        return self.sale_price - self.total_cost

    def as_dict(self) -> dict[str, float]:
        """Return the breakdown as a plain dictionary."""
        return {
            "sale_price": round(self.sale_price, 2),
            "fees": round(self.fees, 2),
            "logistics": round(self.logistics, 2),
            "handling": round(self.handling, 2),
            "repair": round(self.repair, 2),
            "holding": round(self.holding, 2),
            "total_cost": round(self.total_cost, 2),
            "net": round(self.net, 2),
        }


@dataclass(frozen=True, slots=True)
class ChannelEvaluation:
    """The evaluation of one channel.

    Attributes:
        channel: Channel name.
        eligible: Whether the channel can be used for this unit.
        exclusion_reason: Why the channel was excluded, when it was.
        net_samples: The sampled net values.
        mean: Expected net.
        stddev: Standard deviation of the net.
        p10: 10th percentile of the net.
        p50: Median of the net.
        p90: 90th percentile of the net.
        breakdown: Expected cost components.
        grade_probabilities: Grade mix used for this channel.
        price_sources: Price source tag per grade.
        price_as_of: Price as-of timestamp per grade.
    """

    channel: str
    eligible: bool
    exclusion_reason: str | None
    net_samples: NDArray[np.float64]
    mean: float
    stddev: float
    p10: float
    p50: float
    p90: float
    breakdown: CostBreakdown
    grade_probabilities: dict[str, float]
    price_sources: dict[str, str] = field(default_factory=dict)
    price_as_of: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable view of the evaluation."""
        return {
            "channel": self.channel,
            "eligible": self.eligible,
            "exclusion_reason": self.exclusion_reason,
            "mean": round(self.mean, 2),
            "stddev": round(self.stddev, 2),
            "p10": round(self.p10, 2),
            "p50": round(self.p50, 2),
            "p90": round(self.p90, 2),
            "grade_probabilities": {
                grade: round(prob, 6) for grade, prob in self.grade_probabilities.items()
            },
            "price_sources": dict(self.price_sources),
            "price_as_of": dict(self.price_as_of),
            "breakdown": self.breakdown.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class EvaluationInput:
    """Everything the evaluator needs, in one immutable object.

    Flip-condition analysis (F2.8) perturbs this object rather than reaching
    into the evaluator, which keeps the sensitivity search honest.
    """

    sku_id: UUID
    signals: InspectionSignals
    cost_book: CostBook
    channels: tuple[str, ...] = PHASE2_CHANNELS
    as_of: datetime | None = None
    eligibility: dict[str, tuple[bool, str | None]] = field(default_factory=dict)

    def with_signals(self, **changes: object) -> EvaluationInput:
        """Return a copy with different inspection signals."""
        return replace(self, signals=replace(self.signals, **changes))  # type: ignore[arg-type]

    def with_cost_override(self, kind: str, key: str, value: float) -> EvaluationInput:
        """Return a copy with one cost value overridden.

        Used by the flip-condition sensitivity search.
        """
        return replace(self, cost_book=self.cost_book.with_override(kind, key, value))


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """The outcome of evaluating every channel.

    Attributes:
        channels: Per-channel evaluations, in the order evaluated.
        joint_draws: ``(n_eligible, n_samples)`` matrix of independent net draws.
        joint_index_by_channel: Maps a channel name to its row in
            ``joint_draws``. Ineligible channels are not present.
        probability_best: Probability each channel has the best net.
        samples: Number of Monte Carlo samples used.
        seed: Seed used.
    """

    channels: tuple[ChannelEvaluation, ...]
    joint_draws: NDArray[np.float64]
    joint_index_by_channel: dict[str, int]
    probability_best: dict[str, float]
    samples: int
    seed: int

    @property
    def eligible_channels(self) -> tuple[ChannelEvaluation, ...]:
        """Only the channels that passed eligibility."""
        return tuple(c for c in self.channels if c.eligible)

    def by_channel(self, channel: str) -> ChannelEvaluation | None:
        """Return the evaluation for one channel."""
        for candidate in self.channels:
            if candidate.channel == channel:
                return candidate
        return None

    def channel_names(self) -> tuple[str, ...]:
        """Return the evaluated channel names."""
        return tuple(c.channel for c in self.channels)

    def joint_index(self, channel: str) -> int:
        """Return the row index of a channel inside ``joint_draws``.

        Args:
            channel: The channel name.

        Returns:
            The row index.

        Raises:
            KeyError: If the channel is not eligible.
        """
        return self.joint_index_by_channel[channel]


def derive_seed(seed: int, *parts: object) -> int:
    """Derive a deterministic sub-seed from a master seed and label parts."""
    payload = ":".join([str(seed), *(str(p) for p in parts)]).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _lognormal_factor(rng: np.random.Generator, size: int, cv: float) -> NDArray[np.float64]:
    """Return multiplicative noise with the given coefficient of variation."""
    if cv <= 0:
        return np.ones(size, dtype=np.float64)
    sigma = float(np.sqrt(np.log1p(cv**2)))
    mu = float(-0.5 * np.log1p(cv**2))
    return np.exp(rng.normal(mu, sigma, size=size))


def _quantile(samples: NDArray[np.float64], q: float) -> float:
    """Return the ``q`` quantile of a sample array."""
    return float(np.quantile(samples, q))


async def evaluate_channels(
    evaluation_input: EvaluationInput,
    price_source: PriceSource,
    *,
    samples: int = 10_000,
    seed: int = 42,
    as_of: datetime | None = None,
) -> EvaluationResult:
    """Evaluate every channel with a Monte Carlo simulation.

    Args:
        evaluation_input: The unit, its inspection signals and the cost book.
        price_source: Where sale prices come from.
        samples: Number of Monte Carlo samples (default 10,000).
        seed: Master seed. The same seed and inputs always give the same result.
        as_of: Timestamp used to look up prices.

    Returns:
        The evaluation result, including the joint draws used for
        probability-best and confidence.
    """
    if samples <= 0:
        raise ValueError("samples must be positive")

    as_of = as_of or evaluation_input.as_of or datetime.utcnow()
    grade_probs = _grade_probabilities(evaluation_input)

    evaluations: list[ChannelEvaluation] = []
    net_samples_by_channel: list[NDArray[np.float64]] = []

    for channel in evaluation_input.channels:
        eligible, reason = evaluation_input.eligibility.get(channel, (True, None))
        if not eligible:
            evaluations.append(
                _ineligible_evaluation(channel, reason or "Channel not eligible for this unit.")
            )
            net_samples_by_channel.append(np.zeros(0, dtype=np.float64))
            continue

        try:
            per_grade, components, price_sources, price_as_of = await _grade_net_samples(
                evaluation_input,
                price_source,
                channel,
                grade_probs,
                samples=samples,
                seed=seed,
                as_of=as_of,
            )
        except PriceSourceNotFoundError as exc:
            # The source has no data for this channel. The channel is skipped
            # rather than the whole decision failing: a missing price source
            # is a reason not to recommend that channel, not a reason to
            # recommend nothing.
            logger.info("channel_skipped_no_price_data", channel=channel, reason=str(exc))
            evaluations.append(_ineligible_evaluation(channel, f"No price data available: {exc}"))
            net_samples_by_channel.append(np.zeros(0, dtype=np.float64))
            continue

        mixed = _mix_grades(per_grade, grade_probs, samples=samples, seed=seed, channel=channel)
        breakdown = _expected_breakdown(components, grade_probs)

        evaluations.append(
            ChannelEvaluation(
                channel=channel,
                eligible=True,
                exclusion_reason=None,
                net_samples=mixed,
                mean=float(mixed.mean()),
                stddev=float(mixed.std(ddof=0)),
                p10=_quantile(mixed, 0.10),
                p50=_quantile(mixed, 0.50),
                p90=_quantile(mixed, 0.90),
                breakdown=breakdown,
                grade_probabilities=dict(grade_probs),
                price_sources=price_sources,
                price_as_of=price_as_of,
            )
        )
        net_samples_by_channel.append(mixed)

    joint, probability_best, joint_index_by_channel = _joint_draws(
        net_samples_by_channel, [c.channel for c in evaluations], samples=samples, seed=seed
    )

    return EvaluationResult(
        channels=tuple(evaluations),
        joint_draws=joint,
        joint_index_by_channel=joint_index_by_channel,
        probability_best=probability_best,
        samples=samples,
        seed=seed,
    )


def _grade_probabilities(evaluation_input: EvaluationInput) -> dict[str, float]:
    """Return the grade mix, normalised over the grades that carry mass."""
    from secondroute.condition.grades import grade_distribution

    distribution: GradeDistribution = grade_distribution(evaluation_input.signals)
    raw = {grade: max(distribution.probabilities[grade], 0.0) for grade in GRADES}
    total = sum(raw.values())
    if total <= 0:
        return dict.fromkeys(GRADES, 0.25)
    return {grade: value / total for grade, value in raw.items()}


async def _grade_net_samples(
    evaluation_input: EvaluationInput,
    price_source: PriceSource,
    channel: str,
    grade_probs: dict[str, float],
    *,
    samples: int,
    seed: int,
    as_of: datetime,
) -> tuple[
    dict[str, NDArray[np.float64]],
    dict[str, dict[str, NDArray[np.float64]]],
    dict[str, str],
    dict[str, str],
]:
    """Return the net samples and cost components for each grade of one channel."""
    book = evaluation_input.cost_book
    fee_pct = book.get(CostKind.CHANNEL_FEE_PCT, channel)
    fixed_fee = book.get(CostKind.FIXED_FEE, channel)
    logistics_base = book.get(CostKind.LOGISTICS_COST, channel)
    handling_base = book.get(CostKind.HANDLING_COST, channel)
    holding_rate = book.get(CostKind.HOLDING_COST_PER_DAY, channel)

    per_grade: dict[str, NDArray[np.float64]] = {}
    components: dict[str, dict[str, NDArray[np.float64]]] = {}
    price_sources: dict[str, str] = {}
    price_as_of: dict[str, str] = {}

    for grade in GRADES:
        if grade_probs.get(grade, 0.0) <= 0:
            continue

        distribution: PriceDistribution = await price_source.get_distribution(
            evaluation_input.sku_id, grade, channel, as_of
        )
        rng = np.random.default_rng(derive_seed(seed, channel, grade))
        price = distribution.sample(rng, samples)

        fixed_fee_draws = fixed_fee * _lognormal_factor(rng, samples, COST_CV[CostKind.FIXED_FEE])
        logistics = logistics_base * _lognormal_factor(
            rng, samples, COST_CV[CostKind.LOGISTICS_COST]
        )
        handling = handling_base * _lognormal_factor(rng, samples, COST_CV[CostKind.HANDLING_COST])

        repair_base = book.get(CostKind.REPAIR_COST, f"{channel}:{grade}")
        repair = repair_base * _lognormal_factor(rng, samples, COST_CV[CostKind.REPAIR_COST])

        days_base = book.get(CostKind.EXPECTED_DAYS_TO_SELL, f"{channel}:{grade}")
        days = days_base * _lognormal_factor(rng, samples, COST_CV[CostKind.EXPECTED_DAYS_TO_SELL])
        holding = holding_rate * days

        fees = price * fee_pct + fixed_fee_draws
        per_grade[grade] = price - fees - logistics - handling - repair - holding
        components[grade] = {
            "sale_price": price,
            "fees": fees,
            "logistics": logistics,
            "handling": handling,
            "repair": repair,
            "holding": holding,
        }

        price_sources[grade] = distribution.source
        price_as_of[grade] = distribution.as_of.isoformat()

    return per_grade, components, price_sources, price_as_of


def _mix_grades(
    per_grade: dict[str, NDArray[np.float64]],
    grade_probs: dict[str, float],
    *,
    samples: int,
    seed: int,
    channel: str,
) -> NDArray[np.float64]:
    """Mix the per-grade net samples according to the grade probabilities."""
    if not per_grade:
        return np.zeros(samples, dtype=np.float64)

    grades = sorted(per_grade)
    probabilities = np.array([max(grade_probs.get(g, 0.0), 0.0) for g in grades], dtype=np.float64)
    if probabilities.sum() <= 0:
        probabilities = np.full(len(grades), 1.0 / len(grades))
    probabilities = probabilities / probabilities.sum()

    rng = np.random.default_rng(derive_seed(seed, channel, "grade-mix"))
    indices = rng.choice(len(grades), size=samples, p=probabilities)
    return np.array([per_grade[grades[i]][j] for j, i in enumerate(indices)], dtype=np.float64)


def _expected_breakdown(
    components: dict[str, dict[str, NDArray[np.float64]]],
    grade_probs: dict[str, float],
) -> CostBreakdown:
    """Return the expected cost breakdown, weighted by the grade mix."""
    if not components:
        return CostBreakdown(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    total_weight = sum(grade_probs.get(grade, 0.0) for grade in components) or 1.0

    def weighted(name: str) -> float:
        return (
            sum(
                float(components[grade][name].mean()) * grade_probs.get(grade, 0.0)
                for grade in components
            )
            / total_weight
        )

    sale_price = weighted("sale_price")
    fees = weighted("fees")
    logistics = weighted("logistics")
    handling = weighted("handling")
    repair = weighted("repair")
    holding = weighted("holding")

    return CostBreakdown(
        sale_price=sale_price,
        fees=fees,
        logistics=logistics,
        handling=handling,
        repair=repair,
        holding=holding,
    )


def _ineligible_evaluation(channel: str, reason: str) -> ChannelEvaluation:
    """Return the evaluation record for a channel that was blocked."""
    empty = np.zeros(0, dtype=np.float64)
    return ChannelEvaluation(
        channel=channel,
        eligible=False,
        exclusion_reason=reason,
        net_samples=empty,
        mean=0.0,
        stddev=0.0,
        p10=0.0,
        p50=0.0,
        p90=0.0,
        breakdown=CostBreakdown(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        grade_probabilities={},
    )


def _joint_draws(
    net_samples_by_channel: Sequence[NDArray[np.float64]],
    channel_names: Sequence[str],
    *,
    samples: int,
    seed: int,
) -> tuple[NDArray[np.float64], dict[str, float], dict[str, int]]:
    """Build independent joint draws and the probability each channel is best.

    Returns:
        A ``(joint_draws, probability_best, joint_index_by_channel)`` tuple.
        The joint matrix only contains eligible channels, so the index map is
        needed to translate a channel name into a row.
    """
    eligible_indices = [i for i, arr in enumerate(net_samples_by_channel) if arr.size == samples]
    if not eligible_indices:
        return (
            np.zeros((0, samples), dtype=np.float64),
            {},
            {},
        )

    rng = np.random.default_rng(derive_seed(seed, "joint"))
    indices = rng.integers(0, samples, size=(samples, len(eligible_indices)))

    joint = np.empty((len(eligible_indices), samples), dtype=np.float64)
    for position, channel_index in enumerate(eligible_indices):
        source = net_samples_by_channel[channel_index]
        joint[position] = source[indices[:, position]]

    best = joint.max(axis=0)
    tolerance = np.maximum(np.abs(best) * 1e-9, 1e-9)
    is_best = joint >= best - tolerance
    tie_counts = is_best.sum(axis=0)

    probability_best: dict[str, float] = {}
    joint_index_by_channel: dict[str, int] = {}
    for position, channel_index in enumerate(eligible_indices):
        name = channel_names[channel_index]
        joint_index_by_channel[name] = position
        wins = float(is_best[position].sum())
        total = float(tie_counts.sum())
        probability_best[name] = wins / total if total > 0 else 0.0

    return joint, probability_best, joint_index_by_channel
