"""Pydantic models for shared AAS payloads."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthPayload(BaseModel):
    health_index: int = Field(..., ge=0, le=100)
    health_confidence: float = Field(..., ge=0, le=1)
    anomaly_score: float = Field(..., ge=0, le=1)
    physics_residual: float = Field(..., ge=0, le=1)
    decision_rationale: str | None = None
    detected_pattern: str | None = None
    fusion_method: str | None = None
    confidence_interval: str | None = None
    fmu_residual: float | None = None
    model_version: str | None = None
    fmu_version: str | None = None


class CapabilityPayload(BaseModel):
    assurance_state: str
    surface_finish_grade: str | None = None
    tolerance_class: str | None = None
    energy_cost_per_part_kwh: float | None = None
    carbon_footprint_g_per_part: float | None = None


class SimulationModelReference(BaseModel):
    url: str
    content_type: str | None = None
    model_version: str | None = None
