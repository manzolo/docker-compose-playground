#!/bin/bash
# Script: node.sh
# Purpose: Initialize Node.js containers with common packages
# Usage: node.sh <container-name>

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# --- Configuration ---
CONTAINER_NAME="${1:-}"
validate_container_name "$CONTAINER_NAME"

# --- Main Logic ---
main() {
    log_info "Initializing Node.js environment for ${CONTAINER_NAME}..."

    # Install common global packages
    log_info "Installing common packages..."
    docker_exec "$CONTAINER_NAME" npm install -g \
        nodemon \
        pm2 2>/dev/null || true

    log_success "Node.js environment initialized"
}

main "$@"
