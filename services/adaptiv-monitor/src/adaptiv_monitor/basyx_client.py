"""
BaSyx AAS Client for Adaptiv-Monitor.

Provides methods for:
- Discovering submodel endpoints via registries
- Reading submodel data
- Patching submodel elements by path
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx
from aas_contract import (
    HEALTH_ELEMENT_PATHS,
    capability_submodel_id,
    encode_id,
    health_submodel_id,
    simulation_submodel_id,
)

logger = logging.getLogger(__name__)


class BasyxClient:
    """HTTP client for BaSyx AAS infrastructure."""

    def __init__(
        self,
        aas_environment_url: str,
        aas_registry_url: str,
        submodel_registry_url: str,
        timeout: float = 30.0,
    ) -> None:
        self.aas_env_url = aas_environment_url.rstrip("/")
        self.aas_registry_url = aas_registry_url.rstrip("/")
        self.sm_registry_url = submodel_registry_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    # ========================================================================
    # Health Submodel Operations
    # ========================================================================

    async def get_health_submodel(self, asset_id: str) -> dict[str, Any] | None:
        """Get current health submodel values for an asset."""
        submodel_id = health_submodel_id(asset_id)
        encoded_id = encode_id(submodel_id)

        try:
            response = await self._client.get(
                f"{self.aas_env_url}/submodels/{encoded_id}",
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            submodel = response.json()

            # Extract values from submodel elements
            result: dict[str, Any] = {}
            for element in submodel.get("submodelElements", []):
                id_short = element.get("idShort", "")
                if "value" in element:
                    result[id_short] = element["value"]
                elif element.get("modelType") == "SubmodelElementCollection":
                    for sub_elem in element.get("value", []):
                        sub_id = sub_elem.get("idShort")
                        if not sub_id:
                            continue
                        if "value" in sub_elem:
                            result[sub_id] = sub_elem.get("value", "")

            return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            logger.error(f"Failed to get health submodel: {e}")
            raise

    async def update_health_submodel(
        self,
        asset_id: str,
        health_index: int,
        health_confidence: float,
        anomaly_score: float,
        physics_residual: float,
        rationale: str,
        detected_pattern: str | None = None,
        fusion_method: str | None = None,
        confidence_interval: str | None = None,
        fmu_residual: float | None = None,
        model_version: str | None = None,
        fmu_version: str | None = None,
    ) -> None:
        """Update health submodel values for an asset."""
        submodel_id = health_submodel_id(asset_id)
        encoded_sm_id = encode_id(submodel_id)

        # Update each property via PATCH
        updates = [
            (HEALTH_ELEMENT_PATHS["health_index"], str(health_index)),
            (HEALTH_ELEMENT_PATHS["health_confidence"], str(health_confidence)),
            (HEALTH_ELEMENT_PATHS["anomaly_score"], str(anomaly_score)),
            (HEALTH_ELEMENT_PATHS["physics_residual"], str(physics_residual)),
            (HEALTH_ELEMENT_PATHS["last_update"], datetime.now(UTC).isoformat()),
        ]

        for id_short, value in updates:
            await self._patch_property(encoded_sm_id, id_short, value)

        # Update explainability bundle
        fmu_residual_value = None if fmu_residual is None else str(fmu_residual)
        explainability_updates: dict[str, str | None] = {
            HEALTH_ELEMENT_PATHS["decision_rationale"]: rationale,
            HEALTH_ELEMENT_PATHS["detected_pattern"]: detected_pattern,
            HEALTH_ELEMENT_PATHS["fusion_method"]: fusion_method,
            HEALTH_ELEMENT_PATHS["confidence_interval"]: confidence_interval,
            HEALTH_ELEMENT_PATHS["fmu_residual"]: fmu_residual_value,
            HEALTH_ELEMENT_PATHS["model_version"]: model_version,
            HEALTH_ELEMENT_PATHS["fmu_version"]: fmu_version,
        }

        for id_short, explain_value in explainability_updates.items():
            if explain_value is None:
                continue
            await self._patch_property(encoded_sm_id, id_short, str(explain_value))

    async def _patch_property(
        self, encoded_sm_id: str, id_short_path: str, value: str
    ) -> None:
        """Patch a single property value by idShort path."""
        try:
            path = quote(id_short_path, safe="")
            response = await self._client.patch(
                f"{self.aas_env_url}/submodels/{encoded_sm_id}/submodel-elements/{path}/$value",
                json=value,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
        except Exception as e:
            logger.warning(f"Failed to patch {id_short_path}: {e}")

    # ========================================================================
    # SimulationModels Submodel Operations
    # ========================================================================

    async def get_fmu_url(self, asset_id: str) -> str | None:
        """Get the FMU download URL from SimulationModels submodel."""
        submodel_id = simulation_submodel_id(asset_id)
        encoded_id = encode_id(submodel_id)

        try:
            response = await self._client.get(
                f"{self.aas_env_url}/submodels/{encoded_id}",
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            submodel = response.json()

            # Navigate: SimulationModel:BearingWear -> ModelFile -> ModelFileVersion -> DigitalFile
            for element in submodel.get("submodelElements", []):
                if element.get("idShort", "").startswith("SimulationModel:"):
                    for sub1 in element.get("value", []):
                        if sub1.get("idShort") == "ModelFile":
                            for sub2 in sub1.get("value", []):
                                if sub2.get("idShort") == "ModelFileVersion":
                                    for sub3 in sub2.get("value", []):
                                        if sub3.get("idShort") == "DigitalFile":
                                            value = sub3.get("value")
                                            if value is None:
                                                return None
                                            return value if isinstance(value, str) else str(value)

            return None
        except Exception as e:
            logger.error(f"Failed to get FMU URL: {e}")
            return None

    # ========================================================================
    # Capability Submodel Operations
    # ========================================================================

    async def get_capability_state(self, asset_id: str) -> dict[str, Any] | None:
        """Get current capability state for an asset."""
        submodel_id = capability_submodel_id(asset_id)
        encoded_id = encode_id(submodel_id)

        try:
            response = await self._client.get(
                f"{self.aas_env_url}/submodels/{encoded_id}",
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            submodel = response.json()

            result: dict[str, Any] = {}
            for element in submodel.get("submodelElements", []):
                if element.get("idShort", "").startswith("ProcessCapability:"):
                    for prop in element.get("value", []):
                        id_short = prop.get("idShort", "")
                        if "value" in prop:
                            result[id_short] = prop["value"]

            return result
        except Exception as e:
            logger.error(f"Failed to get capability state: {e}")
            return None
