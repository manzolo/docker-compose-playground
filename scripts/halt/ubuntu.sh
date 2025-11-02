#!/bin/bash
# Script: ubuntu.sh
# Purpose: Backup Ubuntu container configuration before stopping
# Usage: ubuntu.sh <container-name>

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# --- Configuration ---
CONTAINER_NAME="${1:-}"
SHARED_DIR="${SHARED_DIR:-./shared-volumes}"
validate_container_name "$CONTAINER_NAME"

# --- Main Logic ---
main() {
    log_info "Backing up Ubuntu configuration for ${CONTAINER_NAME}..."

    # Create backup directory (remove playground- prefix if present)
    local backup_dir="${SHARED_DIR}/data/backups/${CONTAINER_NAME#playground-}"
    mkdir -p "$backup_dir"

    local timestamp
    timestamp=$(get_timestamp)

    # Backup installed packages list
    docker_exec "$CONTAINER_NAME" dpkg --get-selections > \
    "$backup_dir/packages_${timestamp}.txt" 2>/dev/null || true

    # Backup apt sources
    docker_exec "$CONTAINER_NAME" cat /etc/apt/sources.list > \
    "$backup_dir/sources_${timestamp}.txt" 2>/dev/null || true

    log_success "Backup saved to: data/backups/${CONTAINER_NAME#playground-}/"
}

main "$@"
