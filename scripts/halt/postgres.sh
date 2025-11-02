#!/bin/bash
# Script: postgres.sh
# Purpose: Cleanup/backup PostgreSQL containers before stopping
# Usage: postgres.sh <container-name>

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
    log_info "Backing up PostgreSQL for ${CONTAINER_NAME}..."

    # Create backup directory
    local backup_dir
    backup_dir=$(create_backup_dir "$CONTAINER_NAME")

    # Generate timestamp
    local timestamp
    timestamp=$(get_timestamp)

    # Backup databases
    local backup_file="${backup_dir}/postgres_${timestamp}.sql"
    docker_exec "$CONTAINER_NAME" pg_dumpall -U playground > "$backup_file" 2>/dev/null || {
        log_warning "Backup failed or no data to backup"
        rm -f "$backup_file"
        return 0
    }

    if [ -f "$backup_file" ] && [ -s "$backup_file" ]; then
        log_success "Backup saved to ${backup_file}"
    else
        rm -f "$backup_file" 2>/dev/null
        log_info "No data to backup"
    fi
}

main "$@"
