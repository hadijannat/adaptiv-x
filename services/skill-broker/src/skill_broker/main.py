"""
Skill-Broker: Semantic Capability Reasoning Service

This service implements the capability reasoning loop for Adaptiv-X:
1. Observes health events from adaptiv-monitor (via MQTT)
2. Evaluates policy rules to determine capability state changes
3. Patches AAS Capability submodel via BaSyx API
4. Logs all changes for auditability

The key semantic insight: capabilities are not just "on/off" but have
assurance states (assured, offered, notAvailable) following German
capability-based engineering principles.

Part of Adaptiv-X: Capability-Based Self-Healing Digital Twin
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from skill_broker.aas_patcher import AASPatcher
from skill_broker.config import Settings
from skill_broker.mqtt_subscriber import MQTTSubscriber
from skill_broker.policy_engine import PolicyAction, PolicyEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
settings = Settings()
policy_engine: PolicyEngine | None = None
aas_patcher: AASPatcher | None = None
mqtt_subscriber: MQTTSubscriber | None = None
_evaluation_task: asyncio.Task[None] | None = None


# ============================================================================
# Pydantic Models
# ============================================================================


class HealthEvent(BaseModel):
    """Health event received from adaptiv-monitor."""

    asset_id: str
    health_index: int = Field(..., ge=0, le=100)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CapabilityPatch(BaseModel):
    """Request to manually patch capability state."""

    asset_id: str
    path: str = Field(..., description="Submodel element path")
    value: str


class PolicyEvaluationResult(BaseModel):
    """Result of policy evaluation."""

    asset_id: str
    health_index: int
    actions_taken: list[dict[str, str]]
    timestamp: datetime


class AuditLogEntry(BaseModel):
    """Audit log entry for capability changes."""

    timestamp: datetime
    asset_id: str
    action: str
    path: str
    old_value: str | None
    new_value: str
    reason: str


MAX_AUDIT_LOG = 1000
audit_log: list[AuditLogEntry] = []


# ============================================================================
# FastAPI Application
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan for startup/shutdown."""
    global policy_engine, aas_patcher, mqtt_subscriber, _evaluation_task

    logger.info("Starting Skill-Broker service...")

    # Initialize components
    policy_engine = PolicyEngine(policy_file=settings.policy_file)
    aas_patcher = AASPatcher(aas_environment_url=settings.aas_environment_url)

    # Initialize MQTT subscriber with callback
    mqtt_subscriber = MQTTSubscriber(
        broker_host=settings.mqtt_broker_host,
        broker_port=settings.mqtt_broker_port,
        on_health_event=_handle_health_event,
    )
    await mqtt_subscriber.connect()

    # Start periodic evaluation (fallback if MQTT fails)
    if settings.enable_polling:
        _evaluation_task = asyncio.create_task(_periodic_evaluation())

    logger.info("Skill-Broker service started successfully")

    yield

    # Cleanup
    logger.info("Shutting down Skill-Broker service...")
    if _evaluation_task:
        _evaluation_task.cancel()
        try:
            await _evaluation_task
        except asyncio.CancelledError:
            logger.debug("Periodic evaluation task cancelled")
    if aas_patcher:
        await aas_patcher.close()
    if mqtt_subscriber:
        await mqtt_subscriber.disconnect()


app = FastAPI(
    title="Skill-Broker",
    description="Semantic Capability Reasoning for Self-Healing Digital Twins",
    version="0.1.0",
    lifespan=lifespan,
)


# ============================================================================
# Event Handlers
# ============================================================================


async def _handle_health_event(event: HealthEvent) -> None:
    """Handle health event from MQTT."""
    if not policy_engine or not aas_patcher:
        return

    logger.info(f"Received health event: {event.asset_id} = {event.health_index}")
    await _evaluate_and_apply(event.asset_id, event.health_index)


async def _evaluate_and_apply(asset_id: str, health_index: int) -> list[PolicyAction]:
    """Evaluate policy and apply capability changes."""
    if not policy_engine or not aas_patcher:
        return []

    # Get actions from policy engine
    actions = policy_engine.evaluate(health_index)

    if not actions:
        logger.debug(f"No policy actions for {asset_id} at health={health_index}")
        return []

    logger.info(f"Applying {len(actions)} capability changes for {asset_id}")

    # Apply each action
    for action in actions:
        try:
            old_value = await aas_patcher.get_element_value(asset_id, action.path)
            await aas_patcher.patch_element(asset_id, action.path, action.value)

            # Audit log
            entry = AuditLogEntry(
                timestamp=datetime.now(UTC),
                asset_id=asset_id,
                action="PATCH",
                path=action.path,
                old_value=old_value,
                new_value=action.value,
                reason=f"Health index = {health_index}",
            )
            audit_log.append(entry)
            if len(audit_log) > MAX_AUDIT_LOG:
                audit_log.pop(0)
            logger.info(f"Patched {action.path} = {action.value} (was: {old_value})")

        except Exception as e:
            logger.error(f"Failed to apply action {action}: {e}")

    return actions


async def _periodic_evaluation() -> None:
    """Periodic evaluation (fallback for MQTT)."""
    while True:
        await asyncio.sleep(settings.polling_interval_seconds)
        if not aas_patcher:
            continue

        assets = await aas_patcher.list_assets()
        if not assets:
            logger.debug("No assets discovered for periodic evaluation")
            continue

        for asset_id in assets:
            health_index = await aas_patcher.get_health_index(asset_id)
            if health_index is None:
                continue
            await _evaluate_and_apply(asset_id, health_index)


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Service health check endpoint."""
    return {"status": "healthy", "service": "skill-broker"}


@app.post("/evaluate", response_model=PolicyEvaluationResult)
async def evaluate_health(event: HealthEvent) -> PolicyEvaluationResult:
    """
    Manually trigger policy evaluation for a health event.

    Useful for testing and debugging.
    """
    if not policy_engine:
        raise HTTPException(status_code=503, detail="Service not initialized")

    actions = await _evaluate_and_apply(event.asset_id, event.health_index)

    return PolicyEvaluationResult(
        asset_id=event.asset_id,
        health_index=event.health_index,
        actions_taken=[{"path": a.path, "value": a.value} for a in actions],
        timestamp=datetime.now(UTC),
    )


@app.patch("/capability")
async def patch_capability(patch: CapabilityPatch) -> dict[str, str]:
    """Manually patch a capability value (admin override)."""
    if not aas_patcher:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        old_value = await aas_patcher.get_element_value(patch.asset_id, patch.path)
        await aas_patcher.patch_element(patch.asset_id, patch.path, patch.value)

        # Audit log
        entry = AuditLogEntry(
            timestamp=datetime.now(UTC),
            asset_id=patch.asset_id,
            action="MANUAL_PATCH",
            path=patch.path,
            old_value=old_value,
            new_value=patch.value,
            reason="Manual admin override",
        )
        audit_log.append(entry)
        if len(audit_log) > MAX_AUDIT_LOG:
            audit_log.pop(0)

        return {"status": "success", "message": f"Patched {patch.path} = {patch.value}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/policy/rules")
async def get_policy_rules() -> dict[str, list[dict[str, object]]]:
    """Get current policy rules."""
    if not policy_engine:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return {"rules": policy_engine.get_rules()}


@app.get("/audit")
async def get_audit_log(
    asset_id: str | None = None, limit: int = 100
) -> list[AuditLogEntry]:
    """Get audit log entries."""
    entries = audit_log
    if asset_id:
        entries = [e for e in entries if e.asset_id == asset_id]
    return entries[-limit:]


def run() -> None:
    """Entry point for running the service."""
    import uvicorn

    uvicorn.run(
        "skill_broker.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()
