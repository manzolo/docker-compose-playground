#!/bin/bash
# Pre-stop script for python-3.12-stack
# Backs up Python environment before stopping

CONTAINER_NAME="$1"
SHARED_DIR="${SHARED_DIR:-./shared-volumes}"

echo "Backing up Python environment..."

# Create backup directory
BACKUP_DIR="${SHARED_DIR}/backups/python-dev-stack"
mkdir -p "${BACKUP_DIR}"

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Export pip packages
docker exec "${CONTAINER_NAME}" pip freeze > "${BACKUP_DIR}/requirements_${TIMESTAMP}.txt" 2>/dev/null

echo "✓ Python packages backed up to ${BACKUP_DIR}/requirements_${TIMESTAMP}.txt"
