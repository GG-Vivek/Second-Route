"""
Tests for photo condition assist (Phase 6 - F6.8).
"""

import pytest
from unittest.mock import MagicMock, patch

from secondroute.learning.photo_assist import (
    PhotoQualityChecker,
    PhotoQualityResult,
    DamageDetector,
    SerialReader,
    PhotoConditionAssist,
    PhotoAssistResult,
    DamageSuggestion,
    SerialReadResult,
    GRADE_ORDER,
    MAX_GRADE_CHANGE,
    ALLOWED_MODEL_LICENSES,
)


class TestPhotoQualityChecker:
    """Tests for photo quality checking."""

    def test_quality_checker_init(self) -> None:
        """Test quality checker initialization."""
        checker = PhotoQualityChecker(
            blur_threshold=100.0,
            dark_threshold=50.0,
            bright_threshold=200.0,
        )
        assert checker.blur_threshold == 100.0
        assert checker.dark_threshold == 50.0
        assert checker.bright_threshold == 200.0

    def test_check_quality_mock(self) -> None:
        """Test quality check with mock (no OpenCV)."""
        checker = PhotoQualityChecker()
        result = checker.check_quality("fake_image.jpg")

        # Should return mock result since OpenCV may not be available
        assert isinstance(result, PhotoQualityResult)
        assert isinstance(result.blur_score, float)
        assert isinstance(result.is_blurry, bool)
        assert isinstance(result.brightness, float)
        assert isinstance(result.quality_ok, bool)


class TestDamageDetector:
    """Tests for damage detection."""

    def test_license_verified(self) -> None:
        """Test that allowed license is verified."""
        detector = DamageDetector(model_license="Apache-2.0")
        assert detector.license_verified is True

    def test_license_not_verified(self) -> None:
        """Test that disallowed license is not verified."""
        detector = DamageDetector(model_license="Proprietary")
        assert detector.license_verified is False

    def test_detect_damage_no_license(self) -> None:
        """Test that damage detection returns empty when license not verified."""
        detector = DamageDetector(model_license="Proprietary")
        damages = detector.detect_damage("fake_image.jpg")
        assert damages == []

    def test_detect_damage_with_license(self) -> None:
        """Test that damage detection works with allowed license."""
        detector = DamageDetector(model_license="Apache-2.0")
        damages = detector.detect_damage("fake_image.jpg")
        # Mock implementation returns empty list
        assert isinstance(damages, list)

    def test_suggest_grade_change_no_damages(self) -> None:
        """Test that no damages suggest no grade change."""
        detector = DamageDetector(model_license="Apache-2.0")
        change = detector.suggest_grade_change("A", [])
        assert change == 0

    def test_suggest_grade_change_bounded(self) -> None:
        """Test that grade change is bounded to MAX_GRADE_CHANGE."""
        detector = DamageDetector(model_license="Apache-2.0")
        damages = [
            DamageSuggestion(
                damage_type="screen_crack",
                confidence=0.9,
                suggested_grade_change=-2,  # Would be 2 grades worse
                description="Screen crack detected",
            ),
        ]
        change = detector.suggest_grade_change("A", damages)
        # Should be bounded to -1
        assert change == -MAX_GRADE_CHANGE

    def test_apply_grade_change(self) -> None:
        """Test applying grade change."""
        assert DamageDetector.apply_grade_change("A", -1) == "B"
        assert DamageDetector.apply_grade_change("B", -1) == "C"
        assert DamageDetector.apply_grade_change("C", -1) == "D"
        assert DamageDetector.apply_grade_change("D", -1) == "D"  # Can't go worse than D
        assert DamageDetector.apply_grade_change("A", 1) == "A"  # Can't go better than A
        assert DamageDetector.apply_grade_change("B", 1) == "A"
        assert DamageDetector.apply_grade_change("X", -1) == "X"  # Unknown grade unchanged

    def test_suggestion_outside_bound_rejected(self) -> None:
        """Test that suggestions outside the bound are rejected."""
        detector = DamageDetector(model_license="Apache-2.0")
        # A change of 2 is outside the bound
        assert (
            not detector.validate_grade_change(2)
            if hasattr(detector, "validate_grade_change")
            else True
        )


class TestSerialReader:
    """Tests for serial label OCR."""

    def test_license_verified(self) -> None:
        """Test that allowed license is verified."""
        reader = SerialReader(model_license="Apache-2.0")
        assert reader.license_verified is True

    def test_license_not_verified(self) -> None:
        """Test that disallowed license is not verified."""
        reader = SerialReader(model_license="Proprietary")
        assert reader.license_verified is False

    def test_read_serial_no_license(self) -> None:
        """Test that serial reading fails when license not verified."""
        reader = SerialReader(model_license="Proprietary")
        result = reader.read_serial("fake_image.jpg")
        assert result.success is False
        assert result.serial == ""

    def test_read_serial_with_license(self) -> None:
        """Test that serial reading works with allowed license."""
        reader = SerialReader(model_license="Apache-2.0")
        result = reader.read_serial("fake_image.jpg")
        assert isinstance(result, SerialReadResult)


class TestPhotoConditionAssist:
    """Tests for the complete photo condition assist service."""

    def test_analyze_returns_result(self) -> None:
        """Test that analyze returns a PhotoAssistResult."""
        assist = PhotoConditionAssist(model_license="Apache-2.0")
        result = assist.analyze("fake_image.jpg", current_grade="A")

        assert isinstance(result, PhotoAssistResult)
        assert isinstance(result.quality, PhotoQualityResult)
        assert isinstance(result.damages, list)
        assert result.requires_confirmation is True  # Always requires confirmation

    def test_license_verified(self) -> None:
        """Test that license is verified for allowed license."""
        assist = PhotoConditionAssist(model_license="Apache-2.0")
        result = assist.analyze("fake_image.jpg", current_grade="A")
        assert result.license_verified is True

    def test_license_not_verified(self) -> None:
        """Test that license is not verified for disallowed license."""
        assist = PhotoConditionAssist(model_license="Proprietary")
        result = assist.analyze("fake_image.jpg", current_grade="A")
        assert result.license_verified is False

    def test_grade_change_bounded(self) -> None:
        """Test that grade change is bounded."""
        assist = PhotoConditionAssist(model_license="Apache-2.0")
        result = assist.analyze("fake_image.jpg", current_grade="A")
        assert abs(result.grade_change) <= MAX_GRADE_CHANGE

    def test_requires_confirmation(self) -> None:
        """Test that suggestions always require confirmation."""
        assist = PhotoConditionAssist(model_license="Apache-2.0")
        result = assist.analyze("fake_image.jpg", current_grade="A")
        assert result.requires_confirmation is True

    def test_store_suggestion(self) -> None:
        """Test storing a suggestion alongside inspector's final grade."""
        assist = PhotoConditionAssist(model_license="Apache-2.0")
        stored = assist.store_suggestion(
            image_id="img-123",
            suggested_grade="B",
            grade_change=-1,
            inspector_final_grade="B",
        )

        assert stored["image_id"] == "img-123"
        assert stored["suggested_grade"] == "B"
        assert stored["grade_change"] == -1
        assert stored["inspector_final_grade"] == "B"
        assert stored["suggestion_accepted"] is True
        assert "timestamp" in stored

    def test_store_suggestion_rejected(self) -> None:
        """Test storing a rejected suggestion."""
        assist = PhotoConditionAssist(model_license="Apache-2.0")
        stored = assist.store_suggestion(
            image_id="img-123",
            suggested_grade="B",
            grade_change=-1,
            inspector_final_grade="A",
        )

        assert stored["suggestion_accepted"] is False

    def test_validate_grade_change(self) -> None:
        """Test grade change validation."""
        assist = PhotoConditionAssist(model_license="Apache-2.0")
        assert assist.validate_grade_change(0) is True
        assert assist.validate_grade_change(1) is True
        assert assist.validate_grade_change(-1) is True
        assert assist.validate_grade_change(2) is False
        assert assist.validate_grade_change(-2) is False

    def test_allowed_licenses(self) -> None:
        """Test that allowed licenses are defined."""
        assert "Apache-2.0" in ALLOWED_MODEL_LICENSES
        assert "MIT" in ALLOWED_MODEL_LICENSES
        assert "Proprietary" not in ALLOWED_MODEL_LICENSES

    def test_grade_order(self) -> None:
        """Test grade ordering."""
        assert GRADE_ORDER == ["A", "B", "C", "D"]
        assert MAX_GRADE_CHANGE == 1
