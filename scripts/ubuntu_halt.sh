#!/bin/bash
CONTAINER_NAME="$1"
echo "💾 Backing up Ubuntu configuration for $CONTAINER_NAME..."

# Create backup directory
BACKUP_DIR="${SHARED_DIR:-./shared-volumes}/backups/$CONTAINER_NAME"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup installed packages list
docker exec "$CONTAINER_NAME" dpkg --get-selections > \
"$BACKUP_DIR/packages_${TIMESTAMP}.txt" 2>/dev/null || true

# Backup apt sources
docker exec "$CONTAINER_NAME" cat /etc/apt/sources.list > \
"$BACKUP_DIR/sources_${TIMESTAMP}.txt" 2>/dev/null || true

echo "✓ Backup saved to: backups/$CONTAINER_NAME/"
