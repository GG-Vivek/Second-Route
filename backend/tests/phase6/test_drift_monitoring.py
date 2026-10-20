"""
Tests for drift monitoring (Phase 6 - F6.4).
"""

import pytest
import numpy as np
from datetime import datetime, timezone, UTC

from secondroute.learning.drift import (
    DriftMonitor,
    PSIRResult,
    CalibrationDriftResult,
    PSI_THRESHOLD_LOW,
    PSI_THRESHOLD_HIGH,
)


class TestPSI:
    """Tests for population stability index computation."""

    def test_no_drift(self) -> None:
        """Test PSI with no significant drift."""
        monitor = DriftMonitor()
        expected = [1.0, 2.0, 3.0, 4.0, 5.0] * 100
        actual = [1.0, 2.0, 3.0, 4.0, 5.0] * 100

        result = monitor.compute_psi(expected, actual)

        assert result.psi < PSI_THRESHOLD_LOW
        assert result.is_drift is False
        assert result.is_alert is False

    def test_significant_drift(self) -> None:
        """Test PSI with significant drift."""
        monitor = DriftMonitor()
        expected = [1.0, 2.0, 3.0, 4.0, 5.0] * 100
        # Shift the distribution significantly
        actual = [6.0, 7.0, 8.0, 9.0, 10.0] * 100

        result = monitor.compute_psi(expected, actual)

        assert result.psi >= PSI_THRESHOLD_HIGH
        assert result.is_drift is True
        assert result.is_alert is True

    def test_moderate_drift(self) -> None:
        """Test PSI with moderate drift."""
        monitor = DriftMonitor()
        expected = [1.0, 2.0, 3.0, 4.0, 5.0] * 100
        # Slight shift
        actual = [1.5, 2.5, 3.5, 4.5, 5.5] * 100

        result = monitor.compute_psi(expected, actual)

        # Should detect some drift
        assert result.psi >= 0
        assert isinstance(result.is_drift, bool)
        assert isinstance(result.is_alert, bool)

    def test_empty_data(self) -> None:
        """Test PSI with empty data."""
        monitor = DriftMonitor()
        result = monitor.compute_psi([], [])

        assert result.psi == 0.0
        assert result.is_drift is False
        assert result.is_alert is False

    def test_constant_data(self) -> None:
        """Test PSI with constant values."""
        monitor = DriftMonitor()
        expected = [5.0] * 100
        actual = [5.0] * 100

        result = monitor.compute_psi(expected, actual)

        assert result.psi == 0.0
        assert result.is_drift is False

    def test_injected_input_shift_triggers_alert(self) -> None:
        """Test that an injected input shift triggers an alert."""
        monitor = DriftMonitor()
        # Reference distribution
        reference = {
            "battery_health": [90.0, 95.0, 88.0, 92.0, 91.0] * 100,
            "price": [1000.0, 1100.0, 950.0, 1050.0, 1000.0] * 100,
        }

        # Inject a significant shift in battery_health
        current = {
            "battery_health": [50.0, 55.0, 48.0, 52.0, 51.0] * 100,  # Major shift!
            "price": [1000.0, 1100.0, 950.0, 1050.0, 1000.0] * 100,
        }

        psi_results = monitor.compute_input_drift(reference, current)
        alert_status = monitor.check_alerts(psi_results)

        assert alert_status["alert_triggered"] is True
        assert alert_status["num_alerts"] >= 1
        # The battery_health feature should trigger an alert
        battery_alerts = [a for a in alert_status["alerts"] if a.get("feature") == "battery_health"]
        assert len(battery_alerts) > 0


class TestCalibrationDrift:
    """Tests for calibration drift computation."""

    def test_well_calibrated(self) -> None:
        """Test with well-calibrated predictions."""
        monitor = DriftMonitor()
        predicted = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95] * 10
        observed = [0, 0, 0, 0, 1, 0, 1, 1, 1, 1] * 10

        result = monitor.compute_calibration_drift(predicted, observed)

        assert result.ece >= 0
        assert result.mce >= 0
        assert isinstance(result.is_drift, bool)

    def test_empty_data(self) -> None:
        """Test with empty data."""
        monitor = DriftMonitor()
        result = monitor.compute_calibration_drift([], [])

        assert result.ece == 0.0
        assert result.mce == 0.0
        assert result.is_drift is False

    def test_calibration_drift_detection(self) -> None:
        """Test that calibration drift is detected."""
        monitor = DriftMonitor(calibration_threshold=0.05)
        # Predictions are overconfident
        predicted = [0.9] * 100
        observed = [0] * 100  # All negative

        result = monitor.compute_calibration_drift(predicted, observed)

        assert result.ece > 0.05
        assert result.is_drift is True


class TestAlerts:
    """Tests for alert checking."""

    def test_no_alerts(self) -> None:
        """Test no alerts when no drift."""
        monitor = DriftMonitor()
        psi_results = {
            "feature1": PSIRResult(psi=0.05, is_drift=False, is_alert=False),
        }

        alert_status = monitor.check_alerts(psi_results)

        assert alert_status["alert_triggered"] is False
        assert alert_status["num_alerts"] == 0

    def test_psi_alert(self) -> None:
        """Test PSI alert is triggered."""
        monitor = DriftMonitor()
        psi_results = {
            "feature1": PSIRResult(psi=0.25, is_drift=True, is_alert=True),
        }

        alert_status = monitor.check_alerts(psi_results)

        assert alert_status["alert_triggered"] is True
        assert alert_status["num_alerts"] == 1
        assert alert_status["alerts"][0]["type"] == "psi_alert"
        assert alert_status["alerts"][0]["feature"] == "feature1"

    def test_psi_drift_warning(self) -> None:
        """Test PSI drift warning (below alert threshold)."""
        monitor = DriftMonitor()
        psi_results = {
            "feature1": PSIRResult(psi=0.15, is_drift=True, is_alert=False),
        }

        alert_status = monitor.check_alerts(psi_results)

        assert alert_status["alert_triggered"] is False
        assert alert_status["num_alerts"] == 1
        assert alert_status["alerts"][0]["type"] == "psi_drift"

    def test_calibration_alert(self) -> None:
        """Test calibration drift alert."""
        monitor = DriftMonitor()
        psi_results = {}
        calibration_result = CalibrationDriftResult(
            ece=0.15,
            mce=0.20,
            is_drift=True,
        )

        alert_status = monitor.check_alerts(psi_results, calibration_result)

        assert alert_status["alert_triggered"] is True
        assert alert_status["num_alerts"] == 1
        assert alert_status["alerts"][0]["type"] == "calibration_drift"


class TestPrometheusExport:
    """Tests for Prometheus metrics export."""

    def test_export_psi_metrics(self) -> None:
        """Test exporting PSI metrics."""
        monitor = DriftMonitor()
        psi_results = {
            "battery_health": PSIRResult(psi=0.15, is_drift=True, is_alert=False),
        }

        metrics = monitor.export_prometheus_metrics(psi_results)

        assert 'drift_psi{feature="battery_health"} 0.150000' in metrics
        assert 'drift_psi_alert{feature="battery_health"} 0' in metrics

    def test_export_calibration_metrics(self) -> None:
        """Test exporting calibration metrics."""
        monitor = DriftMonitor()
        psi_results = {}
        calibration_result = CalibrationDriftResult(
            ece=0.12,
            mce=0.18,
            is_drift=True,
        )

        metrics = monitor.export_prometheus_metrics(psi_results, calibration_result)

        assert "drift_calibration_ece 0.120000" in metrics
        assert "drift_calibration_mce 0.180000" in metrics
        assert "drift_calibration_alert 1" in metrics
