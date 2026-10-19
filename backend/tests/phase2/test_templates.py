"""
Tests for the action card templates (F2.10).
"""

from __future__ import annotations

import pytest

from secondroute.decision.evaluator import PHASE2_CHANNELS
from secondroute.instructions.templates import (
    ActionStep,
    action_steps_for,
    has_template,
)


class TestChannelCoverage:
    """Every channel in the decision space has a template."""

    @pytest.mark.parametrize("channel", PHASE2_CHANNELS)
    def test_every_channel_has_a_template(self, channel: str) -> None:
        """Each evaluable channel has a template."""
        assert has_template(channel)
        assert action_steps_for(channel)

    def test_safe_default_has_a_template(self) -> None:
        """The SAFE_DEFAULT fallback has a template."""
        assert has_template("SAFE_DEFAULT")
        assert action_steps_for("SAFE_DEFAULT")

    def test_unknown_channel_falls_back_to_safe_default(self) -> None:
        """An unknown channel still produces guidance."""
        steps = action_steps_for("MYSTERY_CHANNEL")
        assert steps
        assert steps[0].title == "Human inspection before routing"

    def test_templates_are_distinct(self) -> None:
        """Each channel has its own instructions."""
        first = action_steps_for("RESELL_OPEN_BOX")
        second = action_steps_for("RESELL_REFURB")
        assert [step.title for step in first] != [step.title for step in second]


class TestStepContent:
    """The steps must be actionable."""

    def test_steps_are_ordered(self) -> None:
        """The steps come back in order."""
        for channel in (*PHASE2_CHANNELS, "SAFE_DEFAULT"):
            steps = action_steps_for(channel)
            assert [step.order for step in steps] == list(range(1, len(steps) + 1))

    def test_every_step_has_a_title_and_detail(self) -> None:
        """No step is empty."""
        for channel in (*PHASE2_CHANNELS, "SAFE_DEFAULT"):
            for step in action_steps_for(channel):
                assert step.title
                assert step.detail
                assert step.title[0].isupper()

    def test_open_box_references_the_nist_wipe_standard(self) -> None:
        """The open-box flow wipes per NIST 800-88."""
        steps = action_steps_for("RESELL_OPEN_BOX")
        references = [step.reference for step in steps if step.reference]
        assert any("NIST" in reference for reference in references)

    def test_recycle_references_the_battery_rules(self) -> None:
        """The recycling flow calls out the battery rules."""
        steps = action_steps_for("RECYCLE")
        references = [step.reference for step in steps if step.reference]
        assert any("battery" in reference.lower() for reference in references)

    def test_donate_records_a_receipt(self) -> None:
        """The donation flow keeps the receipt for the tax treatment."""
        steps = action_steps_for("DONATE")
        assert any("receipt" in step.title.lower() for step in steps)


class TestSafeDefaultSteps:
    """The fallback must ask for a human, not automate the call."""

    def test_first_step_is_a_human_inspection(self) -> None:
        """The first step is a human inspection."""
        steps = action_steps_for("SAFE_DEFAULT")
        assert steps[0].title == "Human inspection before routing"
        assert "confidence" in steps[0].detail.lower()

    def test_fallback_channel_is_added_when_known(self) -> None:
        """A closing step names the conservative floor."""
        steps = action_steps_for("SAFE_DEFAULT", fallback_channel="RESELL_REFURB")
        assert steps[-1].title == "Route to RESELL_REFURB once confirmed"

    def test_no_closing_step_without_a_fallback(self) -> None:
        """Without a floor there is no closing step."""
        steps = action_steps_for("SAFE_DEFAULT")
        assert not any("once confirmed" in step.title for step in steps)


class TestSerialisation:
    """The steps serialise for the API."""

    def test_step_serialises(self) -> None:
        """A step becomes a plain dictionary."""
        step = ActionStep(order=1, title="Wipe the device", detail="Erase it.", reference="NIST")
        payload = step.as_dict()
        assert payload == {
            "order": 1,
            "title": "Wipe the device",
            "detail": "Erase it.",
            "reference": "NIST",
        }

    @pytest.mark.parametrize("channel", [*PHASE2_CHANNELS, "SAFE_DEFAULT"])
    def test_all_steps_serialise(self, channel: str) -> None:
        """Every step of every channel serialises."""
        for step in action_steps_for(channel):
            payload = step.as_dict()
            assert isinstance(payload["order"], int)
            assert payload["order"] >= 1
            assert payload["title"]
