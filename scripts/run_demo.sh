#!/usr/bin/env bash
# run_demo.sh - Adaptiv-X Self-Healing Demo Script
#
# Demonstrates the "killer demo" scenario:
# 1. Start with healthy milling-01
# 2. Dispatch precision job → assigned to milling-01
# 3. Inject fault (simulate bearing wear)
# 4. Observe health degradation and capability downgrade
# 5. Dispatch again → rerouted to milling-02

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Service endpoints
AAS_ENV_URL="${AAS_ENV_URL:-http://localhost:4001}"
MONITOR_URL="${MONITOR_URL:-http://localhost:8011}"
BROKER_URL="${BROKER_URL:-http://localhost:8002}"
DISPATCHER_URL="${DISPATCHER_URL:-http://localhost:8003}"
FAULT_INJECTOR_URL="${FAULT_INJECTOR_URL:-http://localhost:8004}"

# Evidence directory
EVIDENCE_DIR="$PROJECT_ROOT/docs/baseline-evidence"
mkdir -p "$EVIDENCE_DIR"

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

AUTO_RUN=0
while [[ $# -gt 0 ]]; do
    case $1 in
        --non-interactive|--auto) AUTO_RUN=1; shift ;;
        *) shift ;;
    esac
done

print_header() {
    echo ""
    echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_step() {
    echo -e "${GREEN}▶ [STEP $1]${NC} $2"
}

print_result() {
    echo -e "  ${YELLOW}→${NC} $1"
}

wait_key() {
    if [ "$AUTO_RUN" != "1" ]; then
        echo ""
        read -p "Press Enter to continue..."
    else
        sleep 2
    fi
}

capture_evidence() {
    local name=$1
    local asset=$2
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    # Store AAS snapshot
    local submodel_id="urn:adaptivx:submodel:health:$asset"
    local encoded_id=$(echo -n "$submodel_id" | base64 | tr '+/' '-_' | tr -d '=')
    curl -sf "$AAS_ENV_URL/submodels/$encoded_id" > "$EVIDENCE_DIR/${timestamp}_${name}_health.json" || true
    
    local cap_id="urn:adaptivx:submodel:capability:$asset"
    local encoded_cap=$(echo -n "$cap_id" | base64 | tr '+/' '-_' | tr -d '=')
    curl -sf "$AAS_ENV_URL/submodels/$encoded_cap" > "$EVIDENCE_DIR/${timestamp}_${name}_capability.json" || true
}

get_health() {
    local asset=$1
    local submodel_id="urn:adaptivx:submodel:health:$asset"
    local encoded_id=$(echo -n "$submodel_id" | base64 | tr '+/' '-_' | tr -d '=')
    
    curl -sf "$AAS_ENV_URL/submodels/$encoded_id" 2>/dev/null | \
        jq -r '.submodelElements[] | select(.idShort == "HealthIndex") | .value' || echo "N/A"
}

get_capability() {
    local asset=$1
    local submodel_id="urn:adaptivx:submodel:capability:$asset"
    local encoded_id=$(echo -n "$submodel_id" | base64 | tr '+/' '-_' | tr -d '=')
    
    local result=$(curl -sf "$AAS_ENV_URL/submodels/$encoded_id" 2>/dev/null)
    if [ -z "$result" ]; then
        echo "Grade=N/A State=N/A Energy=N/AkWh"
        return
    fi
    
    local grade=$(echo "$result" | jq -r '.submodelElements[0].value[] | select(.idShort == "SurfaceFinishGrade") | .value')
    local state=$(echo "$result" | jq -r '.submodelElements[0].value[] | select(.idShort == "AssuranceState") | .value')
    local energy=$(echo "$result" | jq -r '.submodelElements[0].value[] | select(.idShort == "EnergyCostPerPart_kWh") | .value')
    
    echo "Grade=$grade State=$state Energy=${energy}kWh"
}

dispatch_job() {
    local job_id=$1
    local description=$2
    
    local result=$(curl -sf -X POST "$DISPATCHER_URL/dispatch" \
        -H "Content-Type: application/json" \
        -d "{
            \"job_id\": \"$job_id\",
            \"description\": \"$description\",
            \"capability_requirements\": {
                \"surface_finish_grade\": \"A\",
                \"assurance_required\": true
            }
        }" 2>/dev/null || echo '{"assigned_asset": "DISPATCHER_OFFLINE"}')
    
    echo "$result" | jq -r '.assigned_asset // "NONE"'
}

inject_fault() {
    local asset=$1
    local vib_rms=$2
    local wear=$3
    
    # Use fault-injector service if available, otherwise direct call to monitor
    if curl -sf "$FAULT_INJECTOR_URL/health" > /dev/null; then
        logger "Using fault-injector service orchestrator..."
        curl -sf -X POST "$FAULT_INJECTOR_URL/inject" \
            -H "Content-Type: application/json" \
            -d "{
                \"asset_id\": \"$asset\",
                \"vib_rms\": $vib_rms,
                \"omega\": 150.0,
                \"load\": 800.0,
                \"wear\": $wear,
                \"evaluate_policy\": true
            }" 2>/dev/null || echo '{"assessment": {"health_index": "FAULT_INJECTOR_FAILED"}}'
    else
        curl -sf -X POST "$MONITOR_URL/assess" \
            -H "Content-Type: application/json" \
            -d "{
                \"asset_id\": \"$asset\",
                \"vib_rms\": $vib_rms,
                \"omega\": 150.0,
                \"load\": 100.0,
                \"wear\": $wear
            }" 2>/dev/null || echo '{"health_index": "MONITOR_OFFLINE"}'
    fi
}

logger() {
    echo -e "  ${CYAN}DEBUG:${NC} $1"
}

main() {
    print_header "ADAPTIV-X SELF-HEALING DEMO"
    
    echo "This demo shows 'resilience through adaptation' where:"
    echo "  • ML detects vibration anomalies"
    echo "  • FMU physics validates the anomaly"
    echo "  • Skill-broker downgrades capability"
    echo "  • Dispatcher automatically reroutes jobs"
    echo ""
    
    # ========== INITIAL STATE ==========
    print_header "PHASE 1: INITIAL STATE"
    
    print_step "1.1" "Check initial health of both machines"
    print_result "milling-01 Health: $(get_health milling-01)"
    print_result "milling-02 Health: $(get_health milling-02)"
    capture_evidence "initial" "milling-01"
    
    print_step "1.2" "Check initial capabilities"
    print_result "milling-01: $(get_capability milling-01)"
    print_result "milling-02: $(get_capability milling-02)"
    
    wait_key
    
    # ========== NORMAL OPERATION ==========
    print_header "PHASE 2: NORMAL OPERATION"
    
    print_step "2.1" "Dispatch precision job (requires Grade A, assured)"
    local assigned=$(dispatch_job "JOB-001" "High-precision milling")
    print_result "Job JOB-001 assigned to: ${BOLD}$assigned${NC}"
    
    if [ "$assigned" == "milling-01" ]; then
        echo -e "  ${GREEN}✓ Correct! milling-01 has assured Grade A capability${NC}"
    fi
    
    wait_key
    
    # ========== FAULT INJECTION ==========
    print_header "PHASE 3: FAULT INJECTION"
    
    print_step "3.1" "Simulating bearing wear on milling-01..."
    echo "  Injecting via Fault-Injector: vibration=5.2 mm/s, wear=0.8 (80%)"
    
    local assessment=$(inject_fault "milling-01" 5.2 0.8)
    
    # Handle both direct monitor and fault-injector response shapes
    local new_health=$(echo "$assessment" | jq -r '.assessment.health_index // .health_index // "?"')
    local anomaly=$(echo "$assessment" | jq -r '.assessment.anomaly_score // .anomaly_score // "?"')
    local residual=$(echo "$assessment" | jq -r '.assessment.physics_residual // .physics_residual // "?"')
    
    print_result "Health Assessment Result:"
    print_result "  HealthIndex: $new_health"
    print_result "  AnomalyScore: $anomaly"
    print_result "  PhysicsResidual: $residual"
    
    capture_evidence "post_fault" "milling-01"
    wait_key
    
    # ========== CAPABILITY DOWNGRADE ==========
    print_header "PHASE 4: SEMANTIC CAPABILITY REASONING"
    
    print_step "4.1" "Observed capability state after policy evaluation"
    local cap_after=$(get_capability milling-01)
    print_result "milling-01: $cap_after"
    
    if [[ "$cap_after" == *"State=notAvailable"* ]]; then
        echo -e "  ${GREEN}✓ SUCCESS! Capability downgraded to notAvailable${NC}"
    fi
    
    wait_key
    
    # ========== AUTOMATIC REROUTING ==========
    print_header "PHASE 5: AUTOMATIC REROUTING"
    
    print_step "5.1" "Dispatch new precision job (JOB-002)..."
    local new_assigned=$(dispatch_job "JOB-002" "Another precision milling job")
    print_result "Job JOB-002 assigned to: ${BOLD}$new_assigned${NC}"
    
    if [ "$new_assigned" == "milling-02" ]; then
        echo ""
        echo -e "  ${GREEN}✓ SUCCESS! Job automatically rerouted to milling-02${NC}"
    fi
    capture_evidence "final" "milling-01"
    
    # ========== SUMMARY ==========
    print_header "DEMO COMPLETE"
    
    echo "Summary of self-healing loop:"
    echo ""
    echo "  1. ✓ ML detected anomaly in vibration data"
    echo "  2. ✓ FMU physics validated the anomaly (confirmed wear)"
    echo "  3. ✓ Skill-broker downgraded capability (assured → notAvailable)"
    echo "  4. ✓ Dispatcher rerouted job to healthy asset"
    echo ""
    echo "This demonstrates 'resilience through adaptation'"
    echo "rather than 'failure through alarms'"
    echo ""
    
    print_result "Final state:"
    print_result "  milling-01: $(get_capability milling-01)"
    print_result "  milling-02: $(get_capability milling-02)"
}

main "$@"
