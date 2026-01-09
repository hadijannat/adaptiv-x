"""
Capability Query Service for Job-Dispatcher.

Queries AAS Registry and retrieves capability states from assets.
"""

from __future__ import annotations

import asyncio
import logging
from base64 import urlsafe_b64encode
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class CapabilityQueryService:
    """Queries AAS infrastructure for asset capabilities."""

    def __init__(
        self,
        aas_registry_url: str,
        aas_environment_url: str,
        timeout: float = 30.0,
    ) -> None:
        self.registry_url = aas_registry_url.rstrip("/")
        self.env_url = aas_environment_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    def _encode_id(self, identifier: str) -> str:
        """Base64-URL encode an identifier."""
        return urlsafe_b64encode(identifier.encode()).decode().rstrip("=")

    def _extract_asset_id(self, entry: dict[str, Any]) -> str | None:
        asset_id = entry.get("idShort") or entry.get("id")
        if isinstance(asset_id, dict):
            asset_id = asset_id.get("id") or asset_id.get("identifier")
        if not asset_id:
            return None
        asset_id = str(asset_id)
        return asset_id.split(":")[-1] if ":" in asset_id else asset_id

    async def list_assets(self) -> list[str]:
        """List assets from registry, falling back to AAS Environment."""
        assets = await self._fetch_assets_from_registry()
        if assets:
            return list(dict.fromkeys(assets))
        return await self._fetch_assets_from_environment()

    async def _fetch_assets_from_registry(self) -> list[str]:
        try:
            response = await self._client.get(f"{self.registry_url}/shell-descriptors")
            response.raise_for_status()
            payload = response.json()
            descriptors = payload.get("result", payload)
            assets = [
                asset_id
                for entry in descriptors
                if (asset_id := self._extract_asset_id(entry))
            ]
            return list(dict.fromkeys(assets))
        except Exception as e:
            logger.debug(f"Registry asset discovery failed: {e}")
            return []

    async def _fetch_assets_from_environment(self) -> list[str]:
        try:
            response = await self._client.get(f"{self.env_url}/shells")
            response.raise_for_status()
            payload = response.json()
            shells = payload.get("result", payload)
            assets = [
                asset_id
                for entry in shells
                if (asset_id := self._extract_asset_id(entry))
            ]
            return assets
        except Exception as e:
            logger.debug(f"Environment asset discovery failed: {e}")
            return []

    async def get_all_candidates(self) -> dict[str, dict[str, Any]]:
        """
        Get all milling machine candidates with their capability states.

        Returns:
            Dict mapping asset_id to capability properties
        """
        result: dict[str, dict[str, Any]] = {}

        assets = await self.list_assets()
        if not assets:
            logger.warning("No assets discovered from registry or environment")
            return result

        results = await asyncio.gather(
            *[self._fetch_candidate(asset_id) for asset_id in assets],
            return_exceptions=True,
        )

        for item in results:
            if isinstance(item, BaseException):
                logger.warning("Candidate fetch failed: %s", item)
                continue
            asset_id, capability = item
            if capability is None:
                continue
            result[asset_id] = capability

        return result

    async def _fetch_candidate(
        self, asset_id: str
    ) -> tuple[str, dict[str, Any] | None]:
        capability = await self.get_capability_state(asset_id)
        if not capability:
            return asset_id, None
        health = await self.get_health_index(asset_id)
        capability["HealthIndex"] = health
        return asset_id, capability

    async def get_capability_state(self, asset_id: str) -> dict[str, Any] | None:
        """Get capability state for a specific asset."""
        submodel_id = f"urn:adaptivx:submodel:capability:{asset_id}"
        encoded_id = self._encode_id(submodel_id)

        try:
            response = await self._client.get(
                f"{self.env_url}/submodels/{encoded_id}",
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            submodel = response.json()

            # Extract capability properties
            result: dict[str, Any] = {}
            for element in submodel.get("submodelElements", []):
                if element.get("idShort", "").startswith("ProcessCapability:"):
                    for prop in element.get("value", []):
                        id_short = prop.get("idShort", "")
                        if "value" in prop:
                            result[id_short] = prop["value"]

            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug(f"Capability submodel not found for {asset_id}")
                return None
            raise
        except Exception as e:
            logger.error(f"Failed to get capability for {asset_id}: {e}")
            return None

    async def get_health_index(self, asset_id: str) -> int | None:
        """Get current health index for an asset."""
        submodel_id = f"urn:adaptivx:submodel:health:{asset_id}"
        encoded_id = self._encode_id(submodel_id)

        try:
            response = await self._client.get(
                f"{self.env_url}/submodels/{encoded_id}",
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            submodel = response.json()

            for element in submodel.get("submodelElements", []):
                if element.get("idShort") == "HealthIndex":
                    return int(element.get("value", 100))

            return None

        except Exception as e:
            logger.debug(f"Failed to get health for {asset_id}: {e}")
            return None
