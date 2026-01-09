"""
HTTP clients for upstream Adaptiv-X services.
"""

from __future__ import annotations

from typing import Any

import httpx


class MonitorClient:
    """Client for adaptiv-monitor service."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def assess(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post(
            f"{self._base_url}/assess",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()


class BrokerClient:
    """Client for skill-broker service."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def evaluate(self, asset_id: str, health_index: int) -> dict[str, Any]:
        response = await self._client.post(
            f"{self._base_url}/evaluate",
            json={"asset_id": asset_id, "health_index": health_index},
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()
