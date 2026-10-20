"""
Tests for the explanation text (Phase 5 - F5.7).

The acceptance criterion is that every explanation either passes the
validator or is the template, and that no number the decision does not
contain ever reaches the operator.

The validator is the safety property, so it is tested on its own, hard,
before anything that depends on a model.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any, Optional

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.decision.models import Decision
from secondroute.identity.models import SKU
from secondroute.instructions.explainer import (
    REASON_DISABLED,
    REASON_EMPTY,
    REASON_MODEL_ERROR,
    REASON_MODEL_TIMEOUT,
    REASON_UNSEEN_NUMBER,
    REASON_VALIDATED,
    SOURCE_MODEL,
    SOURCE_TEMPLATE,
    ExplainerService,
    Explanation,
    ValidationResult,
    extract_numbers,
    normalise_number,
    numbers_in,
    template_explanation,
    validate_explanation,
)
from secondroute.instructions.models import DecisionExplanation
from secondroute.intake.models import Inspection, OrderChannel, ReturnReasonCode, Unit

#: A decision with the numbers an explanation is allowed to repeat.
DECISION: dict[str, Any] = {
    "id": "11111111-1111-1111-1111-111111111111",
    "model_version": "decision-v1",
    "risk_profile": "balanced",
    "recommended_channel": "RESELL_OPEN_BOX",
    "confidence": 0.85,
    "fallback_used": False,
    "candidates": [
        {
            "channel": "RESELL_OPEN_BOX",
            "eligible": True,
            "mean": 900.0,
            "p10": 800.0,
            "p50": 900.0,
            "p90": 1000.0,
            "stddev": 50.0,
        },
        {
            "channel": "RECYCLE",
            "eligible": True,
            "mean": 100.0,
            "p10": 50.0,
            "p50": 100.0,
            "p90": 150.0,
            "stddev": 25.0,
        },
    ],
    "reasons": [{"code": "price", "contribution": 120.0}],
}


class FakeExplainer:
    """A model runtime that says what the test tells it to say."""

    def __init__(self, text: str = "", error: Optional[Exception] = None) -> None:
        """Set up the fake.

        Args:
            text: What the model says.
            error: The error the model raises, if any.
        """
        self.text = text
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def generate(self, decision: dict[str, Any]) -> str:
        """Return the text, or raise the error.

        Args:
            decision: The decision.

        Returns:
            The text.

        Raises:
            Exception: The error the fake was given.
        """
        self.calls.append(decision)
        if self.error is not None:
            raise self.error
        return self.text

    model = "fake-model"


class TestNumberExtraction:
    """The numbers in a piece of text."""

    @pytest.mark.asyncio
    async def test_plain_numbers(self) -> None:
        """Test that a plain number is found."""
        assert extract_numbers("the net is 900") == ["900"]

    @pytest.mark.asyncio
    async def test_decimal_numbers(self) -> None:
        """Test that a decimal number is found."""
        assert extract_numbers("the net is 900.50") == ["900.5"]

    @pytest.mark.asyncio
    async def test_thousands_separators(self) -> None:
        """Test that a separated number is found."""
        assert extract_numbers("the net is 1,200.00") == ["1200"]

    @pytest.mark.asyncio
    async def test_a_currency_amount(self) -> None:
        """Test that a currency amount is found."""
        assert extract_numbers("about $900") == ["900"]

    @pytest.mark.asyncio
    async def test_a_percentage(self) -> None:
        """Test that a percentage is found."""
        assert extract_numbers("85% confident") == ["85"]

    @pytest.mark.asyncio
    async def test_a_word_with_digits_is_not_a_number(self) -> None:
        """Test that an identifier is left alone."""
        assert extract_numbers("the model decision-v1 made this") == []

    @pytest.mark.asyncio
    async def test_no_numbers(self) -> None:
        """Test that text without numbers gives nothing."""
        assert extract_numbers("the unit is good") == []

    @pytest.mark.asyncio
    async def test_the_repeats_are_removed(self) -> None:
        """Test that the same number is only listed once."""
        assert extract_numbers("900 and 900 and 900") == ["900"]

    @pytest.mark.asyncio
    async def test_the_normalisation(self) -> None:
        """Test that the forms of a number are folded together."""
        assert normalise_number("900") == "900"
        assert normalise_number("900.00") == "900"
        assert normalise_number("1,200") == "1200"
        assert normalise_number("900.50") == "900.5"


class TestNumbersInTheDecision:
    """The numbers the decision allows."""

    @pytest.mark.asyncio
    async def test_the_candidate_numbers_are_allowed(self) -> None:
        """Test that the numbers in the candidates are allowed."""
        allowed = numbers_in(DECISION)
        assert "900" in allowed
        assert "800" in allowed
        assert "1000" in allowed

    @pytest.mark.asyncio
    async def test_the_keys_are_allowed(self) -> None:
        """Test that a number in a key is allowed."""
        allowed = numbers_in({"2024-01-15": "value"})
        assert "2024" in allowed
        assert "1" in allowed
        assert "15" in allowed

    @pytest.mark.asyncio
    async def test_a_boolean_is_not_a_number(self) -> None:
        """Test that a boolean is not treated as a number."""
        assert numbers_in({"fallback_used": True}) == set()


class TestValidator:
    """The validator: the safety property of the whole feature."""

    @pytest.mark.asyncio
    async def test_text_with_only_known_numbers_is_accepted(self) -> None:
        """Test that a text that repeats the decision's numbers passes."""
        text = (
            "The recommended channel is RESELL_OPEN_BOX, with a net of about "
            "900 and a range from 800 to 1000. The engine is 85% confident."
        )
        verdict = validate_explanation(text, DECISION)

        assert verdict.accepted is True
        assert verdict.unseen_numbers == ()
        assert verdict.reason == REASON_VALIDATED

    @pytest.mark.asyncio
    async def test_a_number_the_decision_lacks_is_refused(self) -> None:
        """Test that a number the decision does not have is caught."""
        text = "The recommended channel is RESELL_OPEN_BOX, worth about 1200."

        verdict = validate_explanation(text, DECISION)

        assert verdict.accepted is False
        assert verdict.unseen_numbers == ("1200",)
        assert verdict.reason == REASON_UNSEEN_NUMBER

    @pytest.mark.asyncio
    async def test_a_percentage_of_a_probability_is_allowed(self) -> None:
        """Test that a probability may be written as a percentage.

        The decision holds 0.85 and the model writes "85% confident". That
        is the same number written the way a person writes it, and
        refusing it would refuse almost every sentence.
        """
        verdict = validate_explanation("The engine is 85% confident.", DECISION)

        assert verdict.accepted is True

    @pytest.mark.asyncio
    async def test_every_percentage_of_a_probability_is_allowed(self) -> None:
        """Test that the rounding does not let a probability slip.

        0.55 times 100 is 55.00000000000001 in floating point, so the
        percentage form has to be rounded. Without that, the model saying
        "55% confident" about a decision that holds 0.55 would be refused
        for a number it is allowed to repeat.
        """
        for percent in range(50, 100):
            confidence = percent / 100
            decision = {**DECISION, "confidence": confidence}
            verdict = validate_explanation(f"The engine is {percent}% confident.", decision)
            assert verdict.accepted is True, f"{percent}% was refused"

    @pytest.mark.asyncio
    async def test_a_percentage_the_decision_lacks_is_refused(self) -> None:
        """Test that an invented percentage is caught."""
        verdict = validate_explanation("We are 92% certain of this.", DECISION)

        assert verdict.accepted is False
        assert "92" in verdict.unseen_numbers

    @pytest.mark.asyncio
    async def test_a_date_the_decision_lacks_is_refused(self) -> None:
        """Test that an invented date is caught."""
        verdict = validate_explanation("This should sell by March 15.", DECISION)

        assert verdict.accepted is False
        assert "15" in verdict.unseen_numbers

    @pytest.mark.asyncio
    async def test_text_without_numbers_is_accepted(self) -> None:
        """Test that a text with no numbers is fine."""
        verdict = validate_explanation("The unit is in good condition.", DECISION)

        assert verdict.accepted is True

    @pytest.mark.asyncio
    async def test_the_same_number_in_another_form_is_accepted(self) -> None:
        """Test that a number written differently is still allowed."""
        verdict = validate_explanation("The net is 900.00, so about $900.", DECISION)

        assert verdict.accepted is True


class TestTemplateFallback:
    """The template is what is shown when the model cannot be trusted."""

    @pytest.mark.asyncio
    async def test_the_template_names_the_channel(self) -> None:
        """Test that the template says what was decided."""
        explanation = template_explanation(DECISION, REASON_VALIDATED)

        assert explanation.source == SOURCE_TEMPLATE
        assert "RESELL_OPEN_BOX" in explanation.text
        assert "85%" in explanation.text

    @pytest.mark.asyncio
    async def test_the_template_uses_the_action_steps(self) -> None:
        """Test that the template carries the Phase 2 steps."""
        explanation = template_explanation(DECISION, REASON_VALIDATED)

        assert "Wipe the device" in explanation.text

    @pytest.mark.asyncio
    async def test_the_template_is_not_guarded_by_the_validator(self) -> None:
        """Test that the template is trusted by construction.

        The validator guards the *model's* text. The template is written
        by the engine, and it carries the step ordinals and the standard
        references - "NIST SP 800-88 Rev. 1" - which are numbers about
        the procedure rather than about the unit. There is nothing to
        validate, because there is nothing that could have been invented.
        """
        text = template_explanation(DECISION, REASON_VALIDATED).text

        verdict = validate_explanation(text, DECISION)

        assert verdict.accepted is False
        # The numbers it does carry are the engine's own: the step
        # ordinals and the standard the step follows.
        assert "1" in verdict.unseen_numbers
        assert "88" in verdict.unseen_numbers
        # "800" is in the decision, as the p10 of the recommended channel,
        # so it is not an unseen number.
        assert "800" not in verdict.unseen_numbers


class TestExplainerService:
    """The service that decides what to show."""

    @pytest.mark.asyncio
    async def test_a_valid_explanation_is_kept(self) -> None:
        """Test that a validated explanation is shown."""
        fake = FakeExplainer("The engine picked RESELL_OPEN_BOX at a net of 900.")

        explanation = await ExplainerService(fake).explain(DECISION)

        assert explanation.source == SOURCE_MODEL
        assert explanation.reason == REASON_VALIDATED
        assert explanation.text == "The engine picked RESELL_OPEN_BOX at a net of 900."
        assert explanation.model == "fake-model"

    @pytest.mark.asyncio
    async def test_an_unseen_number_falls_back_to_the_template(self) -> None:
        """Test that an explanation with an unknown number is thrown away."""
        fake = FakeExplainer("This will fetch 2000 at least.")

        explanation = await ExplainerService(fake).explain(DECISION)

        assert explanation.source == SOURCE_TEMPLATE
        assert explanation.reason == REASON_UNSEEN_NUMBER
        assert explanation.unseen_numbers == ("2000",)
        assert "2000" not in explanation.text

    @pytest.mark.asyncio
    async def test_a_model_failure_falls_back_to_the_template(self) -> None:
        """Test that an unreachable model falls back."""
        fake = FakeExplainer(error=RuntimeError("no model here"))

        explanation = await ExplainerService(fake).explain(DECISION)

        assert explanation.source == SOURCE_TEMPLATE
        assert explanation.reason == REASON_MODEL_ERROR

    @pytest.mark.asyncio
    async def test_a_timeout_falls_back_to_the_template(self) -> None:
        """Test that a slow model falls back."""
        import httpx

        fake = FakeExplainer(error=httpx.TimeoutException("too slow"))

        explanation = await ExplainerService(fake).explain(DECISION)

        assert explanation.source == SOURCE_TEMPLATE
        assert explanation.reason == REASON_MODEL_TIMEOUT

    @pytest.mark.asyncio
    async def test_empty_output_falls_back_to_the_template(self) -> None:
        """Test that an empty answer falls back."""
        fake = FakeExplainer("   ")

        explanation = await ExplainerService(fake).explain(DECISION)

        assert explanation.source == SOURCE_TEMPLATE
        assert explanation.reason == REASON_EMPTY

    @pytest.mark.asyncio
    async def test_the_model_only_sees_the_decision(self) -> None:
        """Test that the model is given the decision and nothing else."""
        fake = FakeExplainer("A short explanation.")

        await ExplainerService(fake).explain(DECISION)

        assert len(fake.calls) == 1
        assert fake.calls[0]["recommended_channel"] == "RESELL_OPEN_BOX"

    @pytest.mark.asyncio
    async def test_the_model_can_be_switched_off(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that a deployment without a model keeps the template."""
        from secondroute.core.config import settings

        monkeypatch.setattr(settings, "OLLAMA_ENABLED", False)
        fake = FakeExplainer("Should never be used.")

        explanation = await ExplainerService(fake).explain(DECISION)

        assert explanation.source == SOURCE_TEMPLATE
        assert explanation.reason == REASON_DISABLED
        assert fake.calls == []


# ---------------------------------------------------------------------
# The endpoint
# ---------------------------------------------------------------------


async def _make_unit(db_session: AsyncSession, suffix: str = "") -> Unit:
    """Create a unit with an inspection."""
    sku = SKU(
        family="Test",
        model_name=f"Model{suffix}",
        year="2024",
        storage_gb="512",
        ram_gb="16",
        color="Black",
        region="US",
        specs_json={},
        source="test",
        as_of=date(2024, 1, 15),
    )
    db_session.add(sku)
    await db_session.commit()
    await db_session.refresh(sku)

    unit = Unit(
        sku_id=sku.id,
        serial=f"EXP{suffix}",
        return_reason_code=ReturnReasonCode.BUYER_REMORSE,
        order_channel=OrderChannel.ONLINE,
    )
    db_session.add(unit)
    await db_session.commit()
    await db_session.refresh(unit)

    inspection = Inspection(
        unit_id=unit.id,
        battery_health_pct="95",
        cosmetic_grade="A",
        functional_tests_json={},
        activation_lock="none",
        accessories_json={},
    )
    db_session.add(inspection)
    await db_session.commit()

    return unit


async def _make_decision(db_session: AsyncSession, unit: Unit) -> Decision:
    """Create a decision."""
    decision = Decision(
        unit_id=unit.id,
        model_version="decision-v1",
        risk_profile="balanced",
        recommended_channel="RESELL_OPEN_BOX",
        confidence=0.85,
        fallback_used=False,
        candidates_json=json.dumps(DECISION["candidates"]),
        reasons_json=json.dumps(DECISION["reasons"]),
        flip_conditions_json="[]",
        data_freshness_json=json.dumps({"is_synthetic": True}),
        action_steps_json="[]",
        input_snapshot_hash="abc123",
        input_snapshot_json="{}",
    )
    db_session.add(decision)
    await db_session.commit()
    await db_session.refresh(decision)
    return decision


class TestExplanationEndpoint:
    """The endpoint that explains a decision."""

    @pytest.mark.asyncio
    async def test_the_explanation_is_stored(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that asking for an explanation writes a row."""
        from secondroute.decision import api as decision_api

        fake = FakeExplainer("The engine picked RESELL_OPEN_BOX at a net of 900.")
        monkeypatch.setattr(decision_api.ExplainerService, "_runtime", lambda _self: fake)

        unit = await _make_unit(db_session, suffix="1")
        decision = await _make_decision(db_session, unit)

        response = await client.post(f"/api/v1/decisions/{decision.id}/explanation")

        assert response.status_code == 200
        data = response.json()
        assert data["source"] == SOURCE_MODEL
        assert data["reason"] == REASON_VALIDATED
        assert data["text"] == "The engine picked RESELL_OPEN_BOX at a net of 900."

        stored = (await db_session.execute(select(DecisionExplanation))).scalars().all()
        assert len(stored) == 1
        assert stored[0].decision_id == decision.id
        assert stored[0].is_synthetic is True

    @pytest.mark.asyncio
    async def test_the_explanation_is_reused(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a second ask does not call the model again."""
        from secondroute.decision import api as decision_api

        fake = FakeExplainer("The engine picked RESELL_OPEN_BOX at a net of 900.")
        monkeypatch.setattr(decision_api.ExplainerService, "_runtime", lambda _self: fake)

        unit = await _make_unit(db_session, suffix="2")
        decision = await _make_decision(db_session, unit)

        await client.post(f"/api/v1/decisions/{decision.id}/explanation")
        await client.post(f"/api/v1/decisions/{decision.id}/explanation")

        assert len(fake.calls) == 1
        stored = (await db_session.execute(select(DecisionExplanation))).scalars().all()
        assert len(stored) == 1

    @pytest.mark.asyncio
    async def test_a_refresh_writes_a_new_row(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a refresh asks the model again."""
        from secondroute.decision import api as decision_api

        fake = FakeExplainer("The engine picked RESELL_OPEN_BOX at a net of 900.")
        monkeypatch.setattr(decision_api.ExplainerService, "_runtime", lambda _self: fake)

        unit = await _make_unit(db_session, suffix="3")
        decision = await _make_decision(db_session, unit)

        await client.post(f"/api/v1/decisions/{decision.id}/explanation")
        await client.post(f"/api/v1/decisions/{decision.id}/explanation?refresh=true")

        assert len(fake.calls) == 2
        stored = (await db_session.execute(select(DecisionExplanation))).scalars().all()
        assert len(stored) == 2

    @pytest.mark.asyncio
    async def test_an_unseen_number_never_reaches_the_operator(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a number the decision lacks is not returned."""
        from secondroute.decision import api as decision_api

        fake = FakeExplainer("This will fetch 2000 at least.")
        monkeypatch.setattr(decision_api.ExplainerService, "_runtime", lambda _self: fake)

        unit = await _make_unit(db_session, suffix="4")
        decision = await _make_decision(db_session, unit)

        response = await client.post(f"/api/v1/decisions/{decision.id}/explanation")

        assert response.status_code == 200
        data = response.json()
        assert data["source"] == SOURCE_TEMPLATE
        assert data["unseen_numbers"] == ["2000"]
        assert "2000" not in data["text"]

    @pytest.mark.asyncio
    async def test_an_unknown_decision_is_a_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that explaining nothing is a 404."""
        from uuid import uuid4

        response = await client.post(f"/api/v1/decisions/{uuid4()}/explanation")

        assert response.status_code == 404


class TestAcceptance:
    """The acceptance criterion for F5.7.

    "On a test set of 100 decisions, every output either passes the
    validator or uses the template. No unseen numbers reach the UI."
    """

    @pytest.mark.asyncio
    async def test_a_hundred_decisions_never_leak_a_number(self) -> None:
        """Test that the guarantee holds for any output the model gives.

        The model here is a stub that deliberately misbehaves: for half the
        decisions it repeats a number from the decision, and for the other
        half it invents one. Whatever it does, the operator only ever sees
        a validated explanation or the template.
        """
        service = ExplainerService()
        seen: list[Explanation] = []

        for index in range(100):
            decision = {
                **DECISION,
                "id": f"{index:08d}-0000-0000-0000-000000000000",
                "confidence": 0.5 + (index % 50) / 100.0,
            }
            if index % 2 == 0:
                # A number the decision contains.
                stub = FakeExplainer("The net is 900 and the range is 800 to 1000.")
            else:
                # A number nobody produced.
                stub = FakeExplainer(f"This will fetch {4000 + index} at least.")

            explanation = await ExplainerService(stub).explain(decision)
            seen.append(explanation)

        # Every explanation is either validated model text or the template.
        for explanation in seen:
            if explanation.source == SOURCE_MODEL:
                assert explanation.reason == REASON_VALIDATED
                assert explanation.unseen_numbers == ()
            else:
                assert explanation.source == SOURCE_TEMPLATE
                assert explanation.reason == REASON_UNSEEN_NUMBER

        # And the number that was invented is in none of them.
        for index in range(100):
            if index % 2 == 1:
                assert f"{4000 + index}" not in seen[index].text

        # The stub is not needed for the check itself.
        assert service is not None

    @pytest.mark.asyncio
    async def test_the_hundred_decisions_split_evenly(self) -> None:
        """Test that the stub really did exercise both branches."""
        sources: set[str] = set()
        for index in range(100):
            stub = FakeExplainer(
                "The net is 900." if index % 2 == 0 else f"This will fetch {4000 + index} at least."
            )
            explanation = await ExplainerService(stub).explain(DECISION)
            sources.add(explanation.source)

        assert sources == {SOURCE_MODEL, SOURCE_TEMPLATE}

    @pytest.mark.asyncio
    async def test_a_real_model_never_leaks_a_number(self) -> None:
        """Test the criterion against a real model, when there is one.

        This is the literal acceptance test. It needs a local Ollama with
        the model the settings name, so it is skipped when there is not
        one - a machine without a model keeps the suite green, and a
        machine with one runs the real thing.
        """
        import httpx

        from secondroute.core.config import settings

        base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{base_url}/api/tags")
                response.raise_for_status()
                available = {entry["name"] for entry in response.json().get("models", [])}
        except Exception:  # noqa: BLE001 - any failure means there is no model
            pytest.skip(f"No Ollama server at {base_url}")

        model = settings.OLLAMA_MODEL
        if model not in available and f"{model}:latest" not in available:
            pytest.skip(f"The model {model} is not pulled")

        service = ExplainerService()
        for index in range(100):
            decision = {
                **DECISION,
                "id": f"{index:08d}-0000-0000-0000-000000000000",
                "confidence": 0.5 + (index % 50) / 100.0,
            }
            explanation = await service.explain(decision)

            # The criterion: either it passed, or it is the template.
            if explanation.source == SOURCE_MODEL:
                assert explanation.reason == REASON_VALIDATED
                assert explanation.unseen_numbers == ()
                # And no unseen number reached the text.
                allowed = numbers_in(decision)
                for number in extract_numbers(explanation.text):
                    assert number in allowed
            else:
                assert explanation.source == SOURCE_TEMPLATE
                assert explanation.reason in (
                    REASON_UNSEEN_NUMBER,
                    REASON_MODEL_ERROR,
                    REASON_MODEL_TIMEOUT,
                    REASON_EMPTY,
                )
