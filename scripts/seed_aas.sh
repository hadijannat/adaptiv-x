#!/usr/bin/env bash
# seed_aas.sh - Upload AAS Packages to BaSyx
#
# Uploads milling-01 and milling-02 AAS packages via JSON API
# Uploads FMU to MinIO for SimulationModels submodel

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
AAS_DIR="$PROJECT_ROOT/aas/packages"
FMU_DIR="$PROJECT_ROOT/fmu/export"

# Endpoints
AAS_ENV_URL="${AAS_ENV_URL:-http://localhost:4001}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-localhost:9000}"
MINIO_USER="${MINIO_USER:-adaptivx}"
MINIO_PASS="${MINIO_PASS:-adaptivx123}"
AASX_ACCEPT_HEADER="application/asset-administration-shell-package"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

upload_aas_package() {
    local file=$1
    local filename=$(basename "$file")
    
    log_info "Uploading $filename to AAS Environment..."
    
    # Parse JSON and upload shells and submodels
    local content=$(cat "$file")
    
    # Upload AAS shells
    local shells=$(echo "$content" | jq -c '.assetAdministrationShells[]' 2>/dev/null || echo "")
    if [ -n "$shells" ]; then
        echo "$shells" | while read -r shell; do
            local id_short=$(echo "$shell" | jq -r '.idShort')
            log_info "  Creating AAS: $id_short"
            
            curl -sf -X POST "$AAS_ENV_URL/shells" \
                -H "Content-Type: application/json" \
                -d "$shell" > /dev/null 2>&1 || {
                log_warn "  AAS $id_short may already exist, trying update..."
                local encoded_id=$(echo -n "$(echo "$shell" | jq -r '.id')" | base64 | tr '+/' '-_' | tr -d '=')
                curl -sf -X PUT "$AAS_ENV_URL/shells/$encoded_id" \
                    -H "Content-Type: application/json" \
                    -d "$shell" > /dev/null 2>&1 || true
            }
        done
    fi
    
    # Upload submodels
    local submodels=$(echo "$content" | jq -c '.submodels[]' 2>/dev/null || echo "")
    if [ -n "$submodels" ]; then
        echo "$submodels" | while read -r submodel; do
            local id_short=$(echo "$submodel" | jq -r '.idShort')
            log_info "  Creating Submodel: $id_short"
            
            curl -sf -X POST "$AAS_ENV_URL/submodels" \
                -H "Content-Type: application/json" \
                -d "$submodel" > /dev/null 2>&1 || {
                log_warn "  Submodel $id_short may already exist, trying update..."
                local encoded_id=$(echo -n "$(echo "$submodel" | jq -r '.id')" | base64 | tr '+/' '-_' | tr -d '=')
                curl -sf -X PUT "$AAS_ENV_URL/submodels/$encoded_id" \
                    -H "Content-Type: application/json" \
                    -d "$submodel" > /dev/null 2>&1 || true
            }
        done
    fi
}

upload_aasx_package() {
    local file=$1
    local filename=$(basename "$file")

    log_info "Uploading AASX package $filename via /upload..."
    curl -sf -X POST "$AAS_ENV_URL/upload" \
        -H "Accept: ${AASX_ACCEPT_HEADER}" \
        -F "file=@${file}" > /dev/null 2>&1 || {
        log_error "Failed to upload $filename via /upload"
        return 1
    }
}

upload_fmu() {
    local fmu_file="$FMU_DIR/bearing_wear.fmu"
    
    if [ -f "$fmu_file" ]; then
        log_info "Uploading FMU to MinIO..."
        
        # Use mc (MinIO Client) if available
        if command -v mc &> /dev/null; then
            mc alias set adaptivx-minio http://$MINIO_ENDPOINT $MINIO_USER $MINIO_PASS 2>/dev/null || true
            mc cp "$fmu_file" adaptivx-minio/adaptivx-fmu/bearing_wear.fmu
            log_info "FMU uploaded to MinIO"
        else
            # Use curl for MinIO S3 API
            log_warn "MinIO client (mc) not found. Please upload FMU manually or install mc."
            log_info "FMU path: $fmu_file"
            log_info "Target: http://$MINIO_ENDPOINT/adaptivx-fmu/bearing_wear.fmu"
        fi
    else
        log_warn "FMU file not found at $fmu_file"
        log_info "To create the FMU, run: cd fmu/modelica && omc ../scripts/export_fmu.mos"
    fi
}

main() {
    log_info "Seeding Adaptiv-X AAS Packages..."
    log_info ""
    
    # Check AAS Environment is available
    if ! curl -sf "$AAS_ENV_URL/shells" > /dev/null 2>&1; then
        log_error "AAS Environment not available at $AAS_ENV_URL"
        log_error "Run ./scripts/bootstrap_local.sh first"
        exit 1
    fi
    
    # Upload AAS packages (prefer AASX if present)
    local aasx_found=false
    for package in "$AAS_DIR"/*.aasx; do
        if [ -f "$package" ]; then
            aasx_found=true
            upload_aasx_package "$package"
        fi
    done

    if [ "$aasx_found" = false ]; then
        for package in "$AAS_DIR"/*.json; do
            if [ -f "$package" ]; then
                upload_aas_package "$package"
            fi
        done
    fi
    
    # Upload FMU
    upload_fmu
    
    log_info ""
    log_info "=========================================="
    log_info "AAS Packages seeded successfully!"
    log_info "=========================================="
    log_info ""
    log_info "Verify:"
    log_info "  curl -s http://localhost:4001/shells | jq '.result[].idShort'"
    log_info "  curl -s http://localhost:4001/submodels | jq '.result[].idShort'"
}

main "$@"
