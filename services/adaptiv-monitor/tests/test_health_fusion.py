"""Tests for health fusion logic."""

import pytest

from adaptiv_monitor.health_fusion import HealthFusion, HealthResult, compute_health


class TestHealthFusion:
    """Test cases for HealthFusion class."""

    def test_perfect_health(self) -> None:
        """Zero anomaly and residual should give 100% health."""
        fusion = HealthFusion()
        result = fusion.compute(anomaly_score=0.0, physics_residual=0.0)

        assert result.health_index == 100
        assert result.health_confidence == 1.0
        assert result.anomaly_score == 0.0
        assert result.physics_residual == 0.0

    def test_severe_degradation(self) -> None:
        """High anomaly and residual should give low health."""
        fusion = HealthFusion()
        result = fusion.compute(anomaly_score=1.0, physics_residual=1.0)

        assert result.health_index == 0
        assert result.health_confidence == 0.0

    def test_ml_only_anomaly(self) -> None:
        """ML anomaly without physics confirmation."""
        fusion = HealthFusion(ml_weight=0.6, physics_weight=0.4)
        result = fusion.compute(anomaly_score=0.8, physics_residual=0.0)

        # Confidence = 1 - min(1, 0.6*0.8 + 0.4*0.0) = 1 - 0.48 = 0.52
        assert result.health_index == 52
        assert result.health_confidence == pytest.approx(0.52, rel=0.01)

    def test_physics_only_residual(self) -> None:
        """Physics residual without ML anomaly."""
        fusion = HealthFusion(ml_weight=0.6, physics_weight=0.4)
        result = fusion.compute(anomaly_score=0.0, physics_residual=0.8)

        # Confidence = 1 - min(1, 0.6*0.0 + 0.4*0.8) = 1 - 0.32 = 0.68
        assert result.health_index == 68
        assert result.health_confidence == pytest.approx(0.68, rel=0.01)

    def test_moderate_degradation(self) -> None:
        """Moderate degradation from both sources."""
        fusion = HealthFusion()
        result = fusion.compute(anomaly_score=0.3, physics_residual=0.4)

        # Should be in healthy-ish range
        assert 50 <= result.health_index <= 90

    def test_value_capping(self) -> None:
        """Values outside [0,1] should be capped."""
        fusion = HealthFusion()

        # Negative values
        result = fusion.compute(anomaly_score=-0.5, physics_residual=-0.3)
        assert result.health_index == 100

        # Values > 1
        result = fusion.compute(anomaly_score=1.5, physics_residual=2.0)
        assert result.health_index == 0

    def test_custom_weights(self) -> None:
        """Test with custom weights."""
        # ML-heavy weighting
        fusion = HealthFusion(ml_weight=0.9, physics_weight=0.1)
        result = fusion.compute(anomaly_score=0.5, physics_residual=0.5)

        # Confidence = 1 - min(1, 0.9*0.5 + 0.1*0.5) = 1 - 0.5 = 0.5
        assert result.health_index == 50


class TestComputeHealth:
    """Test convenience function."""

    def test_returns_tuple(self) -> None:
        """Should return 4-tuple."""
        result = compute_health(0.2, 0.3)
        assert len(result) == 4
        health_idx, conf, anomaly, residual = result
        assert isinstance(health_idx, int)
        assert isinstance(conf, float)
        assert isinstance(anomaly, float)
        assert isinstance(residual, float)

    def test_edge_cases(self) -> None:
        """Test boundary conditions."""
        # Perfect health
        health, conf, _, _ = compute_health(0.0, 0.0)
        assert health == 100
        assert conf == 1.0

        # Complete failure
        health, conf, _, _ = compute_health(1.0, 1.0)
        assert health == 0
        assert conf == 0.0
