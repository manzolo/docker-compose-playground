#!/bin/bash
# Script: mysql.sh
# Purpose: Initialize MySQL containers with example data
# Usage: mysql.sh <container-name>

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# --- Configuration ---
CONTAINER_NAME="${1:-}"
validate_container_name "$CONTAINER_NAME"

# --- Main Logic ---
main() {
    log_info "Initializing MySQL for ${CONTAINER_NAME}..."

    # Wait for MySQL to be ready
    sleep 5

    # Create example table
    docker_exec "$CONTAINER_NAME" mysql -u playground -pplayground playground -e "
CREATE TABLE IF NOT EXISTS playground_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message TEXT
);

INSERT INTO playground_info (message) VALUES ('MySQL initialized by playground manager');
" 2>/dev/null

    log_success "MySQL initialized"
}

main "$@"
