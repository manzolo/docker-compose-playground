#!/bin/bash
# Script: backup.sh
# Purpose: Generic backup script for containers
# Usage: backup.sh <container-name>

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
    log_info "Creating backup for ${CONTAINER_NAME}..."

    local backup_dir="${SHARED_DIR}/data/backups"
    mkdir -p "$backup_dir"

    local timestamp
    timestamp=$(get_timestamp)
    local backup_file="${backup_dir}/${CONTAINER_NAME}_${timestamp}.tar.gz"

    # Create backup
    docker_exec "$CONTAINER_NAME" tar czf - /data 2>/dev/null > "$backup_file" 2>/dev/null || true

    if [ -f "$backup_file" ] && [ -s "$backup_file" ]; then
        log_success "Backup: ${backup_file}"
    else
        rm -f "$backup_file" 2>/dev/null
        log_info "No data to backup"
    fi
}

main "$@"
