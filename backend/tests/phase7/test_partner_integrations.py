"""
Tests for partner integrations via open APIs (Phase 7 - F7.5).
"""

import pytest
from datetime import datetime, timezone, UTC
import uuid
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock

from secondroute.integrations.adapter import (
    PartnerConfig,
    PartnerAdapter,
    IntegrationContract,
    IntegrationResult,
    PartnerIntegration,
    IntegrationStatus,
    validate_integration_contract,
    run_contract_tests,
    IntegrationResult as IntegrationResultV2,
)
from typing import Any


class SimulatedPartnerError(Exception):
    """Error raised by the mock adapter to simulate a partner failure."""


class MockPartnerAdapter(PartnerAdapter):
    """Mock partner adapter for testing."""

    def __init__(self, config: PartnerConfig):
        super().__init__(config)
        self._health = True
        self._decisions: dict[str, Any] = {}
        self._outcomes: dict[str, Any] = {}
        self._units: dict[str, Any] = {}
        self._should_fail = False
        self._fail_operation: str | None = None

    @property
    def partner_id(self) -> str:
        return self.config.partner_id

    @property
    def partner_name(self) -> str:
        return self.config.partner_name

    async def health_check(self) -> bool:
        return self._health

    async def get_decision(self, decision_id: UUID) -> IntegrationResult:
        if self._should_fail and self._fail_operation == "get_decision":
            raise SimulatedPartnerError("Simulated failure")
        decision = self._decisions.get(str(decision_id))
        if decision:
            return IntegrationResult(
                success=True,
                operation="get_decision",
                partner_id=self.partner_id,
                request_id=str(uuid.uuid4()),
                response_data=decision,
                status_code=200,
                latency_ms=10,
            )
        return IntegrationResult(
            success=False,
            operation="get_decision",
            partner_id=self.partner_id,
            request_id=str(uuid.uuid4()),
            error_message="Decision not found",
            status_code=404,
            latency_ms=10,
        )

    async def post_decision(self, decision_data: dict) -> IntegrationResult:
        if self._should_fail and self._fail_operation == "post_decision":
            raise SimulatedPartnerError("Simulated failure")
        decision_id = uuid4()
        self._decisions[str(decision_id)] = decision_data
        return IntegrationResult(
            success=True,
            operation="post_decision",
            partner_id=self.partner_id,
            request_id=str(uuid.uuid4()),
            response_data={"decision_id": str(decision_id)},
            status_code=201,
            latency_ms=10,
        )

    async def get_outcome(self, decision_id: UUID) -> IntegrationResult:
        if self._should_fail and self._fail_operation == "get_outcome":
            raise SimulatedPartnerError("Simulated failure")
        outcome = self._outcomes.get(str(decision_id))
        if outcome:
            return IntegrationResult(
                success=True,
                operation="get_outcome",
                partner_id=self.partner_id,
                request_id=str(uuid.uuid4()),
                response_data=outcome,
                status_code=200,
                latency_ms=10,
            )
        return IntegrationResult(
            success=False,
            operation="get_outcome",
            partner_id=self.partner_id,
            request_id=str(uuid.uuid4()),
            error_message="Outcome not found",
            status_code=404,
            latency_ms=10,
        )

    async def post_outcome(self, outcome_data: dict) -> IntegrationResult:
        if self._should_fail and self._fail_operation == "post_outcome":
            raise SimulatedPartnerError("Simulated failure")
        return IntegrationResult(
            success=True,
            operation="post_outcome",
            partner_id=self.partner_id,
            request_id=str(uuid.uuid4()),
            response_data=outcome_data,
            status_code=201,
            latency_ms=10,
        )

    async def get_unit(self, unit_id: UUID) -> IntegrationResult:
        if self._should_fail and self._fail_operation == "get_unit":
            raise SimulatedPartnerError("Simulated failure")
        unit = self._units.get(str(unit_id))
        if unit:
            return IntegrationResult(
                success=True,
                operation="get_unit",
                partner_id=self.partner_id,
                request_id=str(uuid.uuid4()),
                response_data=unit,
                status_code=200,
                latency_ms=10,
            )
        return IntegrationResult(
            success=False,
            operation="get_unit",
            partner_id=self.partner_id,
            request_id=str(uuid.uuid4()),
            error_message="Unit not found",
            status_code=404,
            latency_ms=10,
        )

    async def post_unit(self, unit_data: dict) -> IntegrationResult:
        if self._should_fail and self._fail_operation == "post_unit":
            raise SimulatedPartnerError("Simulated failure")
        return IntegrationResult(
            success=True,
            operation="post_unit",
            partner_id=self.partner_id,
            request_id=str(uuid.uuid4()),
            response_data=unit_data,
            status_code=201,
            latency_ms=10,
        )

    async def list_units(self, filters: dict | None = None) -> IntegrationResult:
        if self._should_fail and self._fail_operation == "list_units":
            raise SimulatedPartnerError("Simulated failure")
        return IntegrationResult(
            success=True,
            operation="list_units",
            partner_id=self.partner_id,
            request_id=str(uuid.uuid4()),
            response_data={"units": list(self._units.values())},
            status_code=200,
            latency_ms=10,
        )


class TestPartnerConfig:
    """Tests for PartnerConfig."""

    def test_valid_config(self) -> None:
        """Test creating a valid partner config."""
        config = PartnerConfig(
            partner_id="test-partner",
            partner_name="Test Partner",
            base_url="https://api.testpartner.com",
            api_key="test-api-key",
            supported_operations=["get_decision", "post_decision"],
        )
        assert config.partner_id == "test-partner"
        assert config.partner_name == "Test Partner"
        assert config.rate_limit_rps == 10
        assert config.timeout_seconds == 30
        assert config.retry_attempts == 3

    def test_config_with_custom_values(self) -> None:
        """Test config with custom rate limits and timeouts."""
        config = PartnerConfig(
            partner_id="custom-partner",
            partner_name="Custom Partner",
            base_url="https://api.custom.com",
            api_key="custom-key",
            rate_limit_rps=50,
            timeout_seconds=60,
            retry_attempts=5,
        )
        assert config.rate_limit_rps == 50
        assert config.timeout_seconds == 60
        assert config.retry_attempts == 5


class TestIntegrationContract:
    """Tests for IntegrationContract."""

    def test_basic_contract(self) -> None:
        """Test creating a basic contract."""
        contract = IntegrationContract(
            partner_id="test-partner",
            version="1.0",
            operations={
                "get_decision": {
                    "method": "GET",
                    "path": "/api/v1/decisions/{decision_id}",
                    "request": {"decision_id": "uuid"},
                    "response": {"decision_id": "uuid", "recommended_channel": "string"},
                    "status_codes": [200, 404],
                }
            },
        )
        assert contract.partner_id == "test-partner"
        assert contract.version == "1.0"
        assert "get_decision" in contract.operations

    def test_contract_with_custom_fields(self) -> None:
        """Test contract with custom headers and auth."""
        contract = IntegrationContract(
            partner_id="test-partner",
            required_headers={"X-API-Version": "1.0"},
            authentication={"type": "api_key", "header": "Authorization"},
            rate_limits={"requests_per_second": 100},
        )
        assert contract.required_headers["X-API-Version"] == "1.0"
        assert contract.authentication["type"] == "api_key"


class TestPartnerIntegration:
    """Tests for PartnerIntegration."""

    @pytest.fixture
    def adapter(self) -> PartnerAdapter:
        config = PartnerConfig(
            partner_id="test-partner",
            partner_name="Test Partner",
            base_url="https://api.test.com",
            api_key="test-key",
        )
        return MockPartnerAdapter(config)

    @pytest.fixture
    def contract(self) -> IntegrationContract:
        return IntegrationContract(
            partner_id="test-partner",
            operations={"get_decision": {}},
        )

    @pytest.fixture
    def integration(
        self, adapter: PartnerAdapter, contract: IntegrationContract
    ) -> PartnerIntegration:
        return PartnerIntegration(adapter, contract)

    @pytest.mark.asyncio
    async def test_activate_integration(
        self, integration: PartnerIntegration, adapter: Any
    ) -> None:
        """Test activating an integration."""
        adapter._health = True
        result = await integration.activate()
        assert result is True
        assert integration.status == IntegrationStatus.ACTIVE
        assert integration.last_health_check is not None

    @pytest.mark.asyncio
    async def test_activate_unhealthy_integration(
        self, integration: PartnerIntegration, adapter: Any
    ) -> None:
        """Test activating an unhealthy integration."""
        adapter._health = False
        result = await integration.activate()
        assert result is False
        assert integration.status == IntegrationStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_deactivate_integration(self, integration: PartnerIntegration) -> None:
        """Test deactivating an integration."""
        integration.status = IntegrationStatus.ACTIVE
        integration.deactivate("Testing deactivation")
        assert integration.status == IntegrationStatus.INACTIVE
        assert integration.last_error == "Testing deactivation"

    @pytest.mark.asyncio
    async def test_health_check(self, integration: PartnerIntegration, adapter: Any) -> None:
        """Test health check."""
        adapter._health = True
        healthy = await integration.health_check()
        assert healthy is True
        assert integration.last_health_check is not None

    @pytest.mark.asyncio
    async def test_execute_operation_success(
        self, integration: PartnerIntegration, adapter: Any
    ) -> None:
        """Test successful operation execution."""
        test_decision_id = uuid4()
        adapter._decisions[str(test_decision_id)] = {
            "channel": "RESELL_OPEN_BOX",
            "confidence": 0.9,
        }
        result = await integration.execute_operation("get_decision", decision_id=test_decision_id)
        assert result.success is True
        assert result.operation == "get_decision"
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_operation_not_found(self, integration: PartnerIntegration) -> None:
        """Test executing non-existent operation."""
        result = await integration.execute_operation("nonexistent_operation")
        assert result.success is False
        assert result.error_message is not None
        assert "not supported" in result.error_message.lower()
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_execute_operation_failure(
        self, integration: PartnerIntegration, adapter: Any
    ) -> None:
        """Test operation failure handling."""
        adapter._should_fail = True
        adapter._fail_operation = "get_decision"
        result = await integration.execute_operation("get_decision", decision_id=uuid4())
        assert result.success is False
        assert result.error_message == "Simulated failure"
        assert result.status_code == 500


class TestValidateIntegrationContract:
    """Tests for validate_integration_contract."""

    def test_valid_adapter(self) -> None:
        """Test validation passes for valid adapter."""
        adapter = MockPartnerAdapter(
            PartnerConfig(
                partner_id="test-partner",
                partner_name="Test Partner",
                base_url="https://api.test.com",
                api_key="test-key",
            )
        )
        contract = IntegrationContract(
            partner_id="test-partner",
            operations={"get_decision": {}},
        )
        errors = validate_integration_contract(adapter, contract)
        assert len(errors) == 0

    def test_missing_operation(self) -> None:
        """Test validation fails for missing operation."""
        adapter = MockPartnerAdapter(
            PartnerConfig(
                partner_id="test-partner",
                partner_name="Test Partner",
                base_url="https://api.test.com",
                api_key="test-key",
            )
        )
        contract = IntegrationContract(
            partner_id="test-partner",
            operations={"get_decision": {}, "post_decision": {}},
        )
        # For testing: force the adapter to miss the operation
        adapter._should_fail = True
        adapter._fail_operation = "post_decision"
        adapter.post_decision = None  # type: ignore[method-assign, assignment]

        errors = validate_integration_contract(adapter, contract)
        assert len(errors) > 0
        assert any("post_decision" in e for e in errors)

    def test_missing_required_method(self) -> None:
        """Test validation fails for missing required method."""
        adapter = MockPartnerAdapter(
            PartnerConfig(
                partner_id="incomplete",
                partner_name="Incomplete",
                base_url="https://api.test.com",
                api_key="test-key",
            )
        )
        contract = IntegrationContract(
            partner_id="incomplete",
            operations={"health_check": {}, "get_decision": {}},
        )
        # Simulate a missing required method (e.g. list_units not implemented)
        adapter.list_units = None  # type: ignore[method-assign, assignment]

        errors = validate_integration_contract(adapter, contract)
        assert len(errors) > 0
        assert any("list_units" in e for e in errors)


class TestContractTests:
    """Tests for run_contract_tests."""

    @pytest.mark.asyncio
    async def test_contract_tests_pass(self) -> None:
        """Test that contract tests pass for a valid adapter."""
        adapter = MockPartnerAdapter(
            PartnerConfig(
                partner_id="test-partner",
                partner_name="Test Partner",
                base_url="https://api.test.com",
                api_key="test-key",
            )
        )

        contract = IntegrationContract(
            partner_id="test-partner",
            operations={
                "get_decision": {},
                "post_decision": {},
            },
        )

        # Seed a decision so get_decision returns 200
        known_decision_id = uuid4()
        adapter._decisions[str(known_decision_id)] = {"channel": "RESELL_OPEN_BOX"}

        test_cases = [
            {
                "operation": "get_decision",
                "input": {"decision_id": known_decision_id},
                "expected": {"status_code": 200},
            },
            {
                "operation": "post_decision",
                "input": {"decision_data": {"channel": "RESELL_OPEN_BOX"}},
                "expected": {"status_code": 201},
            },
        ]

        results = await run_contract_tests(adapter, contract, test_cases)

        assert results["passed"] == 2
        assert results["failed"] == 0
        assert len(results["details"]) == 2

    @pytest.mark.asyncio
    async def test_contract_tests_fail(self) -> None:
        """Test that contract tests catch failures."""
        adapter = MockPartnerAdapter(
            PartnerConfig(
                partner_id="test-partner",
                partner_name="Test Partner",
                base_url="https://api.test.com",
                api_key="test-key",
            )
        )
        adapter._should_fail = True
        adapter._fail_operation = "get_decision"

        contract = IntegrationContract(
            partner_id="test-partner",
            operations={"get_decision": {}},
        )

        test_cases = [
            {
                "operation": "get_decision",
                "input": {"decision_id": uuid4()},
                "expected": {"status_code": 200},
            },
        ]

        results = await run_contract_tests(adapter, contract, test_cases)

        assert results["passed"] == 0
        assert results["failed"] == 1
        assert len(results["details"]) == 1
        assert results["details"][0]["status"] == "failed"
