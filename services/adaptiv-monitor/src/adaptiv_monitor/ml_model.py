"""
ML-based Anomaly Detection for Adaptiv-Monitor.

Implements a production-ready statistical detector with an optional model-file hook
for calibrated coefficients and thresholds. The detector combines:
- A physics-aligned expected vibration baseline (linear in omega/load)
- Online residual statistics (rolling window z-score)
- Absolute safety thresholds for hard limits
"""

from __future__ import annotations

import json
import logging
import math
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class LinearModelCoefficients:
    """Linear baseline coefficients for expected vibration."""

    base: float = 0.5
    k1: float = 0.001
    k2: float = 0.002


@dataclass
class DetectorConfig:
    """Configuration for anomaly detection."""

    threshold_vib_rms: float = 3.0
    threshold_factor: float = 2.0
    zscore_threshold: float = 3.0
    min_samples: int = 20
    window_size: int = 200
    coefficients: LinearModelCoefficients = field(default_factory=LinearModelCoefficients)


class AnomalyDetector:
    """
    Statistical anomaly detection for vibration data.

    Uses a calibrated linear baseline and rolling residual stats. A model file
    (JSON) can override thresholds and coefficients for deployment tuning.
    """

    def __init__(
        self,
        *,
        threshold_vib_rms: float = 3.0,
        threshold_factor: float = 2.0,
        zscore_threshold: float = 3.0,
        min_samples: int = 20,
        window_size: int = 200,
        model_path: str | None = None,
    ) -> None:
        self._config = DetectorConfig(
            threshold_vib_rms=threshold_vib_rms,
            threshold_factor=threshold_factor,
            zscore_threshold=zscore_threshold,
            min_samples=min_samples,
            window_size=window_size,
        )

        if model_path:
            self._load_model_file(model_path)

        self._residuals: deque[float] = deque(maxlen=self._config.window_size)
        self._sum = 0.0
        self._sum_sq = 0.0

    def detect(self, vib_rms: float, omega: float = 100.0, load: float = 500.0) -> float:
        """
        Detect anomaly in vibration data.

        Returns:
            Anomaly score in range [0, 1]
        """
        expected_vib = self._estimate_expected(omega, load)
        residual = vib_rms - expected_vib

        self._update_residual_stats(residual)

        zscore = self._compute_zscore(residual)
        ratio = abs(residual) / max(expected_vib, 0.5)

        zscore_score = min(1.0, zscore / max(self._config.zscore_threshold, 0.1))
        ratio_score = min(1.0, ratio)

        anomaly_score = min(1.0, 0.5 * ratio_score + 0.5 * zscore_score)

        if vib_rms > self._config.threshold_vib_rms * self._config.threshold_factor:
            anomaly_score = max(anomaly_score, 0.8)

        logger.debug(
            "Anomaly detection: vib=%.2f expected=%.2f residual=%.2f z=%.2f score=%.3f",
            vib_rms,
            expected_vib,
            residual,
            zscore,
            anomaly_score,
        )

        return anomaly_score

    def _estimate_expected(self, omega: float, load: float) -> float:
        """Estimate expected vibration based on operating conditions."""
        coeffs = self._config.coefficients
        return coeffs.base + coeffs.k1 * omega + coeffs.k2 * load

    def _update_residual_stats(self, residual: float) -> None:
        if len(self._residuals) == self._residuals.maxlen:
            oldest = self._residuals.popleft()
            self._sum -= oldest
            self._sum_sq -= oldest * oldest

        self._residuals.append(residual)
        self._sum += residual
        self._sum_sq += residual * residual

    def _compute_zscore(self, residual: float) -> float:
        n = len(self._residuals)
        if n < max(self._config.min_samples, 2):
            return 0.0

        mean = self._sum / n
        variance = max(0.0, (self._sum_sq / n) - mean * mean)
        std = math.sqrt(variance) if variance > 1e-9 else 1e-6
        return abs(residual - mean) / std

    def _load_model_file(self, path: str) -> None:
        """Load detector coefficients and thresholds from a JSON model file."""
        model_path = Path(path)
        if not model_path.exists():
            logger.warning("Model file not found: %s. Using defaults.", path)
            return

        try:
            with model_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)

            thresholds = data.get("thresholds", {})
            coefficients = data.get("coefficients", {})

            self._config.threshold_vib_rms = float(
                thresholds.get("vib_rms", self._config.threshold_vib_rms)
            )
            self._config.threshold_factor = float(
                thresholds.get("factor", self._config.threshold_factor)
            )
            self._config.zscore_threshold = float(
                thresholds.get("zscore", self._config.zscore_threshold)
            )
            self._config.min_samples = int(
                thresholds.get("min_samples", self._config.min_samples)
            )
            self._config.window_size = int(
                thresholds.get("window_size", self._config.window_size)
            )
            self._config.coefficients = LinearModelCoefficients(
                base=float(coefficients.get("base", self._config.coefficients.base)),
                k1=float(coefficients.get("k1", self._config.coefficients.k1)),
                k2=float(coefficients.get("k2", self._config.coefficients.k2)),
            )
            logger.info("Loaded anomaly detector model from %s", path)

        except (json.JSONDecodeError, OSError, ValueError) as exc:
            logger.warning("Failed to load model file %s: %s. Using defaults.", path, exc)

    def get_statistics(self) -> dict[str, float]:
        """Get current residual statistics."""
        n = len(self._residuals)
        if n == 0:
            return {"mean": 0.0, "std": 0.0, "count": 0}

        mean = self._sum / n
        variance = max(0.0, (self._sum_sq / n) - mean * mean)
        std = math.sqrt(variance)
        return {"mean": mean, "std": std, "count": n}

    def reset(self) -> None:
        """Reset detection history."""
        self._residuals.clear()
        self._sum = 0.0
        self._sum_sq = 0.0
