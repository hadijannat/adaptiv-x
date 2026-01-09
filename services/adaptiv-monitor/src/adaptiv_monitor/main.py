"""
Adaptiv-Monitor: Hybrid AI Health Monitoring Service

This service implements the core health monitoring logic for Adaptiv-X:
1. Consumes vibration data from MQTT or HTTP
2. Computes ML-based anomaly scores (PyTorch)
3. Validates anomalies via FMU physics simulation (FMPy)
4. Fuses ML + Physics into HealthIndex and HealthConfidence
5. Updates AAS Health submodel via BaSyx API
6. Emits events for downstream services (skill-broker)

Part of Adaptiv-X: Capability-Based Self-Healing Digital Twin
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from adaptiv_monitor.basyx_client import BasyxClient
from adaptiv_monitor.config import Settings
from adaptiv_monitor.fmu_runner import FMURunner
from adaptiv_monitor.health_fusion import HealthFusion, HealthResult
from adaptiv_monitor.ml_model import AnomalyDetector
from adaptiv_monitor.mqtt_client import MQTTClient


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
settings = Settings()
basyx_client: BasyxClient | None = None
fmu_runner: FMURunner | None = None
anomaly_detector: AnomalyDetector | None = None
mqtt_client: MQTTClient | None = None
health_fusion: HealthFusion | None = None


# ============================================================================
# Pydantic Models
# ============================================================================


class VibrationData(BaseModel):
    """Vibration measurement data from sensors."""

    asset_id: str = Field(..., description="Asset identifier (e.g., milling-01)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    vib_rms: float = Field(..., ge=0, description="Measured RMS vibration [mm/s]")
    omega: float = Field(..., ge=0, description="Spindle speed [rad/s]")
    load: float = Field(..., ge=0, description="Cutting load [N]")
    wear: float = Field(0.0, ge=0, le=1, description="Estimated wear level [0-1]")


class HealthAssessment(BaseModel):
    """Health assessment result from hybrid AI analysis."""

    asset_id: str
    health_index: int = Field(..., ge=0, le=100)
    health_confidence: float = Field(..., ge=0, le=1)
    anomaly_score: float = Field(..., ge=0, le=1)
    physics_residual: float = Field(..., ge=0, le=1)
    decision_rationale: str
    timestamp: datetime


class TriggerRequest(BaseModel):
    """Request to trigger health assessment for an asset."""

    asset_id: str
    vib_rms: float = Field(..., ge=0)
    omega: float = Field(default=100.0, ge=0)
    load: float = Field(default=500.0, ge=0)
    wear: float = Field(default=0.0, ge=0, le=1)


# ============================================================================
# FastAPI Application
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan for startup/shutdown."""
    global basyx_client, fmu_runner, anomaly_detector, mqtt_client, health_fusion

    logger.info("Starting Adaptiv-Monitor service...")

    # Initialize components
    basyx_client = BasyxClient(
        aas_environment_url=settings.aas_environment_url,
        aas_registry_url=settings.aas_registry_url,
        submodel_registry_url=settings.submodel_registry_url,
    )

    fmu_runner = FMURunner(
        minio_endpoint=settings.minio_endpoint,
        minio_access_key=settings.minio_access_key,
        minio_secret_key=settings.minio_secret_key,
        minio_bucket=settings.minio_bucket,
    )

    anomaly_detector = AnomalyDetector(
        threshold_vib_rms=settings.anomaly_threshold_vib_rms,
        threshold_factor=settings.anomaly_threshold_factor,
        zscore_threshold=settings.anomaly_zscore_threshold,
        min_samples=settings.anomaly_min_samples,
        window_size=settings.anomaly_window_size,
        model_path=settings.anomaly_model_path,
    )
    health_fusion = HealthFusion(
        ml_weight=settings.ml_weight,
        physics_weight=settings.physics_weight,
    )

    mqtt_client = MQTTClient(
        broker_host=settings.mqtt_broker_host,
        broker_port=settings.mqtt_broker_port,
    )
    await mqtt_client.connect()

    logger.info("Adaptiv-Monitor service started successfully")

    yield

    # Cleanup
    logger.info("Shutting down Adaptiv-Monitor service...")
    if basyx_client:
        await basyx_client.close()
    if mqtt_client:
        await mqtt_client.disconnect()


app = FastAPI(
    title="Adaptiv-Monitor",
    description="Hybrid AI Health Monitoring for Self-Healing Digital Twins",
    version="0.1.0",
    lifespan=lifespan,
)


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Service health check endpoint."""
    return {"status": "healthy", "service": "adaptiv-monitor"}


@app.post("/assess", response_model=HealthAssessment)
async def assess_health(data: VibrationData) -> HealthAssessment:
    """
    Perform hybrid AI health assessment for an asset.

    1. Apply ML anomaly detection to vibration data
    2. Run FMU simulation for physics-based expected values
    3. Compute residual between measured and expected
    4. Fuse ML and physics into HealthIndex
    5. Update AAS Health submodel
    """
    if not all([basyx_client, fmu_runner, anomaly_detector, health_fusion, mqtt_client]):
        raise HTTPException(status_code=503, detail="Service not fully initialized")

    logger.info(f"Assessing health for asset: {data.asset_id}")

    # Step 1: ML Anomaly Detection
    anomaly_score = anomaly_detector.detect(data.vib_rms, data.omega, data.load)  # type: ignore[union-attr]
    logger.debug(f"Anomaly score: {anomaly_score:.3f}")

    # Step 2: FMU Physics Simulation
    try:
        fmu_result = await fmu_runner.simulate(  # type: ignore[union-attr]
            asset_id=data.asset_id,
            omega=data.omega,
            load=data.load,
            wear=data.wear,
            basyx_client=basyx_client,  # type: ignore[arg-type]
        )
        vib_expected = fmu_result.get("vib_rms_expected", data.vib_rms)
    except Exception as e:
        logger.warning(f"FMU simulation failed: {e}. Using measured value as expected.")
        vib_expected = data.vib_rms

    # Step 3: Physics Residual
    residual = abs(data.vib_rms - vib_expected) / max(vib_expected, 0.1)
    physics_residual = min(1.0, residual)
    logger.debug(f"Physics residual: {physics_residual:.3f}")

    # Step 4: Health Fusion
    result: HealthResult = health_fusion.compute(anomaly_score, physics_residual)  # type: ignore[union-attr]

    # Generate decision rationale
    rationale = _generate_rationale(anomaly_score, physics_residual, result)

    # Step 5: Update AAS Health Submodel
    try:
        await basyx_client.update_health_submodel(  # type: ignore[union-attr]
            asset_id=data.asset_id,
            health_index=result.health_index,
            health_confidence=result.health_confidence,
            anomaly_score=anomaly_score,
            physics_residual=physics_residual,
            rationale=rationale,
        )
        logger.info(f"Updated Health submodel for {data.asset_id}")
    except Exception as e:
        logger.error(f"Failed to update AAS: {e}")

    # Step 6: Publish MQTT Event
    await mqtt_client.publish_health_event(  # type: ignore[union-attr]
        asset_id=data.asset_id,
        health_index=result.health_index,
        health_confidence=result.health_confidence,
        anomaly_score=anomaly_score,
        physics_residual=physics_residual,
    )

    return HealthAssessment(
        asset_id=data.asset_id,
        health_index=result.health_index,
        health_confidence=result.health_confidence,
        anomaly_score=anomaly_score,
        physics_residual=physics_residual,
        decision_rationale=rationale,
        timestamp=datetime.now(timezone.utc),
    )


@app.post("/trigger", response_model=HealthAssessment)
async def trigger_assessment(request: TriggerRequest) -> HealthAssessment:
    """Convenience endpoint to trigger assessment with minimal parameters."""
    data = VibrationData(
        asset_id=request.asset_id,
        vib_rms=request.vib_rms,
        omega=request.omega,
        load=request.load,
        wear=request.wear,
    )
    return await assess_health(data)


@app.get("/assets/{asset_id}/health", response_model=HealthAssessment | None)
async def get_current_health(asset_id: str) -> HealthAssessment | None:
    """Get current health status from AAS for an asset."""
    if not basyx_client:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        health_data = await basyx_client.get_health_submodel(asset_id)
        if not health_data:
            return None

        return HealthAssessment(
            asset_id=asset_id,
            health_index=health_data.get("HealthIndex", 100),
            health_confidence=health_data.get("HealthConfidence", 1.0),
            anomaly_score=health_data.get("AnomalyScore", 0.0),
            physics_residual=health_data.get("PhysicsResidual", 0.0),
            decision_rationale=health_data.get("DecisionRationale", ""),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(f"Failed to get health for {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Helper Functions
# ============================================================================


def _generate_rationale(
    anomaly_score: float, physics_residual: float, result: HealthResult
) -> str:
    """Generate human-readable explanation for health assessment decision."""
    parts = []

    if anomaly_score < 0.2:
        parts.append("ML model detected normal vibration patterns")
    elif anomaly_score < 0.5:
        parts.append("ML model detected minor anomalies in vibration")
    else:
        parts.append("ML model detected significant anomalies in vibration")

    if physics_residual < 0.2:
        parts.append("Physics model confirms expected behavior")
    elif physics_residual < 0.5:
        parts.append("Physics model shows moderate deviation from expected")
    else:
        parts.append("Physics model shows significant deviation from expected (possible wear)")

    if result.health_index >= 90:
        parts.append("Asset is in healthy condition")
    elif result.health_index >= 80:
        parts.append("Asset shows early signs of degradation")
    else:
        parts.append("Asset requires attention - capability may be compromised")

    return ". ".join(parts) + "."


def run() -> None:
    """Entry point for running the service."""
    import uvicorn

    uvicorn.run(
        "adaptiv_monitor.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()
