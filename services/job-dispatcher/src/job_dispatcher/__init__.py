"""
Job-Dispatcher: Capability-Based Production Routing

Part of Adaptiv-X: Capability-Based Self-Healing Digital Twin
"""

from job_dispatcher.bidding import Bid, BiddingService, Contract
from job_dispatcher.capability_query import CapabilityQueryService
from job_dispatcher.config import Settings
from job_dispatcher.main import app

__all__ = [
    "app",
    "Settings",
    "CapabilityQueryService",
    "BiddingService",
    "Bid",
    "Contract",
]

__version__ = "0.1.0"
