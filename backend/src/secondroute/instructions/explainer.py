"""
The explanation text (Phase 5 - F5.7).

The decision engine says *what* to do. This module says *why*, in words an
operator can read.

The rule is narrow on purpose: the model writes words and nothing else. It
is given the decision as structured JSON and it is asked for a short
paragraph. Every number it produces is then checked against the numbers
the decision actually contains, and output that mentions a number the
decision does not have is thrown away in favour of the Phase 2 template.

That is the whole safety property. A model that says "expect about $900"
when the decision says $900 is fine. A model that says "expect about
$1200" is not, because nobody knows where the $1200 came from - and a
number on a decision card that no computation produced is worse than no
number at all.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, Sequence

import structlog

from secondroute.core.config import settings
from secondroute.instructions.templates import action_steps_for

logger = structlog.get_logger(__name__)

#: Where an explanation came from.
SOURCE_MODEL = "model"
SOURCE_TEMPLATE = "template"

#: The numbers a model produced that are not in the decision.
#: The names of the reasons an explanation was refused.
REASON_VALIDATED = "validated"
REASON_UNSEEN_NUMBER = "unseen-number"
REASON_NO_MODEL = "no-model"
REASON_MODEL_ERROR = "model-error"
REASON_MODEL_TIMEOUT = "model-timeout"
REASON_EMPTY = "empty-output"
REASON_DISABLED = "disabled"

#: A number in running text.
#
# It has to catch the forms a model actually writes: 900, 900.00, 1,200,
# $1,200.00, 85%, 12.5, and the years and model versions that appear in
# identifiers. A number followed by a letter is part of an identifier
# rather than a quantity, so it is left alone.
NUMBER_RE = re.compile(
    r"(?<![\w.])"
    r"(?P<number>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"(?![\w])"
)

#: The system prompt. It says what the model is allowed to do, and the
#: output is checked afterwards, so this is a request rather than a guard.
SYSTEM_PROMPT = """\
You explain a returns-disposition decision to the warehouse operator.

Rules:
- Use only the numbers in the decision JSON you are given. If a number is
  not in that JSON, do not write it.
- Do not recommend a different channel. The decision has already been
  made; you are only explaining it.
- Do not invent dates, quantities, prices or percentages.
- Write two or three plain sentences. No bullet points, no headings, no
  preamble.
- Say which channel was chosen, what the confidence means, and what the
  operator should watch out for.
"""


def normalise_number(raw: str) -> str:
    """Return a number in a form that can be compared.

    Thousands separators are removed, a trailing ``.0`` is dropped, and a
    leading ``+`` is removed, so that ``900``, ``900.00`` and ``$900`` are
    the same number.

    Args:
        raw: The number as it was written.

    Returns:
        The normalised number.
    """
    cleaned = raw.replace(",", "").lstrip("+")
    if "." in cleaned:
        cleaned = cleaned.rstrip("0").rstrip(".")
    if cleaned in ("", "-"):
        return cleaned
    try:
        value = float(cleaned)
    except ValueError:
        return cleaned
    if value == int(value):
        return str(int(value))
    return repr(value)


def extract_numbers(text: str) -> list[str]:
    """Return every number that appears in a piece of text.

    Args:
        text: The text.

    Returns:
        The numbers, normalised, in the order they appeared and with the
        repeats removed.
    """
    found: list[str] = []
    for match in NUMBER_RE.finditer(text):
        number = normalise_number(match.group("number"))
        if number and number not in found:
            found.append(number)
    return found


def numbers_in(payload: Any) -> set[str]:
    """Return every number that appears anywhere in a JSON payload.

    The keys are included, so a value the model reads out of a key - a
    year in a model version, a count in a grade - is a number the model is
    allowed to repeat.

    A probability is also allowed in its percentage form. The decision
    holds ``0.85`` and a model writes "85% confident"; that is the same
    number written the way a person writes it, not a number nobody
    produced. Without this the validator would refuse almost every
    sentence, because a model reaches for a percentage long before it
    reaches for a decimal.

    Args:
        payload: The payload, as JSON-serialisable data.

    Returns:
        The normalised numbers.
    """
    found: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            found.update(extract_numbers(str(key)))
            found.update(numbers_in(value))
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            found.update(numbers_in(item))
    elif isinstance(payload, bool):
        # A boolean is not a number, even though Python says it is one.
        return found
    elif isinstance(payload, (int, float)):
        found.add(normalise_number(str(payload)))
        found.update(_percentage_forms(payload))
    elif isinstance(payload, str):
        found.update(extract_numbers(payload))
    return found


def _percentage_forms(value: float) -> set[str]:
    """Return the percentage form of a probability.

    The multiplication is rounded, because 0.55 times 100 is
    55.00000000000001 in floating point and the model is going to write
    "55%".

    Args:
        value: The number.

    Returns:
        The percentage form, when the number is a probability. An empty
        set otherwise.
    """
    if not 0.0 <= float(value) <= 1.0:
        return set()
    return {normalise_number(str(round(float(value) * 100, 6)))}


@dataclass(frozen=True)
class ValidationResult:
    """The verdict on a piece of generated text.

    Attributes:
        accepted: Whether the text may be shown.
        unseen_numbers: The numbers in the text that the decision does not
            contain.
    """

    accepted: bool
    unseen_numbers: tuple[str, ...] = ()

    @property
    def reason(self) -> str:
        """Why the text was accepted or refused."""
        return REASON_VALIDATED if self.accepted else REASON_UNSEEN_NUMBER


def validate_explanation(text: str, decision: dict[str, Any]) -> ValidationResult:
    """Check that a piece of text mentions no number the decision lacks.

    Args:
        text: The generated text.
        decision: The decision the text is about.

    Returns:
        The verdict.
    """
    allowed = numbers_in(decision)
    unseen = tuple(number for number in extract_numbers(text) if number not in allowed)
    return ValidationResult(accepted=not unseen, unseen_numbers=unseen)


@dataclass
class Explanation:
    """One explanation of a decision.

    Attributes:
        text: The explanation to show.
        source: ``model`` or ``template``.
        reason: Why it is what it is.
        model: The model that wrote it, when a model did.
        unseen_numbers: The numbers that caused a refusal, so the refusal
            can be diagnosed rather than guessed at.
    """

    text: str
    source: str = SOURCE_TEMPLATE
    reason: str = REASON_VALIDATED
    model: Optional[str] = None
    unseen_numbers: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Render the explanation for the API response.

        Returns:
            The explanation.
        """
        return {
            "text": self.text,
            "source": self.source,
            "reason": self.reason,
            "model": self.model,
            "unseen_numbers": list(self.unseen_numbers),
        }


def template_explanation(decision: dict[str, Any], reason: str) -> Explanation:
    """Build the explanation from the Phase 2 template.

    The template is the Phase 2 action card, with a sentence that says
    what the decision was and how sure the engine was. It contains only
    numbers that came out of the decision.

    Args:
        decision: The decision the text is about.
        reason: Why the template is being used.

    Returns:
        The explanation.
    """
    channel = str(decision.get("recommended_channel", "SAFE_DEFAULT"))
    fallback = decision.get("fallback_channel")
    confidence = decision.get("confidence")

    steps = action_steps_for(channel, fallback)
    lines = [
        f"The recommended channel is {channel}.",
    ]
    if confidence is not None:
        lines.append(f"The engine is {float(confidence) * 100:.0f}% confident in that choice.")
    if decision.get("fallback_used"):
        lines.append(
            "The confidence gate did not clear, so a person checks the unit before it moves."
        )
    lines.append("")
    lines.append("What to do:")
    for step in steps:
        lines.append(f"{step.order}. {step.title}. {step.detail}")
        if step.reference:
            lines.append(f"   Follows {step.reference}.")

    return Explanation(
        text="\n".join(lines),
        source=SOURCE_TEMPLATE,
        reason=reason,
    )


class ExplainerClient(Protocol):
    """What the explainer needs from a model runtime."""

    async def generate(self, decision: dict[str, Any]) -> str:
        """Return the model's text for a decision.

        Args:
            decision: The decision to explain.

        Returns:
            The generated text.
        """


class OllamaExplainer:
    """An explainer backed by a local Ollama server.

    The model is asked for a paragraph and nothing else. It is given the
    decision as JSON and the system prompt above, and the output is
    checked by the caller.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Set up the client.

        Args:
            base_url: Where the Ollama server is. The setting is used when
                it is left out.
            model: The model to use. The setting is used when it is left
                out.
            timeout: How long to wait. The setting is used when it is left
                out.
        """
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout if timeout is not None else settings.OLLAMA_TIMEOUT_SECONDS

    async def generate(self, decision: dict[str, Any]) -> str:
        """Ask the model to explain the decision.

        Args:
            decision: The decision to explain.

        Returns:
            The generated text.

        Raises:
            httpx.HTTPError: When the server cannot be reached.
            httpx.TimeoutException: When the model takes too long.
        """
        import httpx

        payload = {
            "model": self.model,
            "system": SYSTEM_PROMPT,
            "prompt": (
                "Explain this decision to the operator.\n\n"
                f"{json.dumps(decision, indent=2, sort_keys=True, default=str)}"
            ),
            "stream": False,
            # The numbers in the decision are what the model may repeat, so
            # it is given the context window it needs and no more.
            "options": {"temperature": 0.2, "num_predict": 300},
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        text = body.get("response", "")
        return str(text).strip()


class ExplainerService:
    """Produces the explanation of a decision, or says why it cannot."""

    def __init__(self, client: Optional[ExplainerClient] = None) -> None:
        """Set up the service.

        Args:
            client: The model runtime. A local Ollama server is used when
                it is left out.
        """
        self._client = client

    def _runtime(self) -> ExplainerClient:
        """Return the model runtime to use."""
        return self._client if self._client is not None else OllamaExplainer()

    async def explain(self, decision: dict[str, Any]) -> Explanation:
        """Explain a decision.

        The model's text is only shown when every number in it appears in
        the decision. Otherwise the Phase 2 template is used, and the
        reason says why.

        Args:
            decision: The decision to explain.

        Returns:
            The explanation.
        """
        if not settings.OLLAMA_ENABLED:
            return template_explanation(decision, REASON_DISABLED)

        runtime = self._runtime()

        try:
            text = await runtime.generate(decision)
        except Exception as error:  # noqa: BLE001 - any failure falls back
            reason = REASON_MODEL_TIMEOUT if _is_timeout(error) else REASON_MODEL_ERROR
            logger.warning(
                "explanation.model_failed",
                reason=reason,
                error=str(error),
            )
            return template_explanation(decision, reason)

        if not text.strip():
            return template_explanation(decision, REASON_EMPTY)

        verdict = validate_explanation(text, decision)
        if not verdict.accepted:
            logger.info(
                "explanation.rejected",
                unseen_numbers=list(verdict.unseen_numbers),
            )
            return Explanation(
                text=template_explanation(decision, REASON_UNSEEN_NUMBER).text,
                source=SOURCE_TEMPLATE,
                reason=REASON_UNSEEN_NUMBER,
                unseen_numbers=verdict.unseen_numbers,
            )

        return Explanation(
            text=text,
            source=SOURCE_MODEL,
            reason=REASON_VALIDATED,
            model=getattr(runtime, "model", None),
        )


def _is_timeout(error: Exception) -> bool:
    """Whether an error is a timeout.

    Args:
        error: The error.

    Returns:
        True when the model took too long.
    """
    try:
        import httpx
    except ImportError:  # pragma: no cover - httpx is a dependency
        return False
    return isinstance(error, httpx.TimeoutException)


@dataclass
class ExplanationAccumulator:
    """Collects the explanations of a batch of decisions.

    Used by the acceptance test, which has to check that every explanation
    either passes the validator or is the template.

    Attributes:
        explanations: The explanations, in the order they were produced.
    """

    explanations: list[Explanation] = field(default_factory=list)

    def add(self, explanation: Explanation) -> None:
        """Record one explanation.

        Args:
            explanation: The explanation.
        """
        self.explanations.append(explanation)

    @property
    def all_valid(self) -> bool:
        """Whether every explanation is model-written and validated."""
        return all(explanation.source == SOURCE_MODEL for explanation in self.explanations)

    @property
    def all_safe(self) -> bool:
        """Whether every explanation is either validated or the template.

        This is the acceptance criterion: an explanation that was refused
        has to be the template, never a piece of model text that slipped
        through.
        """
        return all(
            explanation.source == SOURCE_TEMPLATE
            or (explanation.source == SOURCE_MODEL and explanation.reason == REASON_VALIDATED)
            for explanation in self.explanations
        )


def decision_payload(decision: Any) -> dict[str, Any]:
    """Return the decision as the payload the model is given.

    Args:
        decision: The stored decision.

    Returns:
        The payload.
    """
    if hasattr(decision, "id") and hasattr(decision, "candidates"):
        return {
            "id": str(decision.id),
            "unit_id": str(decision.unit_id),
            "model_version": decision.model_version,
            "risk_profile": decision.risk_profile,
            "recommended_channel": decision.recommended_channel,
            "confidence": decision.confidence,
            "fallback_used": decision.fallback_used,
            "fallback_channel": decision.fallback_channel,
            "candidates": decision.candidates,
            "reasons": decision.reasons,
            "flip_conditions": decision.flip_conditions,
            "action_steps": decision.action_steps,
        }
    return dict(decision)


def sequence_numbers(values: Sequence[str]) -> set[str]:
    """Return a set of normalised numbers.

    Args:
        values: The numbers.

    Returns:
        The normalised numbers.
    """
    return {normalise_number(value) for value in values}
