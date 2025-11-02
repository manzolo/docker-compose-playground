#!/bin/bash
# Script: mysql-8-stack/halt.sh
# Purpose: Backup MySQL 8 stack before stopping
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
    log_info "Backing up MySQL..."

    local backup_dir="${SHARED_DIR}/data/backups/${CONTAINER_NAME#playground-}"
    mkdir -p "$backup_dir"

    local timestamp
    timestamp=$(get_timestamp)

    # Create backup
    docker_exec "$CONTAINER_NAME" mysqldump -u root -pplayground playground > \
        "${backup_dir}/mysql_${timestamp}.sql" 2>/dev/null

    gzip "${backup_dir}/mysql_${timestamp}.sql"

    log_success "Backup created at ${backup_dir}/mysql_${timestamp}.sql.gz"
}

main "$@"
