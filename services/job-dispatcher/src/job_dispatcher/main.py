"""
Job-Dispatcher: Capability-Based Production Routing

This service implements production job routing for Adaptiv-X:
1. Receives job requests with capability requirements
2. Queries AAS Registry for candidate assets
3. Evaluates capability state from each asset
4. Routes jobs to assets with "assured" capability
5. Optional: VDI/VDE 2193-inspired bidding protocol

Part of Adaptiv-X: Capability-Based Self-Healing Digital Twin
"""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from enum import Enum

from aas_contract import (
    CAPABILITY_ELEMENT_PATHS,
    HEALTH_ELEMENT_PATHS,
    SUBMODEL_PREFIX,
)
from aas_contract import (
    __version__ as contract_version,
)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from job_dispatcher.bidding import Bid, BiddingService, Contract
from job_dispatcher.capability_query import CapabilityQueryService
from job_dispatcher.config import Settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
settings = Settings()
query_service: CapabilityQueryService | None = None
bidding_service: BiddingService | None = None


# ============================================================================
# Pydantic Models
# ============================================================================


class JobPriority(str, Enum):
    """Job priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class CapabilityRequirement(BaseModel):
    """Required capability specification."""

    surface_finish_grade: str = Field(default="A", description="Required surface finish (A, B, C)")
    tolerance_class: str = Field(default="±0.02mm", description="Required tolerance")
    assurance_required: bool = Field(default=True, description="Require 'assured' state")


class JobRequest(BaseModel):
    """Production job request."""

    job_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = Field(default="Precision milling job")
    capability_requirements: CapabilityRequirement = Field(default_factory=CapabilityRequirement)
    priority: JobPriority = Field(default=JobPriority.NORMAL)
    quantity: int = Field(default=1, ge=1)


class AssetCandidate(BaseModel):
    """Candidate asset for job assignment."""

    asset_id: str
    surface_finish_grade: str
    tolerance_class: str
    assurance_state: str
    energy_cost_per_part: float
    health_index: int | None = None
    eligible: bool
    rejection_reason: str | None = None


class JobAssignment(BaseModel):
    """Result of job dispatch."""

    job_id: str
    assigned_asset: str | None
    candidates_evaluated: int
    selection_reason: str
    timestamp: datetime
    candidates: list[AssetCandidate]


class BidRequest(BaseModel):
    """VDI/VDE 2193-inspired bid request."""

    job_id: str
    requirements: CapabilityRequirement
    deadline: datetime | None = None


# In-memory job history
job_history: list[JobAssignment] = []


# ============================================================================
# FastAPI Application
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan for startup/shutdown."""
    global query_service, bidding_service

    logger.info("Starting Job-Dispatcher service...")

    query_service = CapabilityQueryService(
        aas_registry_url=settings.aas_registry_url,
        aas_environment_url=settings.aas_environment_url,
    )

    bidding_service = BiddingService(query_service)

    logger.info("Job-Dispatcher service started successfully")

    yield

    logger.info("Shutting down Job-Dispatcher service...")
    if query_service:
        await query_service.close()


app = FastAPI(
    title="Job-Dispatcher",
    description="Capability-Based Production Routing with VDI/VDE 2193 Bidding",
    version="0.1.0",
    lifespan=lifespan,
)


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Service health check endpoint."""
    return {"status": "healthy", "service": "job-dispatcher"}


@app.get("/debug/contract")
async def debug_contract() -> dict[str, object]:
    """Expose shared AAS contract paths for verification."""
    return {
        "service": "job-dispatcher",
        "contract_version": contract_version,
        "submodel_prefix": SUBMODEL_PREFIX,
        "health_paths": HEALTH_ELEMENT_PATHS,
        "capability_paths": CAPABILITY_ELEMENT_PATHS,
    }


@app.post("/dispatch", response_model=JobAssignment)
async def dispatch_job(request: JobRequest) -> JobAssignment:
    """
    Dispatch a job to the best available asset.

    Algorithm:
    1. Query AAS Registry for all milling assets
    2. For each asset, retrieve capability state
    3. Filter by requirements (grade, tolerance, assurance)
    4. Select asset with lowest energy cost
    """
    if not query_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    logger.info(f"Dispatching job: {request.job_id} ({request.description})")

    # Get all candidates with their capability state
    candidates = await query_service.get_all_candidates()

    # Evaluate each candidate against requirements
    evaluated: list[AssetCandidate] = []
    eligible_assets: list[AssetCandidate] = []

    for asset_id, capability in candidates.items():
        candidate = _evaluate_candidate(asset_id, capability, request.capability_requirements)
        evaluated.append(candidate)
        if candidate.eligible:
            eligible_assets.append(candidate)

    # Select best asset (lowest energy cost)
    if eligible_assets:
        selected = min(eligible_assets, key=lambda a: a.energy_cost_per_part)
        assignment = JobAssignment(
            job_id=request.job_id,
            assigned_asset=selected.asset_id,
            candidates_evaluated=len(evaluated),
            selection_reason=(
                f"Lowest energy cost ({selected.energy_cost_per_part} kWh) "
                f"among {len(eligible_assets)} eligible assets"
            ),
            timestamp=datetime.now(tz=UTC),
            candidates=evaluated,
        )
    else:
        assignment = JobAssignment(
            job_id=request.job_id,
            assigned_asset=None,
            candidates_evaluated=len(evaluated),
            selection_reason="No eligible assets found matching requirements",
            timestamp=datetime.now(tz=UTC),
            candidates=evaluated,
        )

    job_history.append(assignment)
    logger.info(f"Job {request.job_id} assigned to: {assignment.assigned_asset}")

    return assignment


@app.post("/bid/request")
async def create_bid_request(request: BidRequest) -> dict[str, object]:
    """
    Create a VDI/VDE 2193-inspired Request for Bids (RFB).

    This initiates the bidding process for a job.
    """
    if not bidding_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    rfb = await bidding_service.create_rfb(
        job_id=request.job_id,
        requirements=request.requirements,
    )

    return {
        "rfb_id": rfb["rfb_id"],
        "job_id": request.job_id,
        "status": "open",
        "bids_received": len(rfb.get("bids", [])),
        "message": "RFB created, assets may submit bids",
    }


@app.get("/bid/{rfb_id}/bids")
async def get_bids(rfb_id: str) -> list[Bid]:
    """Get all bids for a Request for Bids."""
    if not bidding_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return await bidding_service.get_bids(rfb_id)


@app.post("/bid/{rfb_id}/award")
async def award_contract(rfb_id: str) -> Contract:
    """
    Award contract to the best bidder.

    Selection criteria:
    1. Must meet capability requirements
    2. Lowest total cost (energy + risk)
    3. Fastest lead time as tiebreaker
    """
    if not bidding_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    contract = await bidding_service.award_contract(rfb_id)
    if not contract:
        raise HTTPException(status_code=404, detail="No valid bids found")

    return contract


@app.get("/candidates")
async def list_candidates() -> list[AssetCandidate]:
    """List all available asset candidates with their capability states."""
    if not query_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    candidates = await query_service.get_all_candidates()

    # Default requirements for display
    requirements = CapabilityRequirement()

    return [
        _evaluate_candidate(asset_id, capability, requirements)
        for asset_id, capability in candidates.items()
    ]


@app.get("/history")
async def get_job_history(limit: int = 20) -> list[JobAssignment]:
    """Get recent job assignment history."""
    return job_history[-limit:]


# ============================================================================
# Helper Functions
# ============================================================================


def _evaluate_candidate(
    asset_id: str,
    capability: dict[str, object],
    requirements: CapabilityRequirement,
) -> AssetCandidate:
    """Evaluate if an asset meets job requirements."""
    surface_grade = str(
        capability.get(CAPABILITY_ELEMENT_PATHS["surface_finish"].split("/")[-1], "C")
    )
    tolerance = str(
        capability.get(
            CAPABILITY_ELEMENT_PATHS["tolerance_class"].split("/")[-1], "±0.1mm"
        )
    )
    assurance = str(
        capability.get(
            CAPABILITY_ELEMENT_PATHS["assurance_state"].split("/")[-1], "notAvailable"
        )
    )
    energy_cost = _coerce_float(
        capability.get(CAPABILITY_ELEMENT_PATHS["energy_cost"].split("/")[-1], 999.0),
        999.0,
    )
    health = _coerce_int(
        capability.get(HEALTH_ELEMENT_PATHS["health_index"].split(".")[-1])
    )

    rejection_reasons: list[str] = []

    # Check surface finish grade
    grade_order = {"A": 1, "B": 2, "C": 3}
    if grade_order.get(surface_grade, 99) > grade_order.get(requirements.surface_finish_grade, 1):
        rejection_reasons.append(
            f"Surface grade {surface_grade} < required {requirements.surface_finish_grade}"
        )

    # Check assurance state
    if requirements.assurance_required and assurance != "assured":
        rejection_reasons.append(f"Assurance state '{assurance}' != 'assured'")

    # Check tolerance (lower is better)
    if requirements.tolerance_class and tolerance != requirements.tolerance_class:
        required_tol = _parse_tolerance_mm(requirements.tolerance_class)
        candidate_tol = _parse_tolerance_mm(tolerance)
        if (
            required_tol is not None
            and candidate_tol is not None
            and candidate_tol > required_tol
        ):
            rejection_reasons.append(
                f"Tolerance {tolerance} > required {requirements.tolerance_class}"
            )

    eligible = len(rejection_reasons) == 0

    return AssetCandidate(
        asset_id=asset_id,
        surface_finish_grade=surface_grade,
        tolerance_class=tolerance,
        assurance_state=assurance,
        energy_cost_per_part=energy_cost,
        health_index=health,
        eligible=eligible,
        rejection_reason="; ".join(rejection_reasons) if rejection_reasons else None,
    )


def _coerce_float(value: object, default: float) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return None
    return None


def _parse_tolerance_mm(value: str) -> float | None:
    """
    Parse tolerance strings like "±0.02mm" into millimeters.
    Returns None if parsing fails.
    """
    value = value.strip().lower()
    match = re.search(r"([0-9]*\\.?[0-9]+)", value)
    if not match:
        return None

    magnitude = float(match.group(1))
    if "um" in value or "µm" in value:
        return magnitude / 1000.0
    if "cm" in value:
        return magnitude * 10.0
    return magnitude


def run() -> None:
    """Entry point for running the service."""
    import uvicorn

    uvicorn.run(
        "job_dispatcher.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()
