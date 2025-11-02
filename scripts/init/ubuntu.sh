#!/bin/bash
# Script: ubuntu.sh
# Purpose: Initialize Ubuntu containers with common development tools
# Usage: ubuntu.sh <container-name>

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# --- Configuration ---
CONTAINER_NAME="${1:-}"
validate_container_name "$CONTAINER_NAME"

# --- Main Logic ---
main() {
    log_info "Initializing Ubuntu for ${CONTAINER_NAME}..."

    # Install packages silently in background to avoid blocking
    docker_exec "$CONTAINER_NAME" bash -c '
export DEBIAN_FRONTEND=noninteractive
(
apt-get update -qq >/dev/null 2>&1 && \
apt-get install -y -qq \
    vim curl wget git build-essential \
    net-tools iputils-ping dnsutils telnet \
    htop tree less >/dev/null 2>&1
) &
' 2>/dev/null

    log_success "Ubuntu initialization started in background"
}

main "$@"
