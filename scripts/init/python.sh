#!/bin/bash
# Script: python.sh
# Purpose: Initialize Python containers with common packages
# Usage: python.sh <container-name>

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# --- Configuration ---
CONTAINER_NAME="${1:-}"
validate_container_name "$CONTAINER_NAME"

# --- Main Logic ---
main() {
    log_info "Initializing Python environment for ${CONTAINER_NAME}..."

    # Upgrade pip
    docker_exec "$CONTAINER_NAME" pip install --upgrade pip --quiet 2>/dev/null

    # Install common packages
    log_info "Installing common packages..."
    docker_exec "$CONTAINER_NAME" pip install --quiet \
        requests \
        beautifulsoup4 \
        pandas \
        numpy 2>/dev/null

    log_success "Python environment initialized"
}

main "$@"
