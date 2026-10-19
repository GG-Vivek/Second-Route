"""
Action card templates (Phase 2 - F2.10).

Every channel in the decision space has a template. The templates are static
text - no LLM is involved in this phase (PLAN.md principle 3: the LLM writes
words, never decisions).

The ``SAFE_DEFAULT`` template deliberately starts with a human inspection
step, because a fallback decision is a statement that the machine is not
confident enough to route the unit on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

__all__ = [
    "ActionStep",
    "action_steps_for",
    "has_template",
]


@dataclass(frozen=True, slots=True)
class ActionStep:
    """One instruction for the operator.

    Attributes:
        order: 1-based position in the list.
        title: Short imperative title.
        detail: What to do and why.
        reference: Optional standard or regulation the step follows.
    """

    order: int
    title: str
    detail: str
    reference: str | None = None

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable view of the step."""
        return {
            "order": self.order,
            "title": self.title,
            "detail": self.detail,
            "reference": self.reference,
        }


_RESELL_OPEN_BOX: Final[tuple[ActionStep, ...]] = (
    ActionStep(
        order=1,
        title="Wipe the device",
        detail=(
            "Factory-reset the device and confirm the storage is erased before it "
            "leaves the warehouse."
        ),
        reference="NIST SP 800-88 Rev. 1",
    ),
    ActionStep(
        order=2,
        title="Photograph four angles",
        detail="Capture the screen, lid, base and any cosmetic damage in good light.",
    ),
    ActionStep(
        order=3,
        title="Apply the open-box label",
        detail=(
            "Attach the open-box label and list the known cosmetic issue in the "
            "listing so the buyer is not surprised."
        ),
    ),
    ActionStep(
        order=4,
        title="Pack with the original accessories",
        detail="Include only the accessories recorded on the inspection.",
    ),
    ActionStep(
        order=5,
        title="Ship within the open-box window",
        detail="List on the channel immediately - open-box value decays with time.",
    ),
)

_RESELL_REFURB: Final[tuple[ActionStep, ...]] = (
    ActionStep(
        order=1,
        title="Complete the repair",
        detail="Work through the failed functional tests and record what was replaced.",
    ),
    ActionStep(
        order=2,
        title="Re-run the functional test suite",
        detail="Every test that failed on intake must pass before the unit is listed.",
    ),
    ActionStep(
        order=3,
        title="Regrade and re-photograph",
        detail=(
            "The repair changes the condition. Record a new cosmetic grade and refresh the photos."
        ),
    ),
    ActionStep(
        order=4,
        title="Wipe and certify",
        detail=("Erase the device and record the wipe certificate against the unit."),
        reference="NIST SP 800-88 Rev. 1",
    ),
    ActionStep(
        order=5,
        title="List with a refurbished warranty",
        detail="Attach the refurbished warranty terms and the repair summary.",
    ),
)

_RECYCLE: Final[tuple[ActionStep, ...]] = (
    ActionStep(
        order=1,
        title="Verify recyclability",
        detail=(
            "Confirm the unit and its parts are not covered by a take-back "
            "obligation before disposal."
        ),
    ),
    ActionStep(
        order=2,
        title="Remove and segregate the battery",
        detail="Batteries are regulated. Ship them through the approved battery route.",
        reference="PHMSA / DOT battery rules",
    ),
    ActionStep(
        order=3,
        title="Record the recovery receipt",
        detail="File the weight and recovery receipt so the net value can be reconciled.",
    ),
    ActionStep(
        order=4,
        title="Sanitise the data-bearing parts",
        detail="Destroy storage media that cannot be reused.",
        reference="NIST SP 800-88 Rev. 1",
    ),
)

_DONATE: Final[tuple[ActionStep, ...]] = (
    ActionStep(
        order=1,
        title="Confirm donation eligibility",
        detail="Make sure the unit is working, safe and useful to the recipient.",
    ),
    ActionStep(
        order=2,
        title="Wipe the device",
        detail="Erase the device and record the wipe before it leaves.",
        reference="NIST SP 800-88 Rev. 1",
    ),
    ActionStep(
        order=3,
        title="Record the recipient receipt",
        detail=(
            "Keep the donation receipt. It is the evidence for the tax treatment "
            "claimed on this unit."
        ),
        reference="IRS Pub 526",
    ),
)

_SAFE_DEFAULT: Final[tuple[ActionStep, ...]] = (
    ActionStep(
        order=1,
        title="Human inspection before routing",
        detail=(
            "The confidence gate did not clear, so no channel is recommended "
            "automatically. A second inspector must confirm the condition and "
            "pick the channel."
        ),
    ),
    ActionStep(
        order=2,
        title="Check for an activation lock",
        detail=(
            "Activation lock is the most common reason a resale route is blocked. "
            "Confirm the lock state before anything else."
        ),
    ),
    ActionStep(
        order=3,
        title="Check the battery health reading",
        detail="A single bad battery reading can move a unit across two grades.",
    ),
    ActionStep(
        order=4,
        title="Re-run the decision",
        detail=(
            "Once the condition is confirmed, record the corrected inspection and "
            "run the decision again."
        ),
    ),
)

_TEMPLATES: Final[dict[str, tuple[ActionStep, ...]]] = {
    "RESELL_OPEN_BOX": _RESELL_OPEN_BOX,
    "RESELL_REFURB": _RESELL_REFURB,
    "RECYCLE": _RECYCLE,
    "DONATE": _DONATE,
    "SAFE_DEFAULT": _SAFE_DEFAULT,
}


def has_template(channel: str) -> bool:
    """Return whether a channel has an action template."""
    return channel in _TEMPLATES


def action_steps_for(channel: str, fallback_channel: str | None = None) -> list[ActionStep]:
    """Return the action steps for a channel.

    Args:
        channel: The recommended channel, or ``SAFE_DEFAULT``.
        fallback_channel: The channel the SAFE_DEFAULT fallback points at, used
            to add a closing step.

    Returns:
        The ordered action steps. Unknown channels fall back to the
        ``SAFE_DEFAULT`` template so the card always has guidance.
    """
    steps = _TEMPLATES.get(channel)
    if steps is None:
        steps = _SAFE_DEFAULT

    if channel == "SAFE_DEFAULT" and fallback_channel:
        extra = ActionStep(
            order=len(steps) + 1,
            title=f"Route to {fallback_channel} once confirmed",
            detail=(
                f"The conservative floor for this unit is {fallback_channel}. "
                "Use it if the human inspection confirms the condition."
            ),
        )
        return [*steps, extra]

    return list(steps)
