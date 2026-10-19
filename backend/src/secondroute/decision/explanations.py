"""
Reasons and flip conditions (Phase 2 - F2.8).

Two kinds of explanation come out of the engine:

**Reasons** answer "why this channel?". They are the largest contributors to
the net-value difference between the recommended channel and the runner-up,
computed straight from the cost breakdown so they can never contradict the
numbers on the card.

**Flip conditions** answer "what would change this?". Each one names a single
input and the threshold at which the recommendation changes, found by a
one-at-a-time sensitivity search.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Final

from secondroute.decision.evaluator import ChannelEvaluation, EvaluationInput
from secondroute.decision.evaluator import PHASE2_CHANNELS

__all__ = [
    "FlipCondition",
    "Reason",
    "apply_flip_condition",
    "build_flip_conditions",
    "build_reasons",
]

#: Labels for the cost components that can explain a decision.
COMPONENT_LABELS: Final[dict[str, str]] = {
    "sale_price": "Expected sale price",
    "fees": "Platform and transaction fees",
    "logistics": "Outbound logistics",
    "handling": "Handling and repacking",
    "repair": "Expected repair spend",
    "holding": "Cost of holding the unit",
}

#: How many reasons the card shows by default.
MAX_REASONS: Final[int] = 4

#: How many flip conditions the card shows by default.
MAX_FLIP_CONDITIONS: Final[int] = 3


@dataclass(frozen=True, slots=True)
class Reason:
    """One reason why a channel was recommended.

    Attributes:
        code: Stable machine-readable code (e.g. ``higher_sale_price``).
        label: Human-readable component label.
        contribution: Signed contribution to the net difference, in USD.
        favours_recommended: True when the contribution favours the
            recommended channel.
        text: Plain-language sentence.
    """

    code: str
    label: str
    contribution: float
    favours_recommended: bool
    text: str

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable view of the reason."""
        return {
            "code": self.code,
            "label": self.label,
            "contribution": round(self.contribution, 2),
            "favours_recommended": self.favours_recommended,
            "text": self.text,
        }


@dataclass(frozen=True, slots=True)
class FlipCondition:
    """One input whose change would flip the recommendation.

    Attributes:
        input_name: Name of the input (e.g. ``battery_health_pct``).
        input_kind: ``numeric`` or ``categorical``.
        current_value: The value used for this decision.
        threshold_value: The value at which the recommendation changes.
        new_channel: The channel the decision flips to.
        direction: ``above`` or ``below`` - which side of the current value
            triggers the flip.
        description: Plain-language sentence.
        target_channel: The channel the input belongs to, for cost inputs.
        fallback_triggered: Whether the confidence gate also falls back at the
            threshold.
    """

    input_name: str
    input_kind: str
    current_value: float | str
    threshold_value: float | str
    new_channel: str
    direction: str
    description: str
    target_channel: str | None = None
    fallback_triggered: bool = False

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable view of the flip condition."""
        return {
            "input_name": self.input_name,
            "input_kind": self.input_kind,
            "current_value": _round(self.current_value),
            "threshold_value": _round(self.threshold_value),
            "new_channel": self.new_channel,
            "direction": self.direction,
            "description": self.description,
            "target_channel": self.target_channel,
            "fallback_triggered": self.fallback_triggered,
        }


def build_reasons(
    recommended: ChannelEvaluation,
    runner_up: ChannelEvaluation | None,
    *,
    max_reasons: int = MAX_REASONS,
) -> list[Reason]:
    """Build the reasons that explain a recommendation.

    Args:
        recommended: The recommended channel's evaluation.
        runner_up: The second-best eligible channel, when there is one.
        max_reasons: How many reasons to return.

    Returns:
        The reasons, largest contribution first.
    """
    if runner_up is None:
        return [
            Reason(
                code="only_eligible_channel",
                label="Only eligible channel",
                contribution=0.0,
                favours_recommended=True,
                text=(
                    f"{recommended.channel} is the only channel available for this unit, "
                    "so no alternative could be compared."
                ),
            )
        ]

    contributions: list[tuple[str, float]] = [
        (
            "sale_price",
            recommended.breakdown.sale_price - runner_up.breakdown.sale_price,
        ),
        ("fees", -(recommended.breakdown.fees - runner_up.breakdown.fees)),
        (
            "logistics",
            -(recommended.breakdown.logistics - runner_up.breakdown.logistics),
        ),
        (
            "handling",
            -(recommended.breakdown.handling - runner_up.breakdown.handling),
        ),
        ("repair", -(recommended.breakdown.repair - runner_up.breakdown.repair)),
        ("holding", -(recommended.breakdown.holding - runner_up.breakdown.holding)),
    ]

    ranked = sorted(contributions, key=lambda item: abs(item[1]), reverse=True)
    reasons: list[Reason] = []
    for component, contribution in ranked:
        if abs(contribution) < 0.01:
            continue
        favours = contribution > 0
        label = COMPONENT_LABELS[component]
        if favours:
            text = (
                f"{recommended.channel} wins on {label.lower()}: "
                f"{_money(abs(contribution))} better than {runner_up.channel}."
            )
        else:
            text = (
                f"{runner_up.channel} is {_money(abs(contribution))} better on "
                f"{label.lower()}, but {recommended.channel} wins overall."
            )
        reasons.append(
            Reason(
                code=f"{'favourable' if favours else 'unfavourable'}_{component}",
                label=label,
                contribution=contribution,
                favours_recommended=favours,
                text=text,
            )
        )
        if len(reasons) >= max_reasons:
            break

    if not reasons:
        reasons.append(
            Reason(
                code="narrow_margin",
                label="Narrow margin",
                contribution=0.0,
                favours_recommended=True,
                text=(
                    f"{recommended.channel} and {runner_up.channel} are within a dollar of "
                    "each other on every cost component."
                ),
            )
        )
    return reasons


@dataclass(frozen=True, slots=True)
class Recommendation:
    """The outcome of ranking a candidate input.

    Attributes:
        channel: The channel the ranking prefers, before the confidence gate.
        gated_channel: What the engine actually returns (the same channel, or
            ``SAFE_DEFAULT`` when the gate fails).
        fallback_used: Whether the confidence gate produced a fallback.
    """

    channel: str
    gated_channel: str
    fallback_used: bool


#: A callback that re-evaluates a perturbed input and returns its
#: recommendation.
Recommender = Callable[[EvaluationInput], Awaitable[Recommendation]]


@dataclass(frozen=True, slots=True)
class _NumericPerturbation:
    """A numeric input that can be perturbed."""

    name: str
    label: str
    current: float
    lower: float
    upper: float
    unit: str
    apply: Callable[[EvaluationInput, float], EvaluationInput]


@dataclass(frozen=True, slots=True)
class _CategoricalPerturbation:
    """A categorical input that can be perturbed."""

    name: str
    label: str
    current: str
    options: tuple[str, ...]
    apply: Callable[[EvaluationInput, str], EvaluationInput]


def _money(value: float) -> str:
    """Format a USD amount."""
    return f"${value:,.2f}"


def _round(value: float | str) -> float | str:
    """Round a numeric value for display, leaving strings untouched."""
    if isinstance(value, (int, float)):
        return round(float(value), 4)
    return value


def _numeric_perturbations(
    evaluation_input: EvaluationInput, recommended_channel: str
) -> list[_NumericPerturbation]:
    """Return the numeric inputs that can be perturbed."""
    signals = evaluation_input.signals
    book = evaluation_input.cost_book

    perturbations: list[_NumericPerturbation] = [
        _NumericPerturbation(
            name="battery_health_pct",
            label="Battery health",
            current=signals.battery_health_pct,
            lower=50.0,
            upper=100.0,
            unit="%",
            apply=lambda inp, value: inp.with_signals(battery_health_pct=value),
        ),
        _NumericPerturbation(
            name="channel_fee_pct",
            label="Platform fee",
            current=book.get("channel_fee_pct", recommended_channel),
            lower=0.0,
            upper=0.60,
            unit="%",
            apply=lambda inp, value: inp.with_cost_override(
                "channel_fee_pct", recommended_channel, value
            ),
        ),
        _NumericPerturbation(
            name="repair_cost",
            label="Expected repair cost",
            current=book.get("repair_cost", f"{recommended_channel}:A"),
            lower=0.0,
            upper=1500.0,
            unit="USD",
            apply=lambda inp, value: inp.with_cost_override(
                "repair_cost", f"{recommended_channel}:A", value
            ),
        ),
        _NumericPerturbation(
            name="logistics_cost",
            label="Outbound logistics",
            current=book.get("logistics_cost", recommended_channel),
            lower=0.0,
            upper=400.0,
            unit="USD",
            apply=lambda inp, value: inp.with_cost_override(
                "logistics_cost", recommended_channel, value
            ),
        ),
    ]
    return perturbations


def _categorical_perturbations(evaluation_input: EvaluationInput) -> list[_CategoricalPerturbation]:
    """Return the categorical inputs that can be perturbed."""
    return [
        _CategoricalPerturbation(
            name="cosmetic_grade",
            label="Cosmetic grade",
            current=evaluation_input.signals.cosmetic_grade,
            options=("A", "B", "C", "D"),
            apply=lambda inp, value: inp.with_signals(cosmetic_grade=value),
        )
    ]


async def build_flip_conditions(
    evaluation_input: EvaluationInput,
    recommender: Recommender,
    recommended_channel: str,
    *,
    max_conditions: int = MAX_FLIP_CONDITIONS,
    max_iterations: int = 24,
) -> list[FlipCondition]:
    """Find the inputs whose change would flip the recommendation.

    Each input is perturbed on its own. For numeric inputs a bisection search
    finds the nearest threshold at which the recommendation changes; for
    categorical inputs every alternative value is tried.

    The search targets the *ranked channel*, not the gated result. A change
    that merely trips the confidence gate is not the answer the operator is
    looking for - they want to know which channel takes over.

    Args:
        evaluation_input: The input the decision was made from.
        recommender: Callback that re-evaluates and returns the recommendation.
        recommended_channel: The channel currently recommended.
        max_conditions: How many flip conditions to return.
        max_iterations: Maximum bisection steps per numeric input.

    Returns:
        The flip conditions, closest threshold first.
    """
    baseline = await recommender(evaluation_input)

    conditions: list[FlipCondition] = []

    for categorical in _categorical_perturbations(evaluation_input):
        for option in categorical.options:
            if option == categorical.current:
                continue
            perturbed = categorical.apply(evaluation_input, option)
            result = await recommender(perturbed)
            if result.channel == baseline.channel:
                continue
            conditions.append(
                FlipCondition(
                    input_name=categorical.name,
                    input_kind="categorical",
                    current_value=categorical.current,
                    threshold_value=option,
                    new_channel=result.channel,
                    direction="at",
                    description=(
                        f"If {categorical.label.lower()} were {option} instead of "
                        f"{categorical.current}, the recommendation would become "
                        f"{_channel_phrase(result)}."
                    ),
                    target_channel=recommended_channel,
                    fallback_triggered=result.fallback_used,
                )
            )

    for numeric in _numeric_perturbations(evaluation_input, recommended_channel):
        threshold = await _bisect_threshold(
            evaluation_input,
            recommender,
            numeric,
            baseline,
            max_iterations=max_iterations,
        )
        if threshold is None:
            continue
        value, result = threshold
        direction = "below" if value < numeric.current else "above"
        conditions.append(
            FlipCondition(
                input_name=numeric.name,
                input_kind="numeric",
                current_value=numeric.current,
                threshold_value=value,
                new_channel=result.channel,
                direction=direction,
                description=(
                    f"If {numeric.label.lower()} were {direction} "
                    f"{_format_value(value, numeric.unit)} "
                    f"(currently {_format_value(numeric.current, numeric.unit)}), "
                    f"the recommendation would become {_channel_phrase(result)}."
                ),
                target_channel=recommended_channel,
                fallback_triggered=result.fallback_used,
            )
        )

    conditions.sort(
        key=lambda condition: _distance(condition.current_value, condition.threshold_value)
    )
    return conditions[:max_conditions]


def _channel_phrase(result: Recommendation) -> str:
    """Describe the channel a flip would land on."""
    if result.fallback_used:
        return f"a safe default (the conservative floor is {result.channel})"
    return result.channel


def _format_value(value: float, unit: str) -> str:
    """Format a perturbed value for display."""
    if unit == "USD":
        return _money(value)
    if unit == "%":
        return f"{value * 100:.1f}%"
    return f"{value:.1f}{unit}"


def _distance(current: float | str, threshold: float | str) -> float:
    """Return a sortable distance between the current and threshold values."""
    try:
        return abs(float(current) - float(threshold))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return float("inf")


async def _bisect_threshold(
    evaluation_input: EvaluationInput,
    recommender: Recommender,
    perturbation: _NumericPerturbation,
    baseline: Recommendation,
    *,
    max_iterations: int,
) -> tuple[float, Recommendation] | None:
    """Bisect for the nearest value that flips the recommendation.

    The search runs outwards from the current value in both directions and
    keeps the boundary closest to it: the largest flipping value when
    searching downwards, the smallest when searching upwards.
    """
    current = perturbation.current

    for _direction, bound in (("below", perturbation.lower), ("above", perturbation.upper)):
        perturbed = perturbation.apply(evaluation_input, bound)
        result = await recommender(perturbed)
        if result.channel == baseline.channel:
            continue

        # ``flipping`` always flips the recommendation, ``stable`` never does.
        # The current value is the stable end; the bound is the flipping end.
        flipping, stable = bound, current

        for _ in range(max_iterations):
            middle = (flipping + stable) / 2
            perturbed = perturbation.apply(evaluation_input, middle)
            middle_result = await recommender(perturbed)
            if middle_result.channel == baseline.channel:
                stable = middle
            else:
                flipping = middle
                result = middle_result
            if abs(flipping - stable) < 1e-4:
                break

        return flipping, result

    return None


def eligible_channels(channels: Sequence[ChannelEvaluation]) -> list[ChannelEvaluation]:
    """Return only the eligible channels from a list."""
    return [channel for channel in channels if channel.eligible]


def apply_flip_condition(
    evaluation_input: EvaluationInput, condition: FlipCondition
) -> EvaluationInput:
    """Apply a flip condition to an evaluation input.

    Applying the threshold value of a flip condition must change the
    recommendation. This helper makes that checkable by the test suite and
    usable by the UI ("show me what changes").

    Args:
        evaluation_input: The input the decision was made from.
        condition: The flip condition to apply.

    Returns:
        A perturbed evaluation input.

    Raises:
        ValueError: If the flip condition names an unknown input.
    """
    channel = condition.target_channel or "RESELL_OPEN_BOX"

    if condition.input_name == "battery_health_pct":
        return evaluation_input.with_signals(battery_health_pct=float(condition.threshold_value))
    if condition.input_name == "cosmetic_grade":
        return evaluation_input.with_signals(cosmetic_grade=str(condition.threshold_value))
    if condition.input_name == "channel_fee_pct":
        return evaluation_input.with_cost_override(
            "channel_fee_pct", channel, float(condition.threshold_value)
        )
    if condition.input_name == "repair_cost":
        return evaluation_input.with_cost_override(
            "repair_cost", f"{channel}:A", float(condition.threshold_value)
        )
    if condition.input_name == "logistics_cost":
        return evaluation_input.with_cost_override(
            "logistics_cost", channel, float(condition.threshold_value)
        )
    raise ValueError(f"Unknown flip condition input: {condition.input_name}")


def default_channels() -> tuple[str, ...]:
    """Return the channel names the Phase 2 engine evaluates."""
    return PHASE2_CHANNELS
