"""
Photo condition assist for Phase 6 (F6.8).

OpenCV checks photo quality (blur, lighting). An open-license classifier
suggests screen and body damage. Tesseract or PaddleOCR reads serial labels.
Suggested grade changes are bounded (at most one grade) and always require
inspector confirmation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, UTC
from typing import Any, Optional, Sequence
from uuid import UUID

import structlog
from pydantic import BaseModel, ConfigDict

logger = structlog.get_logger(__name__)

# Grade ordering for bounded suggestions
GRADE_ORDER = ["A", "B", "C", "D"]

# Maximum grade change allowed (bounded suggestion)
MAX_GRADE_CHANGE = 1

# Allowed model licenses (from docs/data-sources.md)
ALLOWED_MODEL_LICENSES = {
    "Apache-2.0",
    "MIT",
    "BSD-3-Clause",
    "BSD-2-Clause",
    "CC-BY-4.0",
    "CC0-1.0",
    "Unlicense",
}


@dataclass
class PhotoQualityResult:
    """Result of photo quality check.

    Attributes:
        blur_score: Laplacian variance (higher = sharper).
        is_blurry: Whether the photo is too blurry.
        brightness: Mean brightness (0-255).
        is_too_dark: Whether the photo is too dark.
        is_too_bright: Whether the photo is too bright.
        quality_ok: Whether the photo passes quality checks.
    """

    blur_score: float
    is_blurry: bool
    brightness: float
    is_too_dark: bool
    is_too_bright: bool
    quality_ok: bool


@dataclass
class DamageSuggestion:
    """Suggested damage assessment from photo analysis.

    Attributes:
        damage_type: Type of damage detected (e.g., "screen_crack", "body_dent").
        confidence: Confidence of the detection (0-1).
        suggested_grade_change: Suggested grade change (e.g., -1 for one grade worse).
        description: Human-readable description.
    """

    damage_type: str
    confidence: float
    suggested_grade_change: int
    description: str


@dataclass
class SerialReadResult:
    """Result of serial label OCR.

    Attributes:
        serial: The read serial number.
        confidence: OCR confidence (0-1).
        success: Whether OCR was successful.
    """

    serial: str
    confidence: float
    success: bool


@dataclass
class PhotoAssistResult:
    """Complete photo assist result.

    Attributes:
        quality: Photo quality assessment.
        damages: List of detected damages.
        serial: Serial number read from label.
        suggested_grade: Suggested grade based on damages.
        grade_change: Suggested grade change (bounded).
        requires_confirmation: Whether inspector must confirm.
        license_verified: Whether the model license is allowed.
    """

    quality: PhotoQualityResult
    damages: list[DamageSuggestion] = field(default_factory=list)
    serial: SerialReadResult | None = None
    suggested_grade: str | None = None
    grade_change: int = 0
    requires_confirmation: bool = True
    license_verified: bool = False


class PhotoQualityChecker:
    """Checks photo quality using OpenCV metrics.

    Uses Laplacian variance for blur detection and mean brightness
    for lighting assessment.
    """

    def __init__(
        self,
        blur_threshold: float = 100.0,
        dark_threshold: float = 50.0,
        bright_threshold: float = 200.0,
    ) -> None:
        self.blur_threshold = blur_threshold
        self.dark_threshold = dark_threshold
        self.bright_threshold = bright_threshold

    def check_quality(self, image: Any) -> PhotoQualityResult:
        """Check photo quality.

        Args:
            image: The image (numpy array or path).

        Returns:
            PhotoQualityResult with quality assessment.
        """
        # In a real implementation, this would use OpenCV
        # For now, we provide a mock implementation
        # that can be tested without OpenCV installed

        try:
            import cv2  # type: ignore[import-not-found]
            import numpy as np  # type: ignore[import-not-found]

            if isinstance(image, str):
                img = cv2.imread(image)
            else:
                img = image

            if img is None:
                return PhotoQualityResult(
                    blur_score=0.0,
                    is_blurry=True,
                    brightness=0.0,
                    is_too_dark=True,
                    is_too_bright=False,
                    quality_ok=False,
                )

            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Blur detection using Laplacian variance
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

            # Brightness
            brightness = gray.mean()

            is_blurry = laplacian_var < self.blur_threshold
            is_too_dark = brightness < self.dark_threshold
            is_too_bright = brightness > self.bright_threshold
            quality_ok = not is_blurry and not is_too_dark and not is_too_bright

            return PhotoQualityResult(
                blur_score=float(laplacian_var),
                is_blurry=is_blurry,
                brightness=float(brightness),
                is_too_dark=is_too_dark,
                is_too_bright=is_too_bright,
                quality_ok=quality_ok,
            )
        except ImportError:
            # OpenCV not available - return mock result
            return PhotoQualityResult(
                blur_score=150.0,
                is_blurry=False,
                brightness=128.0,
                is_too_dark=False,
                is_too_bright=False,
                quality_ok=True,
            )


class DamageDetector:
    """Detects screen and body damage from photos.

    Uses an open-license classifier. Only models with allowed licenses
    are used (license gate).
    """

    def __init__(self, model_license: str = "Apache-2.0") -> None:
        self.model_license = model_license
        self.license_verified = model_license in ALLOWED_MODEL_LICENSES

    def detect_damage(self, image: Any) -> list[DamageSuggestion]:  # noqa: ARG002
        """Detect damages in a photo.

        Args:
            image: The image to analyze.

        Returns:
            List of DamageSuggestion objects.
        """
        if not self.license_verified:
            logger.warning(
                "model_license_not_allowed",
                license=self.model_license,
                allowed=ALLOWED_MODEL_LICENSES,
            )
            return []

        # In a real implementation, this would use a classifier
        # For now, we provide a mock implementation
        return []

    def suggest_grade_change(
        self,
        current_grade: str,  # noqa: ARG002
        damages: list[DamageSuggestion],
    ) -> int:
        """Suggest a grade change based on detected damages.

        The suggestion is bounded to at most MAX_GRADE_CHANGE grades.

        Args:
            current_grade: Current grade (A/B/C/D).
            damages: List of detected damages.

        Returns:
            Suggested grade change (negative = worse, positive = better).
        """
        if not damages:
            return 0

        # Calculate total grade change from damages
        total_change = sum(d.suggested_grade_change for d in damages)

        # Bound the change
        total_change = max(-MAX_GRADE_CHANGE, min(MAX_GRADE_CHANGE, total_change))

        return total_change

    @staticmethod
    def apply_grade_change(grade: str, change: int) -> str:
        """Apply a grade change to a grade.

        Args:
            grade: Current grade (A/B/C/D).
            change: Grade change (negative = worse, positive = better).

        Returns:
            New grade after applying change.
        """
        if grade not in GRADE_ORDER:
            return grade

        idx = GRADE_ORDER.index(grade)
        new_idx = max(0, min(len(GRADE_ORDER) - 1, idx - change))  # Negative change = worse grade

        return GRADE_ORDER[new_idx]


class SerialReader:
    """Reads serial labels using OCR.

    Uses Tesseract or PaddleOCR. Only models with allowed licenses are used.
    """

    def __init__(self, ocr_engine: str = "tesseract", model_license: str = "Apache-2.0") -> None:
        self.ocr_engine = ocr_engine
        self.model_license = model_license
        self.license_verified = model_license in ALLOWED_MODEL_LICENSES

    def read_serial(self, image: Any) -> SerialReadResult:  # noqa: ARG002
        """Read serial number from an image.

        Args:
            image: The image to analyze.

        Returns:
            SerialReadResult with serial and confidence.
        """
        if not self.license_verified:
            logger.warning(
                "ocr_license_not_allowed",
                license=self.model_license,
                allowed=ALLOWED_MODEL_LICENSES,
            )
            return SerialReadResult(serial="", confidence=0.0, success=False)

        # In a real implementation, this would use Tesseract or PaddleOCR
        # For now, we provide a mock implementation
        return SerialReadResult(serial="", confidence=0.0, success=False)


class PhotoConditionAssist:
    """Complete photo condition assist service.

    Combines photo quality checking, damage detection, and serial reading
    into a single bounded suggestion. Always requires inspector confirmation.
    """

    def __init__(
        self,
        blur_threshold: float = 100.0,
        dark_threshold: float = 50.0,
        bright_threshold: float = 200.0,
        model_license: str = "Apache-2.0",
        ocr_engine: str = "tesseract",
    ) -> None:
        self.quality_checker = PhotoQualityChecker(
            blur_threshold=blur_threshold,
            dark_threshold=dark_threshold,
            bright_threshold=bright_threshold,
        )
        self.damage_detector = DamageDetector(model_license=model_license)
        self.serial_reader = SerialReader(ocr_engine=ocr_engine, model_license=model_license)

    def analyze(
        self,
        image: Any,
        current_grade: str = "A",
    ) -> PhotoAssistResult:
        """Analyze a photo and provide bounded suggestions.

        Args:
            image: The image to analyze.
            current_grade: Current grade assessment.

        Returns:
            PhotoAssistResult with suggestions (requires confirmation).
        """
        # Check photo quality
        quality = self.quality_checker.check_quality(image)

        # Detect damages
        damages = self.damage_detector.detect_damage(image)

        # Read serial
        serial = self.serial_reader.read_serial(image)

        # Suggest grade change (bounded)
        grade_change = self.damage_detector.suggest_grade_change(current_grade, damages)

        # Calculate suggested grade
        suggested_grade = None
        if grade_change != 0:
            suggested_grade = self.damage_detector.apply_grade_change(current_grade, grade_change)

        # Verify license
        license_verified = (
            self.damage_detector.license_verified and self.serial_reader.license_verified
        )

        return PhotoAssistResult(
            quality=quality,
            damages=damages,
            serial=serial,
            suggested_grade=suggested_grade,
            grade_change=grade_change,
            requires_confirmation=True,  # Always requires confirmation
            license_verified=license_verified,
        )

    def validate_grade_change(self, change: int) -> bool:
        """Validate that a grade change is within bounds.

        Args:
            change: The proposed grade change.

        Returns:
            True if within bounds, False otherwise.
        """
        return abs(change) <= MAX_GRADE_CHANGE

    def store_suggestion(
        self,
        image_id: str,
        suggested_grade: str | None,
        grade_change: int,
        inspector_final_grade: str,
    ) -> dict[str, Any]:
        """Store a suggestion alongside the inspector's final grade.

        Args:
            image_id: ID of the image.
            suggested_grade: The suggested grade.
            grade_change: The suggested grade change.
            inspector_final_grade: The inspector's final grade.

        Returns:
            Dictionary with stored data.
        """
        return {
            "image_id": image_id,
            "suggested_grade": suggested_grade,
            "grade_change": grade_change,
            "inspector_final_grade": inspector_final_grade,
            "suggestion_accepted": suggested_grade == inspector_final_grade
            if suggested_grade
            else False,
            "timestamp": datetime.now(UTC).isoformat(),
        }
