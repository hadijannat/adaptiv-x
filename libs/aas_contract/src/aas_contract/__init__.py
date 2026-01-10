"""
Shared AAS contract definitions for Adaptiv-X.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import CapabilityPayload, HealthPayload, SimulationModelReference
else:
    try:  # Optional at runtime for repo-level tests without deps
        from .models import CapabilityPayload, HealthPayload, SimulationModelReference
    except ModuleNotFoundError:
        CapabilityPayload = HealthPayload = SimulationModelReference = None  # type: ignore[assignment]
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

__version__ = "0.2.0"

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
