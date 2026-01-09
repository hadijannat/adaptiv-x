#!/usr/bin/env bash
# bootstrap_local.sh - Start Adaptiv-X Infrastructure Stack
#
# Starts BaSyx AAS Environment, registries, MQTT, and MinIO
# Waits for all services to be healthy before returning

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_DIR="$PROJECT_ROOT/deploy/compose"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

wait_for_service() {
    local service_name=$1
    local url=$2
    local max_attempts=${3:-30}
    local attempt=1

    log_info "Waiting for $service_name..."
    while [ $attempt -le $max_attempts ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            log_info "$service_name is ready!"
            return 0
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done
    
    log_error "$service_name failed to start after $max_attempts seconds"
    return 1
}

main() {
    log_info "Starting Adaptiv-X Infrastructure Stack..."
    
    # Change to compose directory
    cd "$COMPOSE_DIR"
    
    # Create .env from example if not exists
    if [ ! -f .env ]; then
        cp .env.example .env
        log_info "Created .env from .env.example"
    fi
    
    # Start infrastructure services
    log_info "Starting Docker Compose services..."
    docker compose up -d aas-registry submodel-registry mosquitto minio minio-init
    
    # Wait for core services
    wait_for_service "AAS Registry" "http://localhost:4000/shell-descriptors"
    wait_for_service "Submodel Registry" "http://localhost:4002/submodel-descriptors"
    wait_for_service "MinIO" "http://localhost:9000/minio/health/live"
    
    # Start AAS Environment (depends on registries)
    docker compose up -d aas-environment
    wait_for_service "AAS Environment" "http://localhost:4001/shells"
    
    log_info "=========================================="
    log_info "Adaptiv-X Infrastructure is ready!"
    log_info "=========================================="
    log_info ""
    log_info "Services:"
    log_info "  AAS Environment: http://localhost:4001"
    log_info "  AAS Registry:    http://localhost:4000"
    log_info "  Submodel Registry: http://localhost:4002"
    log_info "  MQTT Broker:     localhost:1883"
    log_info "  MinIO Console:   http://localhost:9001 (adaptivx / adaptivx123)"
    log_info ""
    log_info "Next steps:"
    log_info "  ./scripts/seed_aas.sh    # Upload AAS packages"
    log_info "  ./scripts/run_demo.sh    # Run the demo scenario"
}

main "$@"
