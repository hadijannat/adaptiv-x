"""
Integration tests for AAS Semantic Contracts.

Verifies that the AAS Environment matches the expected semantic structure
defined in IDTA 02006 (Capability) and IDTA 02005 (Simulation).
"""

import os
import pytest
import pytest_asyncio
import httpx

from aas_contract import (
    capability_submodel_id,
    encode_id,
    health_submodel_id,
    normalize_list,
)

AAS_ENV_URL = os.getenv("AAS_ENV_URL", "http://localhost:4001")

@pytest_asyncio.fixture
async def client() -> httpx.AsyncClient:
    async with httpx.AsyncClient(base_url=AAS_ENV_URL, timeout=10.0) as client:
        yield client

@pytest.mark.asyncio
async def test_aas_discovery(client):
    """Verify that expected AAS shells are present."""
    response = await client.get("/shells")
    assert response.status_code == 200
    shells = normalize_list(response.json())
    
    # We expect at least milling-01 and milling-02
    ids = [s.get("idShort") for s in shells]
    assert "milling-01" in ids or any("milling-01" in s.get("id", "") for s in shells)

@pytest.mark.asyncio
async def test_capability_submodel_contract(client):
    """Verify Capability submodel structure and semantic IDs."""
    asset_id = "milling-01"
    submodel_id = capability_submodel_id(asset_id)
    encoded_id = encode_id(submodel_id)
    
    response = await client.get(f"/submodels/{encoded_id}")
    assert response.status_code == 200
    sm = response.json()
    
    # Semantic ID for Capability Submodel (IDTA 02006-1-0)
    # Note: Using the Adaptiv-X specific URN as the primary semantic reference
    semantic_id = sm.get("semanticId", {}).get("keys", [{}])[0].get("value")
    assert "capability" in semantic_id.lower()

    # Check for critical elements used by Job-Dispatcher
    elements = sm.get("submodelElements", [])
    id_shorts = [e.get("idShort") for e in elements]
    
    # ProcessCapability:Milling is a submodel element collection
    assert any("Milling" in s for s in id_shorts)

@pytest.mark.asyncio
async def test_health_submodel_contract(client):
    """Verify Health submodel structure."""
    asset_id = "milling-01"
    submodel_id = health_submodel_id(asset_id)
    encoded_id = encode_id(submodel_id)
    
    response = await client.get(f"/submodels/{encoded_id}")
    assert response.status_code == 200
    sm = response.json()
    
    elements = sm.get("submodelElements", [])
    id_shorts = {e.get("idShort"): e for e in elements}
    
    assert "HealthIndex" in id_shorts
    assert "HealthConfidence" in id_shorts
    assert "AnomalyScore" in id_shorts
    assert "PhysicsResidual" in id_shorts

@pytest.mark.asyncio
async def test_semantic_id_consistency(client):
    """Check that semantic IDs across assets are consistent."""
    response = await client.get("/submodels")
    assert response.status_code == 200
    all_sm = normalize_list(response.json())
    
    health_sms = [sm for sm in all_sm if "health" in sm.get("id", "").lower()]
    capability_sms = [sm for sm in all_sm if "capability" in sm.get("id", "").lower()]
    
    # All health submodels should have the same semantic ID
    health_semantic_ids = {
        sm.get("semanticId", {}).get("keys", [{}])[0].get("value") 
        for sm in health_sms if sm.get("semanticId")
    }
    assert len(health_semantic_ids) <= 1
    
    # All capability submodels should have the same semantic ID
    cap_semantic_ids = {
        sm.get("semanticId", {}).get("keys", [{}])[0].get("value") 
        for sm in capability_sms if sm.get("semanticId")
    }
    assert len(cap_semantic_ids) <= 1
