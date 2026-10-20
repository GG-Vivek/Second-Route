"""
Partner integration adapter for Phase 7 (F7.5).

Implements the adapter pattern for partner integrations with contract tests
and written agreements.
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, UTC
from typing import Any, Optional, Sequence
from uuid import UUID

import structlog
from pydantic import BaseModel, ConfigDict, Field

logger = structlog.get_logger(__name__)


class IntegrationStatus(str):
    """Status of a partner integration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    DEPRECATED = "deprecated"


class IntegrationOperation(str):
    """Types of operations supported by the integration."""

    GET_DECISION = "get_decision"
    POST_DECISION = "post_decision"
    GET_OUTCOME = "get_outcome"
    POST_OUTCOME = "post_outcome"
    GET_UNIT = "get_unit"
    POST_UNIT = "post_unit"
    LIST_UNITS = "list_units"
    GET_DECISION_CARD = "get_decision_card"


@dataclass
class PartnerConfig:
    """Configuration for a partner integration.

    Attributes:
        partner_id: Unique identifier for the partner.
        partner_name: Human-readable name of the partner.
        base_url: Base URL for the partner's API.
        api_key: API key for authentication.
        webhook_secret: Secret for webhook signature verification.
        supported_operations: List of operations this partner supports.
        rate_limit_rps: Rate limit in requests per second.
        timeout_seconds: Request timeout in seconds.
        retry_attempts: Number of retry attempts for failed requests.
    """

    partner_id: str
    partner_name: str
    base_url: str
    api_key: str
    webhook_secret: str = ""
    supported_operations: list[str] = field(default_factory=list)
    rate_limit_rps: int = 10
    timeout_seconds: int = 30
    retry_attempts: int = 3


class IntegrationContract(BaseModel):
    """Contract defining the expected API interface for a partner integration.

    This serves as a contract test specification that both the partner
    and SecondRoute must adhere to.
    """

    model_config = ConfigDict(frozen=True)

    partner_id: str
    version: str = "1.0"
    operations: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Example:
    # {
    #     "get_decision": {
    #         "method": "GET",
    #         "path": "/api/v1/decisions/{decision_id}",
    #         "request": {"decision_id": "uuid"},
    #         "response": {"decision_id": "uuid", "recommended_channel": "string", "confidence": "float"},
    #         "status_codes": [200, 404],
    #     }
    # }

    required_headers: dict[str, str] = field(default_factory=dict)
    authentication: dict[str, Any] = field(default_factory=dict)
    rate_limits: dict[str, int] = field(default_factory=dict)


class IntegrationResult(BaseModel):
    """Result of an integration operation."""

    model_config = ConfigDict(frozen=True)

    success: bool
    operation: str
    partner_id: str
    request_id: str
    response_data: dict[str, Any] | None = None
    error_message: str | None = None
    status_code: int
    latency_ms: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class IntegrationResultV2(BaseModel):
    """Extended result with additional metadata."""

    model_config = ConfigDict(frozen=True)

    success: bool
    operation: str
    partner_id: str
    request_id: str
    response_data: dict[str, Any] | None = None
    error_message: str | None = None
    status_code: int
    latency_ms: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    contract_version: str = "1.0"
    retry_count: int = 0


class PartnerAdapter(ABC):
    """Abstract base class for partner adapters.

    Each partner integration must implement this interface.
    """

    def __init__(self, config: PartnerConfig) -> None:
        self.config = config
        self.contract = IntegrationContract(partner_id=config.partner_id)

    @property
    @abstractmethod
    def partner_id(self) -> str:
        """Unique identifier for this partner."""
        pass

    @property
    @abstractmethod
    def partner_name(self) -> str:
        """Human-readable name of the partner."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the partner integration is healthy."""
        pass

    @abstractmethod
    async def get_decision(self, decision_id: UUID) -> IntegrationResult:
        """Get a decision by ID."""
        pass

    @abstractmethod
    async def post_decision(self, decision_data: dict[str, Any]) -> IntegrationResult:
        """Submit a new decision to the partner."""
        pass

    @abstractmethod
    async def get_outcome(self, decision_id: UUID) -> IntegrationResult:
        """Get the outcome for a decision."""
        pass

    @abstractmethod
    async def post_outcome(self, outcome_data: dict[str, Any]) -> IntegrationResult:
        """Post an outcome to the partner."""
        pass

    @abstractmethod
    async def get_unit(self, unit_id: UUID) -> IntegrationResult:
        """Get unit information from the partner."""
        pass

    @abstractmethod
    async def post_unit(self, unit_data: dict[str, Any]) -> IntegrationResult:
        """Submit a unit to the partner."""
        pass

    @abstractmethod
    async def list_units(self, filters: dict[str, Any] | None = None) -> IntegrationResult:
        """List units from the partner."""
        pass

    def validate_contract(self, contract: IntegrationContract) -> bool:
        """Validate that this adapter conforms to the contract."""
        # Basic validation - can be overridden by specific adapters
        del contract  # unused in the default implementation
        return True


class PartnerIntegration:
    """Manages a partner integration lifecycle.

    Handles configuration, health checks, and operation routing.
    """

    def __init__(self, adapter: PartnerAdapter, contract: IntegrationContract) -> None:
        self.adapter = adapter
        self.contract = contract
        self.status = IntegrationStatus.PENDING
        self.created_at = datetime.now(UTC)
        self.last_health_check: datetime | None = None
        self.last_error: str | None = None

    async def activate(self) -> bool:
        """Activate the integration after health check."""
        healthy = await self.adapter.health_check()
        if healthy:
            self.status = IntegrationStatus.ACTIVE
            self.last_health_check = datetime.now(UTC)
            logger.info("integration_activated", partner=self.adapter.partner_id)
            return True
        else:
            self.status = IntegrationStatus.INACTIVE
            logger.warning("integration_activation_failed", partner=self.adapter.partner_id)
            return False

    def deactivate(self, reason: str = "") -> None:
        """Deactivate the integration."""
        self.status = IntegrationStatus.INACTIVE
        self.last_error = reason
        logger.info("integration_deactivated", partner=self.adapter.partner_id, reason=reason)

    async def health_check(self) -> bool:
        """Perform a health check on the partner."""
        healthy = await self.adapter.health_check()
        if healthy:
            self.last_health_check = datetime.now(UTC)
            self.status = IntegrationStatus.ACTIVE
        else:
            self.status = IntegrationStatus.INACTIVE
        return healthy

    async def execute_operation(
        self,
        operation: str,
        **kwargs: Any,
    ) -> IntegrationResult:
        """Execute an operation on the partner adapter."""
        method = getattr(self.adapter, operation, None)
        if not method:
            return IntegrationResult(
                success=False,
                operation=operation,
                partner_id=self.adapter.partner_id,
                request_id=str(uuid.uuid4()),
                error_message=f"Operation {operation} not supported",
                status_code=400,
                latency_ms=0,
            )

        start = datetime.now(UTC)
        try:
            result = await method(**kwargs)
            latency = int((datetime.now(UTC) - start).total_seconds() * 1000)
            if isinstance(result, IntegrationResult):
                return IntegrationResult(
                    success=result.success,
                    operation=operation,
                    partner_id=self.adapter.partner_id,
                    request_id=str(uuid.uuid4()),
                    response_data=result.response_data,
                    error_message=result.error_message,
                    status_code=result.status_code,
                    latency_ms=latency,
                )
            return IntegrationResult(
                success=True,
                operation=operation,
                partner_id=self.adapter.partner_id,
                request_id=str(uuid.uuid4()),
                response_data=result,
                status_code=200,
                latency_ms=latency,
            )
        except Exception as e:
            latency = int((datetime.now(UTC) - start).total_seconds() * 1000)
            logger.exception(
                "integration_operation_failed",
                partner=self.adapter.partner_id,
                operation=operation,
                error=str(e),
            )
            return IntegrationResult(
                success=False,
                operation=operation,
                partner_id=self.adapter.partner_id,
                request_id=str(uuid.uuid4()),
                error_message=str(e),
                status_code=500,
                latency_ms=latency,
            )


def validate_integration_contract(
    adapter: PartnerAdapter,
    contract: IntegrationContract,
) -> list[str]:
    """Validate that an adapter conforms to its contract.

    Returns:
        List of validation errors (empty if valid).
    """
    errors = []

    # Check that all required operations are implemented
    for op_name, _op_spec in contract.operations.items():
        if not callable(getattr(adapter, op_name, None)):
            errors.append(f"Missing required operation: {op_name}")

    # Check that adapter has all required methods
    required_methods = [
        "health_check",
        "get_decision",
        "post_decision",
        "get_outcome",
        "post_outcome",
        "get_unit",
        "post_unit",
        "list_units",
    ]
    for method in required_methods:
        if not callable(getattr(adapter, method, None)):
            errors.append(f"Missing required method: {method}")

    return errors


async def run_contract_tests(
    adapter: PartnerAdapter,
    contract: IntegrationContract,
    test_cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """Run contract tests against an adapter.

    Args:
        adapter: The partner adapter to test.
        contract: The contract to test against.
        test_cases: List of test cases with input/expected output.

    Returns:
        Dictionary with test results.
    """
    results: dict[str, Any] = {
        "passed": 0,
        "failed": 0,
        "errors": [],
        "details": [],
    }

    for test_case in test_cases:
        operation = str(test_case.get("operation"))
        input_data = test_case.get("input", {})
        expected = test_case.get("expected", {})

        try:
            method = getattr(adapter, operation)
            result = await method(**input_data)

            # Validate response
            if "status_code" in expected:
                if isinstance(result, IntegrationResult):
                    assert result.status_code == expected["status_code"]
                elif hasattr(result, "status_code"):
                    assert result.status_code == expected["status_code"]

            results["passed"] += 1
            results["details"].append(
                {
                    "operation": operation,
                    "status": "passed",
                }
            )

        except Exception as e:
            results["failed"] += 1
            results["errors"].append(str(e))
            results["details"].append(
                {
                    "operation": operation,
                    "status": "failed",
                    "error": str(e),
                }
            )

    return results
