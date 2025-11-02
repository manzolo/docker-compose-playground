#!/bin/bash
# Script: python-3.12/halt.sh
# Purpose: Backup Python 3.12 environment before stopping
# Usage: halt.sh <container-name>

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../lib/common.sh"

# --- Configuration ---
CONTAINER_NAME="${1:-}"
SHARED_DIR="${SHARED_DIR:-./shared-volumes}"
validate_container_name "$CONTAINER_NAME"

# --- Main Logic ---
main() {
    log_info "Backing up Python environment..."

    # Create backup directory
    local backup_dir="${SHARED_DIR}/data/backups/python-dev-stack"
    mkdir -p "$backup_dir"

    # Generate timestamp
    local timestamp
    timestamp=$(get_timestamp)

    # Export pip packages
    docker_exec "$CONTAINER_NAME" pip freeze > "${backup_dir}/requirements_${timestamp}.txt" 2>/dev/null

    log_success "Python packages backed up to ${backup_dir}/requirements_${timestamp}.txt"
}

main "$@"
