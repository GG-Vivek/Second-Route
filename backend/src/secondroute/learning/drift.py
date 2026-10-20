"""
Drift monitoring for Phase 6 (F6.4).

Population stability index on inputs, calibration drift on outputs.
Exported to Prometheus and shown in Grafana with alert rules.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone, UTC
from typing import Any, Optional, Sequence
from uuid import UUID

import numpy as np
import structlog
from pydantic import BaseModel, ConfigDict

logger = structlog.get_logger(__name__)

# PSI thresholds (standard industry values)
PSI_THRESHOLD_LOW = 0.1  # No significant change
PSI_THRESHOLD_HIGH = 0.2  # Significant change - alert


@dataclass
class PSIRResult:
    """Result of population stability index calculation.

    Attributes:
        psi: The PSI value.
        is_drift: Whether significant drift is detected.
        is_alert: Whether an alert should be triggered.
        bins: The bin edges used.
        expected_pct: Percentage in each bin for expected distribution.
        actual_pct: Percentage in each bin for actual distribution.
    """

    psi: float
    is_drift: bool
    is_alert: bool
    bins: list[float] = field(default_factory=list)
    expected_pct: list[float] = field(default_factory=list)
    actual_pct: list[float] = field(default_factory=list)


@dataclass
class CalibrationDriftResult:
    """Result of calibration drift calculation.

    Attributes:
        ece: Expected calibration error.
        mce: Maximum calibration error.
        is_drift: Whether significant calibration drift is detected.
        bins: The bin edges used.
        predicted_avg: Average predicted probability per bin.
        observed_freq: Observed frequency per bin.
    """

    ece: float
    mce: float
    is_drift: bool
    bins: list[float] = field(default_factory=list)
    predicted_avg: list[float] = field(default_factory=list)
    observed_freq: list[float] = field(default_factory=list)


class DriftMonitor:
    """Monitors drift in model inputs and outputs.

    Computes:
    - Population Stability Index (PSI) for input features
    - Calibration drift (ECE/MCE) for output predictions
    """

    def __init__(
        self,
        psi_threshold_low: float = PSI_THRESHOLD_LOW,
        psi_threshold_high: float = PSI_THRESHOLD_HIGH,
        calibration_threshold: float = 0.1,
    ) -> None:
        self.psi_threshold_low = psi_threshold_low
        self.psi_threshold_high = psi_threshold_high
        self.calibration_threshold = calibration_threshold

    def compute_psi(
        self,
        expected: Sequence[float],
        actual: Sequence[float],
        bins: int = 10,
    ) -> PSIRResult:
        """Compute Population Stability Index.

        PSI measures how much the distribution of a feature has changed
        between a reference (expected) population and a current (actual)
        population.

        Formula: PSI = sum((actual_pct - expected_pct) * ln(actual_pct / expected_pct))

        Args:
            expected: Reference distribution values.
            actual: Current distribution values.
            bins: Number of bins to use.

        Returns:
            PSIRResult with PSI value and drift flags.
        """
        if not expected or not actual:
            return PSIRResult(psi=0.0, is_drift=False, is_alert=False)

        expected_arr = np.asarray(expected, dtype=np.float64)
        actual_arr = np.asarray(actual, dtype=np.float64)

        # Create bins based on expected distribution
        bin_edges = np.percentile(expected_arr, np.linspace(0, 100, bins + 1))
        # Ensure unique bin edges
        bin_edges = np.unique(bin_edges)
        if len(bin_edges) < 2:
            # All values the same - no drift possible
            return PSIRResult(psi=0.0, is_drift=False, is_alert=False)

        # Compute percentages in each bin
        expected_counts, _ = np.histogram(expected_arr, bins=bin_edges)
        actual_counts, _ = np.histogram(actual_arr, bins=bin_edges)

        # Convert to percentages
        expected_pct = (expected_counts + 1e-10) / len(expected_arr)  # Add small epsilon
        actual_pct = (actual_counts + 1e-10) / len(actual_arr)

        # Compute PSI
        psi = 0.0
        for i in range(len(expected_pct)):
            if expected_pct[i] > 0 and actual_pct[i] > 0:
                psi += (actual_pct[i] - expected_pct[i]) * np.log(actual_pct[i] / expected_pct[i])

        is_drift = bool(psi >= self.psi_threshold_low)
        is_alert = bool(psi >= self.psi_threshold_high)

        return PSIRResult(
            psi=float(psi),
            is_drift=is_drift,
            is_alert=is_alert,
            bins=bin_edges.tolist(),
            expected_pct=expected_pct.tolist(),
            actual_pct=actual_pct.tolist(),
        )

    def compute_calibration_drift(
        self,
        predicted: Sequence[float],
        observed: Sequence[bool],
        bins: int = 10,
    ) -> CalibrationDriftResult:
        """Compute calibration drift (ECE and MCE).

        Expected Calibration Error (ECE) measures how well predicted
        probabilities match observed frequencies.

        Args:
            predicted: Predicted probabilities.
            observed: Observed outcomes (True/False).
            bins: Number of bins to use.

        Returns:
            CalibrationDriftResult with ECE, MCE, and drift flag.
        """
        if not predicted or not observed:
            return CalibrationDriftResult(ece=0.0, mce=0.0, is_drift=False)

        predicted_arr = np.asarray(predicted, dtype=np.float64)
        observed_arr = np.asarray(observed, dtype=np.float64)

        # Create bins
        bin_edges = np.linspace(0, 1, bins + 1)

        # Compute ECE and MCE
        ece = 0.0
        mce = 0.0
        predicted_avg = []
        observed_freq = []

        for i in range(bins):
            mask = (predicted_arr >= bin_edges[i]) & (predicted_arr < bin_edges[i + 1])
            if i == bins - 1:  # Last bin includes upper bound
                mask = (predicted_arr >= bin_edges[i]) & (predicted_arr <= bin_edges[i + 1])

            if mask.sum() > 0:
                bin_predicted = predicted_arr[mask].mean()
                bin_observed = observed_arr[mask].mean()
                bin_count = mask.sum()
                weight = bin_count / len(predicted_arr)

                ece += weight * abs(bin_predicted - bin_observed)
                mce = max(mce, abs(bin_predicted - bin_observed))

                predicted_avg.append(float(bin_predicted))
                observed_freq.append(float(bin_observed))
            else:
                predicted_avg.append(0.0)
                observed_freq.append(0.0)

        is_drift = bool(ece >= self.calibration_threshold)

        return CalibrationDriftResult(
            ece=float(ece),
            mce=float(mce),
            is_drift=is_drift,
            bins=bin_edges.tolist(),
            predicted_avg=predicted_avg,
            observed_freq=observed_freq,
        )

    def compute_input_drift(
        self,
        reference: dict[str, Sequence[float]],
        current: dict[str, Sequence[float]],
    ) -> dict[str, PSIRResult]:
        """Compute PSI for multiple input features.

        Args:
            reference: Dictionary of feature name -> reference values.
            current: Dictionary of feature name -> current values.

        Returns:
            Dictionary of feature name -> PSIRResult.
        """
        results = {}
        for feature_name, _ in reference.items():
            if feature_name in current:
                results[feature_name] = self.compute_psi(
                    reference[feature_name],
                    current[feature_name],
                )
        return results

    def check_alerts(
        self,
        psi_results: dict[str, PSIRResult],
        calibration_result: CalibrationDriftResult | None = None,
    ) -> dict[str, Any]:
        """Check if any alerts should be triggered.

        Args:
            psi_results: Dictionary of feature name -> PSIRResult.
            calibration_result: Optional calibration drift result.

        Returns:
            Dictionary with alert status and details.
        """
        alerts = []
        alert_triggered = False

        for feature_name, result in psi_results.items():
            if result.is_alert:
                alerts.append({
                    "type": "psi_alert",
                    "feature": feature_name,
                    "psi": result.psi,
                    "threshold": self.psi_threshold_high,
                    "message": f"PSI for {feature_name} is {result.psi:.4f}, exceeding threshold {self.psi_threshold_high}",
                })
                alert_triggered = True
            elif result.is_drift:
                alerts.append({
                    "type": "psi_drift",
                    "feature": feature_name,
                    "psi": result.psi,
                    "threshold": self.psi_threshold_low,
                    "message": f"PSI for {feature_name} is {result.psi:.4f}, exceeding threshold {self.psi_threshold_low}",
                })

        if calibration_result and calibration_result.is_drift:
            alerts.append({
                "type": "calibration_drift",
                "ece": calibration_result.ece,
                "threshold": self.calibration_threshold,
                "message": f"Calibration ECE is {calibration_result.ece:.4f}, exceeding threshold {self.calibration_threshold}",
            })
            alert_triggered = True

        return {
            "alert_triggered": alert_triggered,
            "alerts": alerts,
            "num_alerts": len(alerts),
        }

    def export_prometheus_metrics(
        self,
        psi_results: dict[str, PSIRResult],
        calibration_result: CalibrationDriftResult | None = None,
    ) -> str:
        """Export drift metrics in Prometheus format.

        Args:
            psi_results: Dictionary of feature name -> PSIRResult.
            calibration_result: Optional calibration drift result.

        Returns:
            Prometheus-formatted metrics string.
        """
        lines = []

        # PSI metrics
        for feature_name, result in psi_results.items():
            lines.append(f'drift_psi{{feature="{feature_name}"}} {result.psi:.6f}')
            lines.append(f'drift_psi_alert{{feature="{feature_name}"}} {1 if result.is_alert else 0}')

        # Calibration metrics
        if calibration_result:
            lines.append(f'drift_calibration_ece {calibration_result.ece:.6f}')
            lines.append(f'drift_calibration_mce {calibration_result.mce:.6f}')
            lines.append(f'drift_calibration_alert {1 if calibration_result.is_drift else 0}')

        return "\n".join(lines)