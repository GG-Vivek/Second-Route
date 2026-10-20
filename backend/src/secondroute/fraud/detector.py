"""
Fraud and wardrobing signal detection (Phase 7 - F7.3).

Flags for serial mismatch, component swap, and activation lock mismatch.
Flags go to a review queue. They never auto-reject a return.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, UTC
from enum import Enum, StrEnum
from typing import Any, Optional, Sequence
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, ConfigDict

logger = structlog.get_logger(__name__)


class FraudFlagType(StrEnum):
    """Types of fraud flags."""

    SERIAL_MISMATCH = "serial_mismatch"
    COMPONENT_SWAP = "component_swap"
    ACTIVATION_LOCK_MISMATCH = "activation_lock_mismatch"
    WARDROBING = "wardrobing"
    SUSPICIOUS_PATTERN = "suspicious_pattern"


@dataclass
class FraudFlag:
    """A fraud flag for a unit.

    Attributes:
        flag_type: Type of fraud flag.
        unit_id: Unit identifier.
        severity: Severity level (low, medium, high).
        description: Human-readable description.
        evidence: Evidence supporting the flag.
        created_at: Timestamp of the flag.
        reviewed: Whether the flag has been reviewed.
        reviewed_by: Who reviewed the flag.
        review_outcome: Outcome of the review (confirmed, dismissed, escalated).
    """

    flag_type: FraudFlagType
    unit_id: UUID
    severity: str = "medium"
    description: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    reviewed: bool = False
    reviewed_by: str | None = None
    review_outcome: str | None = None


class FraudDetector:
    """Detects fraud and wardrobing signals.

    Flags are sent to a review queue. They never auto-reject a return.
    """

    def __init__(
        self,
        serial_mismatch_threshold: float = 0.8,
        component_swap_threshold: float = 0.7,
    ) -> None:
        self.serial_mismatch_threshold = serial_mismatch_threshold
        self.component_swap_threshold = component_swap_threshold

    def check_serial_mismatch(
        self,
        unit_serial: str | None,
        sku_serial_prefixes: list[str],
        unit_sku_family: str,
    ) -> FraudFlag | None:
        """Check for serial number mismatch.

        A serial mismatch occurs when the serial number doesn't match
        the expected prefix for the SKU.

        Args:
            unit_serial: The unit's serial number.
            sku_serial_prefixes: Expected serial prefixes for the SKU.
            unit_sku_family: The SKU family.

        Returns:
            FraudFlag if mismatch detected, None otherwise.
        """
        if not unit_serial:
            return None

        # Check if serial matches any expected prefix
        matches = any(unit_serial.startswith(prefix) for prefix in sku_serial_prefixes)

        if not matches and sku_serial_prefixes:
            return FraudFlag(
                flag_type=FraudFlagType.SERIAL_MISMATCH,
                unit_id=uuid4(),  # Placeholder, should be set by caller
                severity="high",
                description=f"Serial '{unit_serial}' does not match expected prefixes for {unit_sku_family}",
                evidence={
                    "serial": unit_serial,
                    "expected_prefixes": sku_serial_prefixes,
                    "sku_family": unit_sku_family,
                },
            )

        return None

    def check_component_swap(
        self,
        serial: str | None,
        components: list[dict[str, Any]],
        expected_components: list[dict[str, Any]],
    ) -> FraudFlag | None:
        """Check for component swap.

        A component swap occurs when the components in the unit don't
        match what's expected for the serial number.

        Args:
            serial: The unit's serial number.
            components: Actual components found.
            expected_components: Expected components for the serial.

        Returns:
            FraudFlag if swap detected, None otherwise.
        """
        if not components or not expected_components:
            return None

        # Check for mismatched components
        mismatched = []
        for actual in components:
            component_type = actual.get("type")
            expected = next(
                (e for e in expected_components if e.get("type") == component_type),
                None,
            )
            if expected:
                if actual.get("serial") != expected.get("serial"):
                    mismatched.append(
                        {
                            "type": component_type,
                            "actual_serial": actual.get("serial"),
                            "expected_serial": expected.get("serial"),
                        }
                    )

        if mismatched:
            return FraudFlag(
                flag_type=FraudFlagType.COMPONENT_SWAP,
                unit_id=uuid4(),  # Placeholder
                severity="high",
                description=f"Component serial mismatch detected: {len(mismatched)} components",
                evidence={
                    "serial": serial,
                    "mismatched_components": mismatched,
                },
            )

        return None

    def check_activation_lock_mismatch(
        self,
        serial: str | None,
        activation_lock_status: str,
        expected_lock_status: str,
    ) -> FraudFlag | None:
        """Check for activation lock mismatch.

        An activation lock mismatch occurs when the activation lock status
        doesn't match what's expected for the unit.

        Args:
            serial: The unit's serial number.
            activation_lock_status: Actual activation lock status.
            expected_lock_status: Expected activation lock status.

        Returns:
            FraudFlag if mismatch detected, None otherwise.
        """
        if activation_lock_status != expected_lock_status:
            return FraudFlag(
                flag_type=FraudFlagType.ACTIVATION_LOCK_MISMATCH,
                unit_id=uuid4(),  # Placeholder
                severity="medium",
                description=f"Activation lock mismatch: expected '{expected_lock_status}', found '{activation_lock_status}'",
                evidence={
                    "serial": serial,
                    "expected": expected_lock_status,
                    "actual": activation_lock_status,
                },
            )

        return None

    def check_wardrobing(
        self,
        unit_serial: str | None,
        return_count: int,
        return_window_days: int = 30,
        threshold: int = 3,
    ) -> FraudFlag | None:
        """Check for wardrobing (returning used items as new).

        Wardrobing is when a customer buys an item, uses it, and returns it
        as if it were new.

        Args:
            unit_serial: The unit's serial number.
            return_count: Number of returns for this serial in the window.
            return_window_days: Time window for returns.
            threshold: Maximum returns before flagging.

        Returns:
            FraudFlag if wardrobing suspected, None otherwise.
        """
        if return_count >= threshold:
            return FraudFlag(
                flag_type=FraudFlagType.WARDROBING,
                unit_id=uuid4(),  # Placeholder
                severity="high",
                description=f"Suspected wardrobing: {return_count} returns in {return_window_days} days",
                evidence={
                    "serial": unit_serial,
                    "return_count": return_count,
                    "return_window_days": return_window_days,
                    "threshold": threshold,
                },
            )

        return None

    def check_all(  # noqa: PLR0913, PLR0917
        self,
        unit_serial: str | None,
        sku_serial_prefixes: list[str],
        unit_sku_family: str,
        components: list[dict[str, Any]] | None = None,
        expected_components: list[dict[str, Any]] | None = None,
        activation_lock_status: str = "unknown",
        expected_lock_status: str = "none",
        return_count: int = 0,
    ) -> list[FraudFlag]:
        """Run all fraud checks on a unit.

        Args:
            unit_serial: The unit's serial number.
            sku_serial_prefixes: Expected serial prefixes for the SKU.
            unit_sku_family: The SKU family.
            components: Actual components found.
            expected_components: Expected components for the serial.
            activation_lock_status: Actual activation lock status.
            expected_lock_status: Expected activation lock status.
            return_count: Number of returns for this serial.

        Returns:
            List of FraudFlag objects (empty if no issues).
        """
        flags = []

        # Serial mismatch check
        serial_flag = self.check_serial_mismatch(unit_serial, sku_serial_prefixes, unit_sku_family)
        if serial_flag:
            flags.append(serial_flag)

        # Component swap check
        if components and expected_components:
            component_flag = self.check_component_swap(unit_serial, components, expected_components)
            if component_flag:
                flags.append(component_flag)

        # Activation lock mismatch check
        lock_flag = self.check_activation_lock_mismatch(
            unit_serial, activation_lock_status, expected_lock_status
        )
        if lock_flag:
            flags.append(lock_flag)

        # Wardrobing check
        wardrobing_flag = self.check_wardrobing(unit_serial, return_count)
        if wardrobing_flag:
            flags.append(wardrobing_flag)

        return flags


class FraudReviewQueue:
    """Review queue for fraud flags.

    Flags are sent here for human review. They never auto-reject a return.
    """

    def __init__(self) -> None:
        self._queue: list[FraudFlag] = []

    def add_flag(self, flag: FraudFlag) -> None:
        """Add a flag to the review queue."""
        self._queue.append(flag)
        logger.info(
            "fraud_flag_queued",
            flag_type=flag.flag_type.value,
            severity=flag.severity,
            unit_id=str(flag.unit_id),
        )

    def add_flags(self, flags: list[FraudFlag]) -> None:
        """Add multiple flags to the review queue."""
        for flag in flags:
            self.add_flag(flag)

    def get_pending(self) -> list[FraudFlag]:
        """Get all pending (unreviewed) flags."""
        return [f for f in self._queue if not f.reviewed]

    def get_all(self) -> list[FraudFlag]:
        """Get all flags."""
        return list(self._queue)

    def review_flag(
        self,
        flag: FraudFlag,
        reviewer: str,
        outcome: str,
    ) -> None:
        """Review a flag.

        Args:
            flag: The flag to review.
            reviewer: Who is reviewing.
            outcome: Review outcome (confirmed, dismissed, escalated).
        """
        flag.reviewed = True
        flag.reviewed_by = reviewer
        flag.review_outcome = outcome
        logger.info(
            "fraud_flag_reviewed",
            flag_type=flag.flag_type.value,
            reviewer=reviewer,
            outcome=outcome,
        )

    def get_by_type(self, flag_type: FraudFlagType) -> list[FraudFlag]:
        """Get flags by type."""
        return [f for f in self._queue if f.flag_type == flag_type]

    def get_by_severity(self, severity: str) -> list[FraudFlag]:
        """Get flags by severity."""
        return [f for f in self._queue if f.severity == severity]

    def clear(self) -> None:
        """Clear the review queue."""
        self._queue.clear()
