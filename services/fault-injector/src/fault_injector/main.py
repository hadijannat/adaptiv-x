"""
Fault-Injector: Orchestrates fault injection scenarios.

Calls adaptiv-monitor for assessment and skill-broker for policy evaluation.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime

from aas_contract import (
    CAPABILITY_ELEMENT_PATHS,
    HEALTH_ELEMENT_PATHS,
    SUBMODEL_PREFIX,
)
from aas_contract import (
    __version__ as contract_version,
)
from adaptiv_auth import AuthSettings, AuthVerifier, auth_middleware, require_role
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from fault_injector.clients import BrokerClient, MonitorClient
from fault_injector.config import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = Settings()
auth_settings = AuthSettings(
    enabled=settings.auth_enabled,
    issuer=settings.oidc_issuer,
    audience=settings.oidc_audience,
    jwks_url=settings.oidc_jwks_url,
    cache_ttl_seconds=settings.auth_cache_ttl_seconds,
)
auth_verifier = AuthVerifier(auth_settings)


class FaultInjectionRequest(BaseModel):
    asset_id: str = Field(..., description="Asset identifier")
    vib_rms: float = Field(..., ge=0, description="Measured RMS vibration [mm/s]")
    omega: float = Field(default=150.0, ge=0, description="Spindle speed [rad/s]")
    load: float = Field(default=800.0, ge=0, description="Cutting load [N]")
    wear: float = Field(default=0.0, ge=0, le=1, description="Wear level [0-1]")
    evaluate_policy: bool = Field(
        default=True, description="Trigger skill-broker policy evaluation"
    )


class HealthAssessment(BaseModel):
    asset_id: str
    health_index: int
    health_confidence: float
    anomaly_score: float
    physics_residual: float
    decision_rationale: str
    timestamp: datetime


class FaultInjectionResponse(BaseModel):
    asset_id: str
    assessment: HealthAssessment
    policy_actions: list[dict[str, str]] | None = None
    policy_evaluated: bool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting Fault-Injector service...")
    monitor_client = MonitorClient(settings.monitor_url)
    broker_client = BrokerClient(settings.broker_url)

    app.state.monitor_client = monitor_client
    app.state.broker_client = broker_client

    yield

    logger.info("Shutting down Fault-Injector service...")
    await monitor_client.close()
    await broker_client.close()


app = FastAPI(
    title="Fault-Injector",
    description="Fault injection orchestrator for Adaptiv-X",
    version="0.1.0",
    lifespan=lifespan,
)
app.state.auth_enabled = settings.auth_enabled
app.state.auth_verifier = auth_verifier
app.middleware("http")(auth_middleware(auth_verifier))

DEMO_ADMIN_DEP = Depends(require_role("demo-admin"))


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "fault-injector"}


@app.get("/debug/contract")
async def debug_contract() -> dict[str, object]:
    """Expose shared AAS contract paths for verification."""
    return {
        "service": "fault-injector",
        "contract_version": contract_version,
        "submodel_prefix": SUBMODEL_PREFIX,
        "health_paths": HEALTH_ELEMENT_PATHS,
        "capability_paths": CAPABILITY_ELEMENT_PATHS,
    }


@app.post("/inject", response_model=FaultInjectionResponse)
async def inject_fault(
    request: FaultInjectionRequest,
    http_request: Request,
    _claims: dict[str, object] = DEMO_ADMIN_DEP,
) -> FaultInjectionResponse:
    monitor_client: MonitorClient = http_request.app.state.monitor_client
    broker_client: BrokerClient = http_request.app.state.broker_client

    assessment_payload = {
        "asset_id": request.asset_id,
        "vib_rms": request.vib_rms,
        "omega": request.omega,
        "load": request.load,
        "wear": request.wear,
    }

    try:
        assessment_data = await monitor_client.assess(assessment_payload)
    except Exception as exc:
        logger.error("Monitor assessment failed: %s", exc)
        raise HTTPException(status_code=502, detail="Monitor assessment failed") from exc

    assessment = HealthAssessment(**assessment_data)

    policy_actions: list[dict[str, str]] | None = None
    if request.evaluate_policy:
        try:
            policy_result = await broker_client.evaluate(
                request.asset_id, assessment.health_index
            )
            policy_actions = policy_result.get("actions_taken", [])
        except Exception as exc:
            logger.error("Policy evaluation failed: %s", exc)
            raise HTTPException(status_code=502, detail="Policy evaluation failed") from exc

    return FaultInjectionResponse(
        asset_id=request.asset_id,
        assessment=assessment,
        policy_actions=policy_actions,
        policy_evaluated=request.evaluate_policy,
    )


def run() -> None:
    import uvicorn

    uvicorn.run(
        "fault_injector.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()
