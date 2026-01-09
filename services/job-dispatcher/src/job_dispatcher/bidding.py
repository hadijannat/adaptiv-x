"""
VDI/VDE 2193-Inspired Bidding Service for Job-Dispatcher.

Implements a conceptual bidding process:
1. Request for Bids (RFB) - Dispatcher publishes job requirements
2. Bid - Assets respond with offers (cost, lead time, risk)
3. Award - Dispatcher selects winner and creates contract

This is a simplified demonstration inspired by VDI/VDE 2193 concepts.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from job_dispatcher.capability_query import CapabilityQueryService

logger = logging.getLogger(__name__)


class Bid(BaseModel):
    """Bid from an asset."""

    bid_id: str
    asset_id: str
    rfb_id: str
    energy_cost: float
    lead_time_minutes: int
    risk_score: float  # 0-1, lower is better
    assurance_state: str
    timestamp: datetime


class Contract(BaseModel):
    """Awarded contract."""

    contract_id: str
    rfb_id: str
    job_id: str
    awarded_to: str
    total_cost: float
    lead_time_minutes: int
    awarded_at: datetime
    rationale: str


@dataclass
class RequestForBids:
    """Request for Bids (RFB) structure."""

    rfb_id: str
    job_id: str
    requirements: dict[str, Any]
    created_at: datetime
    bids: list[Bid] = field(default_factory=list)
    status: str = "open"  # open, closed, awarded
    awarded_contract: Contract | None = None


class BiddingService:
    """
    VDI/VDE 2193-inspired bidding service.

    Message types:
    1. RFB (Request for Bids) - Published by dispatcher
    2. Bid - Response from each asset
    3. Award - Winner selection and contract creation
    """

    def __init__(self, query_service: CapabilityQueryService) -> None:
        self._query_service = query_service
        self._rfbs: dict[str, RequestForBids] = {}

    async def create_rfb(
        self,
        job_id: str,
        requirements: Any,
    ) -> dict[str, Any]:
        """
        Create a Request for Bids.

        In a real implementation, this would be published via MQTT
        and assets would respond asynchronously.
        """
        rfb_id = f"RFB-{uuid.uuid4().hex[:8]}"

        rfb = RequestForBids(
            rfb_id=rfb_id,
            job_id=job_id,
            requirements={
                "surface_finish_grade": requirements.surface_finish_grade,
                "tolerance_class": requirements.tolerance_class,
                "assurance_required": requirements.assurance_required,
            },
            created_at=datetime.now(UTC),
        )

        # Simulate immediate bid collection from all assets
        candidates = await self._query_service.get_all_candidates()

        for asset_id, capability in candidates.items():
            bid = self._generate_bid(rfb_id, asset_id, capability)
            rfb.bids.append(bid)

        self._rfbs[rfb_id] = rfb
        logger.info(f"Created RFB {rfb_id} with {len(rfb.bids)} bids")

        return {
            "rfb_id": rfb_id,
            "job_id": job_id,
            "bids": rfb.bids,
        }

    def _generate_bid(
        self, rfb_id: str, asset_id: str, capability: dict[str, Any]
    ) -> Bid:
        """Generate a bid from an asset based on its capability state."""
        assurance = str(capability.get("AssuranceState", "notAvailable"))
        energy_cost = float(capability.get("EnergyCostPerPart_kWh", 1.5))
        health = capability.get("HealthIndex", 100)

        # Compute risk based on health and assurance
        if assurance == "assured":
            risk = 0.1
        elif assurance == "offered":
            risk = 0.4
        else:
            risk = 0.8

        # Adjust risk based on health
        if health is not None:
            risk += (100 - int(health)) * 0.005

        risk = min(1.0, risk)

        # Lead time increases with degradation
        base_lead_time = 30  # minutes
        if assurance != "assured":
            base_lead_time += 15
        if health is not None and int(health) < 90:
            base_lead_time += 10

        return Bid(
            bid_id=f"BID-{uuid.uuid4().hex[:8]}",
            asset_id=asset_id,
            rfb_id=rfb_id,
            energy_cost=energy_cost,
            lead_time_minutes=base_lead_time,
            risk_score=round(risk, 2),
            assurance_state=assurance,
            timestamp=datetime.now(UTC),
        )

    async def get_bids(self, rfb_id: str) -> list[Bid]:
        """Get all bids for an RFB."""
        rfb = self._rfbs.get(rfb_id)
        if not rfb:
            return []
        return rfb.bids

    async def award_contract(self, rfb_id: str) -> Contract | None:
        """
        Award contract to best bidder.

        Selection criteria (weighted):
        1. Must have "assured" state (if required)
        2. Total score = energy_cost * (1 + risk_score)
        3. Lowest score wins
        """
        rfb = self._rfbs.get(rfb_id)
        if not rfb or rfb.status == "awarded":
            return rfb.awarded_contract if rfb else None

        # Filter to eligible bids
        eligible_bids = [
            b for b in rfb.bids
            if b.assurance_state == "assured"
        ]

        if not eligible_bids:
            # Fall back to "offered" state if no assured assets
            eligible_bids = [
                b for b in rfb.bids
                if b.assurance_state in ("assured", "offered")
            ]

        if not eligible_bids:
            return None

        # Score and select best bid
        def score_bid(bid: Bid) -> float:
            return bid.energy_cost * (1 + bid.risk_score)

        best_bid = min(eligible_bids, key=score_bid)

        # Create contract
        contract = Contract(
            contract_id=f"CONTRACT-{uuid.uuid4().hex[:8]}",
            rfb_id=rfb_id,
            job_id=rfb.job_id,
            awarded_to=best_bid.asset_id,
            total_cost=best_bid.energy_cost,
            lead_time_minutes=best_bid.lead_time_minutes,
            awarded_at=datetime.now(UTC),
            rationale=(
                f"Lowest weighted score ({score_bid(best_bid):.2f}) "
                f"with assurance={best_bid.assurance_state}"
            ),
        )

        rfb.status = "awarded"
        rfb.awarded_contract = contract

        logger.info(f"Awarded {contract.contract_id} to {contract.awarded_to}")

        return contract
