#!/bin/bash
# Script: mysql-8-stack/init.sh
# Purpose: Initialize MySQL 8 stack with sample data
# Usage: init.sh <container-name>

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../lib/common.sh"

# --- Configuration ---
CONTAINER_NAME="${1:-}"
validate_container_name "$CONTAINER_NAME"

# --- Main Logic ---
main() {
    log_info "Initializing MySQL..."

    # Wait for MySQL to be ready
    wait_for_mysql "$CONTAINER_NAME" "root" "playground" 60

    sleep 5

    # Create tables and insert data
    docker_exec "$CONTAINER_NAME" mysql -u root -pplayground playground -e "
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2),
    category VARCHAR(50)
);

INSERT INTO users (username, email) VALUES
('admin', 'admin@playground.local'),
('user1', 'user1@example.com')
ON DUPLICATE KEY UPDATE username=username;

INSERT INTO products (name, price, category) VALUES
('Laptop', 999.99, 'Electronics'),
('Mouse', 29.99, 'Electronics')
ON DUPLICATE KEY UPDATE name=name;
" 2>/dev/null

    log_success "MySQL initialized"
}

main "$@"
