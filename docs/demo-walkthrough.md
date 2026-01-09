# Demo Walkthrough

This guide walks through the Adaptiv-X "killer demo" scenario step by step.

## Prerequisites

- Docker & Docker Compose
- curl, jq (for API calls)
- ~5 minutes

## Quick Start

```bash
# 1. Start infrastructure
./scripts/bootstrap_local.sh

# 2. Seed AAS packages
./scripts/seed_aas.sh

# 3. Run the demo
./scripts/run_demo.sh
```

## Demo Scenario

### Phase 1: Initial State

Both milling machines start healthy with full capability:

```bash
# Check milling-01 health
curl -s http://localhost:4001/submodels/dXJuOmFkYXB0aXZ4OnN1Ym1vZGVsOmhlYWx0aDptaWxsaW5nLTAx | \
  jq '.submodelElements[] | select(.idShort == "HealthIndex") | .value'
# Output: "100"

# Check capability state
curl -s http://localhost:4001/submodels/dXJuOmFkYXB0aXZ4OnN1Ym1vZGVsOmNhcGFiaWxpdHk6bWlsbGluZy0wMQ | \
  jq '.submodelElements[0].value[] | select(.idShort == "AssuranceState") | .value'
# Output: "assured"
```

### Phase 2: Normal Operation

Dispatch a precision job requiring Grade A finish:

```bash
curl -X POST http://localhost:8003/dispatch \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "JOB-001",
    "description": "High-precision milling",
    "capability_requirements": {
      "surface_finish_grade": "A",
      "assurance_required": true
    }
  }'
```

**Expected**: Job assigned to `milling-01` (has assured Grade A)

### Phase 3: Fault Injection

Simulate bearing wear by injecting high vibration:

```bash
curl -X POST http://localhost:8001/assess \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": "milling-01",
    "vib_rms": 4.5,
    "omega": 150.0,
    "load": 800.0,
    "wear": 0.7
  }'
```

**Response**:
```json
{
  "health_index": 65,
  "anomaly_score": 0.78,
  "physics_residual": 0.62,
  "decision_rationale": "ML detected significant anomalies. Physics confirms wear."
}
```

### Phase 4: Capability Downgrade

The skill-broker evaluates policy and patches capability:

```bash
curl -X POST http://localhost:8002/evaluate \
  -H "Content-Type: application/json" \
  -d '{"asset_id": "milling-01", "health_index": 65}'
```

**Result**: Capability changes from:
- `SurfaceFinishGrade: A` → `C`
- `AssuranceState: assured` → `notAvailable`
- `EnergyCostPerPart_kWh: 0.85` → `1.25`

### Phase 5: Automatic Rerouting

Dispatch another precision job:

```bash
curl -X POST http://localhost:8003/dispatch \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "JOB-002",
    "capability_requirements": {
      "surface_finish_grade": "A",
      "assurance_required": true
    }
  }'
```

**Expected**: Job assigned to `milling-02`
- `milling-01` rejected (AssuranceState = notAvailable)

## VDI/VDE 2193 Bidding Mode

For advanced demo with bidding protocol:

```bash
# Create Request for Bids
curl -X POST http://localhost:8003/bid/request \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "JOB-003",
    "requirements": {"surface_finish_grade": "A", "assurance_required": true}
  }'

# Get bids
curl http://localhost:8003/bid/{rfb_id}/bids

# Award contract
curl -X POST http://localhost:8003/bid/{rfb_id}/award
```

## Key Observations

1. **Hybrid AI**: ML + Physics provides trustworthy assessment
2. **Semantic States**: `assured` → `offered` → `notAvailable`
3. **Automatic Routing**: No manual intervention needed
4. **Auditability**: All changes logged with rationale

## Troubleshooting

**Services not running?**
```bash
docker compose -f deploy/compose/docker-compose.yml ps
```

**AAS not responding?**
```bash
curl http://localhost:4001/shells
```

**Reset to initial state?**
```bash
./scripts/seed_aas.sh  # Re-upload original packages
```
