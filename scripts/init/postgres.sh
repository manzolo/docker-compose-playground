#!/bin/bash
# Script: postgres.sh
# Purpose: Initialize PostgreSQL containers with example data
# Usage: postgres.sh <container-name>

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# --- Configuration ---
CONTAINER_NAME="${1:-}"
validate_container_name "$CONTAINER_NAME"

# --- Main Logic ---
main() {
    log_info "Initializing PostgreSQL for ${CONTAINER_NAME}..."

    # Wait for PostgreSQL to be ready
    sleep 5

    # Create example tables
    docker_exec "$CONTAINER_NAME" psql -U playground -d playground -c "
CREATE TABLE IF NOT EXISTS playground_info (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message TEXT
);

INSERT INTO playground_info (message) VALUES ('PostgreSQL initialized by playground manager');
" 2>/dev/null || true

    log_success "PostgreSQL initialized"
}

main "$@"
