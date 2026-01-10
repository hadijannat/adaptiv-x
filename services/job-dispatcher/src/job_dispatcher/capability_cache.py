"""Capability cache for event-driven dispatching."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any


def _parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(tz=UTC)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(tz=UTC)


def _id_short_from_path(path: str) -> str:
    if "/" in path:
        return path.split("/")[-1]
    if "." in path:
        return path.split(".")[-1]
    return path


@dataclass
class CapabilityCacheEntry:
    capability: dict[str, Any]
    updated_at: datetime


@dataclass
class CapabilityCache:
    ttl_seconds: float = 300.0
    _store: dict[str, CapabilityCacheEntry] = field(default_factory=dict)

    def update(
        self,
        asset_id: str,
        capability: dict[str, Any],
        timestamp: str | None,
    ) -> None:
        updated_at = _parse_timestamp(timestamp)
        self._store[asset_id] = CapabilityCacheEntry(
            capability=capability,
            updated_at=updated_at,
        )

    def apply_changes(
        self,
        asset_id: str,
        changes: list[dict[str, str]],
        timestamp: str | None,
    ) -> None:
        updated_at = _parse_timestamp(timestamp)
        entry = self._store.get(asset_id)
        capability = dict(entry.capability) if entry else {}
        for change in changes:
            path = change.get("path", "")
            value = change.get("value")
            if value is None:
                continue
            id_short = _id_short_from_path(path)
            capability[id_short] = value
        self._store[asset_id] = CapabilityCacheEntry(
            capability=capability,
            updated_at=updated_at,
        )

    def update_from_event(self, payload: dict[str, Any]) -> None:
        asset_id = payload.get("asset_id")
        if not asset_id:
            return
        timestamp = payload.get("timestamp")
        capability = payload.get("capability")
        changes = payload.get("changes")
        if isinstance(capability, dict):
            self.update(str(asset_id), capability, timestamp)
            return
        if isinstance(changes, list):
            self.apply_changes(str(asset_id), changes, timestamp)

    def snapshot(self) -> dict[str, dict[str, Any]]:
        now = datetime.now(tz=UTC)
        ttl = timedelta(seconds=self.ttl_seconds)
        result: dict[str, dict[str, Any]] = {}
        for asset_id, entry in list(self._store.items()):
            if now - entry.updated_at > ttl:
                continue
            result[asset_id] = entry.capability
        return result
