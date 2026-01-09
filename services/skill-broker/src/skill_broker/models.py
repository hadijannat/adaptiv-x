"""
Shared models for Skill-Broker.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class HealthEvent(BaseModel):
    """Health event received from adaptiv-monitor."""

    asset_id: str
    health_index: int = Field(..., ge=0, le=100)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
