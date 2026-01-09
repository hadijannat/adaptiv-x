"""
Shared AAS contract definitions for Adaptiv-X.
"""

from __future__ import annotations

from .models import CapabilityPayload, HealthPayload, SimulationModelReference
from .paths import (
    CAPABILITY_ELEMENT_PATHS,
    HEALTH_ELEMENT_PATHS,
    SUBMODEL_PREFIX,
    capability_submodel_id,
    encode_id,
    health_submodel_id,
    normalize_list,
    simulation_submodel_id,
)

__version__ = "0.1.0"

__all__ = [
    "CAPABILITY_ELEMENT_PATHS",
    "HEALTH_ELEMENT_PATHS",
    "SUBMODEL_PREFIX",
    "CapabilityPayload",
    "HealthPayload",
    "SimulationModelReference",
    "capability_submodel_id",
    "encode_id",
    "health_submodel_id",
    "normalize_list",
    "simulation_submodel_id",
]
