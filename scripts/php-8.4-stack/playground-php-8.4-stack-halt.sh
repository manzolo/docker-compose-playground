#!/bin/bash
# Pre-stop script for php-8.4-stack
# Backs up Composer dependencies before stopping

CONTAINER_NAME="$1"
SHARED_DIR="${SHARED_DIR:-./shared-volumes}"

echo "Backing up PHP environment..."

# Create backup directory
BACKUP_DIR="${SHARED_DIR}/data/backups/php-dev-stack"
mkdir -p "${BACKUP_DIR}"

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Export Composer lock file (if exists)
if docker exec "${CONTAINER_NAME}" [ -f /workspace/composer.lock ]; then
  docker exec "${CONTAINER_NAME}" cat /workspace/composer.lock > "${BACKUP_DIR}/composer.lock_${TIMESTAMP}" 2>/dev/null
  echo "✓ Composer lock backed up to ${BACKUP_DIR}/composer.lock_${TIMESTAMP}"
else
  echo "ℹ No composer.lock found, skipping backup"
fi
