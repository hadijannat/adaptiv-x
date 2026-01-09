"""
AAS Patcher for Skill-Broker.

Patches submodel elements in the BaSyx AAS Environment.
"""

from __future__ import annotations

import logging
from base64 import urlsafe_b64encode
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)


class AASPatcher:
    """Patches AAS submodel elements via BaSyx API."""

    def __init__(
        self,
        aas_environment_url: str,
        timeout: float = 30.0,
    ) -> None:
        self.aas_env_url = aas_environment_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    def _encode_id(self, identifier: str) -> str:
        """Base64-URL encode an identifier for AAS API paths."""
        return urlsafe_b64encode(identifier.encode()).decode().rstrip("=")

    def _submodel_id_for_path(self, asset_id: str, element_path: str) -> str:
        """Derive submodel ID from element path."""
        if element_path.startswith("Capabilities"):
            return f"urn:adaptivx:submodel:capability:{asset_id}"
        if element_path.startswith("Health"):
            return f"urn:adaptivx:submodel:health:{asset_id}"
        return f"urn:adaptivx:submodel:capability:{asset_id}"

    def _normalize_element_path(self, element_path: str) -> str:
        """Strip submodel idShort prefix from the element path if present."""
        if element_path.startswith("Capabilities/"):
            element_path = element_path[len("Capabilities/") :]
        elif element_path.startswith("Health/"):
            element_path = element_path[len("Health/") :]
        return element_path.replace("/", ".")

    async def _patch_submodel_element(
        self, submodel_id: str, element_path: str, value: str
    ) -> None:
        encoded_sm_id = self._encode_id(submodel_id)
        normalized_path = self._normalize_element_path(element_path)
        encoded_path = quote(normalized_path, safe="")
        url = (
            f"{self.aas_env_url}/submodels/{encoded_sm_id}"
            f"/submodel-elements/{encoded_path}/$value"
        )

        response = await self._client.patch(
            url,
            json=value,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

    async def _get_submodel_element(
        self, submodel_id: str, element_path: str
    ) -> str | None:
        encoded_sm_id = self._encode_id(submodel_id)
        normalized_path = self._normalize_element_path(element_path)
        encoded_path = quote(normalized_path, safe="")
        url = (
            f"{self.aas_env_url}/submodels/{encoded_sm_id}"
            f"/submodel-elements/{encoded_path}/$value"
        )

        response = await self._client.get(url)
        response.raise_for_status()
        return response.json()

    async def patch_element(
        self, asset_id: str, element_path: str, value: str
    ) -> None:
        """
        Patch a submodel element value.

        Args:
            asset_id: Asset identifier (e.g., "milling-01")
            element_path: Path to element
                (e.g., "Capabilities/ProcessCapability:Milling/AssuranceState")
            value: New value to set
        """
        try:
            submodel_id = self._submodel_id_for_path(asset_id, element_path)
            await self._patch_submodel_element(submodel_id, element_path, value)
            logger.debug(f"Patched {element_path} = {value}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error patching {element_path}: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Failed to patch {element_path}: {e}")
            raise

    async def get_element_value(
        self, asset_id: str, element_path: str
    ) -> str | None:
        """Get current value of a submodel element."""
        try:
            submodel_id = self._submodel_id_for_path(asset_id, element_path)
            return await self._get_submodel_element(submodel_id, element_path)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            logger.error(f"Failed to get {element_path}: {e}")
            return None

    async def get_health_index(self, asset_id: str) -> int | None:
        """Get the HealthIndex value for an asset."""
        submodel_id = f"urn:adaptivx:submodel:health:{asset_id}"
        try:
            value = await self._get_submodel_element(submodel_id, "HealthIndex")
            if value is None:
                return None
            return int(float(value))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            logger.error("Failed to get HealthIndex for %s: %s", asset_id, e)
            return None

    async def list_assets(self) -> list[str]:
        """List asset identifiers from the AAS Environment."""
        try:
            response = await self._client.get(f"{self.aas_env_url}/shells")
            response.raise_for_status()
            payload = response.json()
            shells = payload.get("result", payload)

            assets: list[str] = []
            for shell in shells:
                asset_id = shell.get("idShort") or shell.get("id")
                if isinstance(asset_id, dict):
                    asset_id = asset_id.get("id") or asset_id.get("identifier")
                if not asset_id:
                    continue
                asset_id = str(asset_id)
                if ":" in asset_id:
                    asset_id = asset_id.split(":")[-1]
                assets.append(asset_id)
            return assets
        except Exception as e:
            logger.error("Failed to list assets: %s", e)
            return []
