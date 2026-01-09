"""
Health Fusion for Adaptiv-Monitor.

Combines ML anomaly score and physics residual into unified health metrics.
Implements the hybrid AI approach for trustworthy industrial analytics.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HealthResult:
    """Result of health fusion computation."""

    health_index: int       # 0-100 overall health
    health_confidence: float  # 0-1 confidence in assessment
    anomaly_score: float     # 0-1 normalized anomaly score
    physics_residual: float  # 0-1 normalized physics residual


class HealthFusion:
    """
    Fuses ML and physics signals into unified health metrics.

    The fusion algorithm follows the trustworthy AI principle:
    - ML provides fast anomaly detection
    - Physics provides plausibility validation
    - Fusion integrates both for reliable health assessment

    Fusion formula:
        confidence = 1 - min(1, ml_weight * anomaly + physics_weight * residual)
        health = 100 * confidence
    """

    def __init__(
        self,
        ml_weight: float = 0.6,
        physics_weight: float = 0.4,
    ) -> None:
        """
        Initialize the health fusion engine.

        Args:
            ml_weight: Weight for ML anomaly score (default 0.6)
            physics_weight: Weight for physics residual (default 0.4)
        """
        if not (0 <= ml_weight <= 1 and 0 <= physics_weight <= 1):
            raise ValueError("Weights must be in [0, 1]")

        self.ml_weight = ml_weight
        self.physics_weight = physics_weight

    def compute(
        self, anomaly_score: float, physics_residual: float
    ) -> HealthResult:
        """
        Compute fused health metrics.

        Args:
            anomaly_score: ML anomaly score in [0, 1]
            physics_residual: Physics model residual in [0, 1]

        Returns:
            HealthResult with unified health metrics
        """
        # Normalize inputs to valid range
        a = min(1.0, max(0.0, anomaly_score))
        r = min(1.0, max(0.0, physics_residual))

        # Weighted fusion for confidence
        # Higher anomaly/residual = lower confidence
        confidence = 1.0 - min(1.0, self.ml_weight * a + self.physics_weight * r)

        # Health index scaled to 0-100
        health_index = int(100 * confidence)

        return HealthResult(
            health_index=health_index,
            health_confidence=round(confidence, 3),
            anomaly_score=round(a, 3),
            physics_residual=round(r, 3),
        )

    def compute_with_history(
        self,
        current_anomaly: float,
        current_residual: float,
        history_anomaly: list[float] | None = None,
        history_residual: list[float] | None = None,
        history_weight: float = 0.3,
    ) -> HealthResult:
        """
        Compute health with historical smoothing.

        Args:
            current_anomaly: Current ML anomaly score
            current_residual: Current physics residual
            history_anomaly: Recent anomaly scores
            history_residual: Recent physics residuals
            history_weight: Weight for historical values

        Returns:
            HealthResult with smoothed metrics
        """
        # Smooth anomaly score
        if history_anomaly:
            avg_anomaly = sum(history_anomaly) / len(history_anomaly)
            smoothed_anomaly = (
                (1 - history_weight) * current_anomaly + history_weight * avg_anomaly
            )
        else:
            smoothed_anomaly = current_anomaly

        # Smooth physics residual
        if history_residual:
            avg_residual = sum(history_residual) / len(history_residual)
            smoothed_residual = (
                (1 - history_weight) * current_residual + history_weight * avg_residual
            )
        else:
            smoothed_residual = current_residual

        return self.compute(smoothed_anomaly, smoothed_residual)


def compute_health(
    anomaly_score: float, physics_residual: float
) -> tuple[int, float, float, float]:
    """
    Convenience function for health computation.

    Returns:
        Tuple of (health_index, confidence, anomaly_score, physics_residual)
    """
    fusion = HealthFusion()
    result = fusion.compute(anomaly_score, physics_residual)
    return (
        result.health_index,
        result.health_confidence,
        result.anomaly_score,
        result.physics_residual,
    )
