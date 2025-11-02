#!/bin/bash
# Script: php-8.4-stack/halt.sh
# Purpose: Backup PHP 8.4 stack before stopping
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
    log_info "Backing up PHP environment..."

    # Create backup directory
    local backup_dir="${SHARED_DIR}/data/backups/php-dev-stack"
    mkdir -p "$backup_dir"

    # Generate timestamp
    local timestamp
    timestamp=$(get_timestamp)

    # Export Composer lock file (if exists)
    if docker_exec "$CONTAINER_NAME" [ -f /workspace/composer.lock ]; then
        docker_exec "$CONTAINER_NAME" cat /workspace/composer.lock > "${backup_dir}/composer.lock_${timestamp}" 2>/dev/null
        log_success "Composer lock backed up to ${backup_dir}/composer.lock_${timestamp}"
    else
        log_info "No composer.lock found, skipping backup"
    fi
}

main "$@"
