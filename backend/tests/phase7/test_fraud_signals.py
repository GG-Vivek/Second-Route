"""
Tests for fraud and wardrobing signals (Phase 7 - F7.3).
"""

import pytest
from uuid import uuid4

from secondroute.fraud.detector import (
    FraudDetector,
    FraudFlag,
    FraudFlagType,
    FraudReviewQueue,
)


class TestSerialMismatch:
    """Tests for serial mismatch detection."""

    def test_serial_mismatch_triggers(self) -> None:
        """Test that a serial mismatch triggers a flag."""
        detector = FraudDetector()
        flag = detector.check_serial_mismatch(
            unit_serial="UNKNOWN123",
            sku_serial_prefixes=["C02", "C03"],
            unit_sku_family="MacBook Pro",
        )

        assert flag is not None
        assert flag.flag_type == FraudFlagType.SERIAL_MISMATCH
        assert flag.severity == "high"
        assert "does not match" in flag.description

    def test_serial_match_no_flag(self) -> None:
        """Test that a matching serial does not trigger a flag."""
        detector = FraudDetector()
        flag = detector.check_serial_mismatch(
            unit_serial="C02XYZ123",
            sku_serial_prefixes=["C02", "C03"],
            unit_sku_family="MacBook Pro",
        )

        assert flag is None

    def test_no_serial_no_flag(self) -> None:
        """Test that no serial doesn't trigger a flag."""
        detector = FraudDetector()
        flag = detector.check_serial_mismatch(
            unit_serial=None,
            sku_serial_prefixes=["C02", "C03"],
            unit_sku_family="MacBook Pro",
        )

        assert flag is None

    def test_no_expected_prefixes_no_flag(self) -> None:
        """Test that no expected prefixes doesn't trigger a flag."""
        detector = FraudDetector()
        flag = detector.check_serial_mismatch(
            unit_serial="UNKNOWN123",
            sku_serial_prefixes=[],
            unit_sku_family="MacBook Pro",
        )

        assert flag is None


class TestComponentSwap:
    """Tests for component swap detection."""

    def test_component_swap_triggers(self) -> None:
        """Test that a component swap triggers a flag."""
        detector = FraudDetector()
        flag = detector.check_component_swap(
            serial="C02XYZ123",
            components=[
                {"type": "display", "serial": "DISP-NEW"},
                {"type": "battery", "serial": "BATT-NEW"},
            ],
            expected_components=[
                {"type": "display", "serial": "DISP-ORIG"},
                {"type": "battery", "serial": "BATT-ORIG"},
            ],
        )

        assert flag is not None
        assert flag.flag_type == FraudFlagType.COMPONENT_SWAP
        assert flag.severity == "high"
        assert "mismatch" in flag.description

    def test_no_swap_no_flag(self) -> None:
        """Test that matching components don't trigger a flag."""
        detector = FraudDetector()
        flag = detector.check_component_swap(
            serial="C02XYZ123",
            components=[
                {"type": "display", "serial": "DISP-ORIG"},
                {"type": "battery", "serial": "BATT-ORIG"},
            ],
            expected_components=[
                {"type": "display", "serial": "DISP-ORIG"},
                {"type": "battery", "serial": "BATT-ORIG"},
            ],
        )

        assert flag is None

    def test_empty_components_no_flag(self) -> None:
        """Test that empty components don't trigger a flag."""
        detector = FraudDetector()
        flag = detector.check_component_swap(
            serial="C02XYZ123",
            components=[],
            expected_components=[{"type": "display", "serial": "DISP-ORIG"}],
        )

        assert flag is None


class TestActivationLockMismatch:
    """Tests for activation lock mismatch detection."""

    def test_lock_mismatch_triggers(self) -> None:
        """Test that an activation lock mismatch triggers a flag."""
        detector = FraudDetector()
        flag = detector.check_activation_lock_mismatch(
            serial="C02XYZ123",
            activation_lock_status="present",
            expected_lock_status="none",
        )

        assert flag is not None
        assert flag.flag_type == FraudFlagType.ACTIVATION_LOCK_MISMATCH
        assert flag.severity == "medium"
        assert "mismatch" in flag.description

    def test_lock_match_no_flag(self) -> None:
        """Test that matching lock status doesn't trigger a flag."""
        detector = FraudDetector()
        flag = detector.check_activation_lock_mismatch(
            serial="C02XYZ123",
            activation_lock_status="none",
            expected_lock_status="none",
        )

        assert flag is None


class TestWardrobing:
    """Tests for wardrobing detection."""

    def test_wardrobing_triggers(self) -> None:
        """Test that excessive returns trigger a wardrobing flag."""
        detector = FraudDetector()
        flag = detector.check_wardrobing(
            unit_serial="C02XYZ123",
            return_count=5,
            return_window_days=30,
            threshold=3,
        )

        assert flag is not None
        assert flag.flag_type == FraudFlagType.WARDROBING
        assert flag.severity == "high"
        assert "wardrobing" in flag.description.lower()

    def test_no_wardrobing_below_threshold(self) -> None:
        """Test that returns below threshold don't trigger a flag."""
        detector = FraudDetector()
        flag = detector.check_wardrobing(
            unit_serial="C02XYZ123",
            return_count=2,
            return_window_days=30,
            threshold=3,
        )

        assert flag is None

    def test_wardrobing_at_threshold(self) -> None:
        """Test that returns at threshold trigger a flag."""
        detector = FraudDetector()
        flag = detector.check_wardrobing(
            unit_serial="C02XYZ123",
            return_count=3,
            return_window_days=30,
            threshold=3,
        )

        assert flag is not None
        assert flag.flag_type == FraudFlagType.WARDROBING


class TestCheckAll:
    """Tests for running all fraud checks."""

    def test_check_all_no_flags(self) -> None:
        """Test that clean unit produces no flags."""
        detector = FraudDetector()
        flags = detector.check_all(
            unit_serial="C02XYZ123",
            sku_serial_prefixes=["C02"],
            unit_sku_family="MacBook Pro",
            components=[
                {"type": "display", "serial": "DISP-ORIG"},
            ],
            expected_components=[
                {"type": "display", "serial": "DISP-ORIG"},
            ],
            activation_lock_status="none",
            expected_lock_status="none",
            return_count=1,
        )

        assert len(flags) == 0

    def test_check_all_multiple_flags(self) -> None:
        """Test that multiple issues produce multiple flags."""
        detector = FraudDetector()
        flags = detector.check_all(
            unit_serial="UNKNOWN123",
            sku_serial_prefixes=["C02"],
            unit_sku_family="MacBook Pro",
            components=[
                {"type": "display", "serial": "DISP-NEW"},
            ],
            expected_components=[
                {"type": "display", "serial": "DISP-ORIG"},
            ],
            activation_lock_status="present",
            expected_lock_status="none",
            return_count=5,
        )

        assert len(flags) == 4  # serial mismatch, component swap, lock mismatch, wardrobing
        flag_types = [f.flag_type for f in flags]
        assert FraudFlagType.SERIAL_MISMATCH in flag_types
        assert FraudFlagType.COMPONENT_SWAP in flag_types
        assert FraudFlagType.ACTIVATION_LOCK_MISMATCH in flag_types
        assert FraudFlagType.WARDROBING in flag_types

    def test_check_all_never_auto_reject(self) -> None:
        """Test that flags never auto-reject a return."""
        detector = FraudDetector()
        flags = detector.check_all(
            unit_serial="UNKNOWN123",
            sku_serial_prefixes=["C02"],
            unit_sku_family="MacBook Pro",
            return_count=10,
        )

        # Flags are produced but they don't have a "reject" action
        for flag in flags:
            assert flag.reviewed is False
            assert flag.review_outcome is None


class TestFraudReviewQueue:
    """Tests for the fraud review queue."""

    def test_add_flag(self) -> None:
        """Test adding a flag to the queue."""
        queue = FraudReviewQueue()
        flag = FraudFlag(
            flag_type=FraudFlagType.SERIAL_MISMATCH,
            unit_id=uuid4(),
            severity="high",
            description="Test flag",
        )

        queue.add_flag(flag)
        assert len(queue.get_all()) == 1
        assert len(queue.get_pending()) == 1

    def test_add_multiple_flags(self) -> None:
        """Test adding multiple flags."""
        queue = FraudReviewQueue()
        flags = [
            FraudFlag(flag_type=FraudFlagType.SERIAL_MISMATCH, unit_id=uuid4()),
            FraudFlag(flag_type=FraudFlagType.WARDROBING, unit_id=uuid4()),
        ]

        queue.add_flags(flags)
        assert len(queue.get_all()) == 2

    def test_review_flag(self) -> None:
        """Test reviewing a flag."""
        queue = FraudReviewQueue()
        flag = FraudFlag(flag_type=FraudFlagType.SERIAL_MISMATCH, unit_id=uuid4())
        queue.add_flag(flag)

        queue.review_flag(flag, reviewer="admin@example.com", outcome="confirmed")

        assert flag.reviewed is True
        assert flag.reviewed_by == "admin@example.com"
        assert flag.review_outcome == "confirmed"
        assert len(queue.get_pending()) == 0

    def test_get_by_type(self) -> None:
        """Test filtering by flag type."""
        queue = FraudReviewQueue()
        queue.add_flag(FraudFlag(flag_type=FraudFlagType.SERIAL_MISMATCH, unit_id=uuid4()))
        queue.add_flag(FraudFlag(flag_type=FraudFlagType.WARDROBING, unit_id=uuid4()))
        queue.add_flag(FraudFlag(flag_type=FraudFlagType.SERIAL_MISMATCH, unit_id=uuid4()))

        serial_flags = queue.get_by_type(FraudFlagType.SERIAL_MISMATCH)
        assert len(serial_flags) == 2

    def test_get_by_severity(self) -> None:
        """Test filtering by severity."""
        queue = FraudReviewQueue()
        queue.add_flag(
            FraudFlag(flag_type=FraudFlagType.SERIAL_MISMATCH, unit_id=uuid4(), severity="high")
        )
        queue.add_flag(
            FraudFlag(
                flag_type=FraudFlagType.ACTIVATION_LOCK_MISMATCH, unit_id=uuid4(), severity="medium"
            )
        )

        high_flags = queue.get_by_severity("high")
        assert len(high_flags) == 1

    def test_clear_queue(self) -> None:
        """Test clearing the queue."""
        queue = FraudReviewQueue()
        queue.add_flag(FraudFlag(flag_type=FraudFlagType.SERIAL_MISMATCH, unit_id=uuid4()))
        assert len(queue.get_all()) == 1

        queue.clear()
        assert len(queue.get_all()) == 0
