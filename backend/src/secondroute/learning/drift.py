"""
Drift monitoring for Phase 6 (F6.4).

Population stability index on inputs, calibration drift on outputs.
Exported to Prometheus and shown in Grafana with alert rules.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone, UTC
from typing import Any, Optional, Sequence
from uuid import UUID

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

PSI_THRESHOLD_LOW = 0.1
PSI_THRESHOLD_HIGH = 0.2


@dataclass
class PSIRResult:
    psi: float
    is_drift: bool
    is_alert: bool
    bins: list[float] = field(default_factory=list)
    expected_pct: list[float] = field(default_factory=list)
    actual_pct: list[float] = field(default_factory=list)


@dataclass
class CalibrationDriftResult:
    ece: float
    mce: float
    is_drift: bool
    bins: list[float] = field(default_factory=list)
    predicted_avg: list[float] = field(default_factory=list)
    observed_freq: list[float] = field(default_factory=list)


class DriftMonitor:
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
        if not expected or not actual:
            return PSIRResult(psi=0.0, is_drift=False, is_alert=False)

        expected_arr = np.asarray(expected, dtype=np.float64)
        actual_arr = np.asarray(actual, dtype=np.float64)

        bin_edges = np.percentile(expected_arr, np.linspace(0, 100, bins + 1))
        bin_edges = np.unique(bin_edges)
        if len(bin_edges) < 2:
            return PSIRResult(psi=0.0, is_drift=False, is_alert=False)

        expected_counts, _ = np.histogram(expected_arr, bins=bin_edges)
        actual_counts, _ = np.histogram(actual_arr, bins=bin_edges)

        expected_pct = (expected_counts + 1e-10) / len(expected_arr)
        actual_pct = (actual_counts + 1e-10) / len(actual_arr)

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
        if not predicted or not observed:
            return CalibrationDriftResult(ece=0.0, mce=0.0, is_drift=False)

        predicted_arr = np.asarray(predicted, dtype=np.float64)
        observed_arr = np.asarray(observed, dtype=np.float64)

        bin_edges = np.linspace(0, 1, bins + 1)

        ece = 0.0
        mce = 0.0
        predicted_avg = []
        observed_freq = []

        for i in range(bins):
            mask = (predicted_arr >= bin_edges[i]) & (predicted_arr < bin_edges[i + 1])
            if i == bins - 1:
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
        lines = []

        for feature_name, result in psi_results.items():
            lines.append(f'drift_psi{{feature="{feature_name}"}} {result.psi:.6f}')
            lines.append(f'drift_psi_alert{{feature="{feature_name}"}} {1 if result.is_alert else 0}')

        if calibration_result:
            lines.append(f'drift_calibration_ece {calibration_result.ece:.6f}')
            lines.append(f'drift_calibration_mce {calibration_result.mce:.6f}')
            lines.append(f'drift_calibration_alert {1 if calibration_result.is_drift else 0}')

        return "\n".join(lines)