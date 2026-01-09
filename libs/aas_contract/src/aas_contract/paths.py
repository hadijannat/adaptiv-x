"""AAS identifiers and canonical idShort paths."""

from __future__ import annotations

from base64 import urlsafe_b64encode
from typing import Any

SUBMODEL_PREFIX = "urn:adaptivx:submodel"

HEALTH_ELEMENT_PATHS = {
    "health_index": "HealthIndex",
    "health_confidence": "HealthConfidence",
    "anomaly_score": "AnomalyScore",
    "physics_residual": "PhysicsResidual",
    "last_update": "LastUpdate",
    "decision_rationale": "ExplainabilityBundle.DecisionRationale",
}

CAPABILITY_ELEMENT_PATHS = {
    "assurance_state": "Capabilities/ProcessCapability:Milling/AssuranceState",
    "surface_finish": "Capabilities/ProcessCapability:Milling/SurfaceFinishGrade",
    "tolerance_class": "Capabilities/ProcessCapability:Milling/ToleranceClass",
    "energy_cost": "Capabilities/ProcessCapability:Milling/EnergyCostPerPart_kWh",
}


def encode_id(identifier: str) -> str:
    """Base64-URL encode an identifier for AAS API paths."""
    return urlsafe_b64encode(identifier.encode()).decode().rstrip("=")


def health_submodel_id(asset_id: str) -> str:
    return f"{SUBMODEL_PREFIX}:health:{asset_id}"


def capability_submodel_id(asset_id: str) -> str:
    return f"{SUBMODEL_PREFIX}:capability:{asset_id}"


def simulation_submodel_id(asset_id: str) -> str:
    return f"{SUBMODEL_PREFIX}:simulationmodels:{asset_id}"


def normalize_list(payload: Any) -> list[Any]:
    """Normalize BaSyx list responses (result/items) to a list."""
    if isinstance(payload, dict):
        result = payload.get("result")
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            items = result.get("items")
            if isinstance(items, list):
                return items
    return payload if isinstance(payload, list) else []
