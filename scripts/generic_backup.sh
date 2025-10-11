#!/bin/bash
CONTAINER_NAME="$1"
echo "💾 Creating backup for $CONTAINER_NAME..."
BACKUP_DIR="${SHARED_DIR:-./shared-volumes}/backups"
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/${CONTAINER_NAME}_$(date +%Y%m%d_%H%M%S).tar.gz"
docker exec "playground-$CONTAINER_NAME" tar czf - /data 2>/dev/null > "$BACKUP_FILE" 2>/dev/null || true
if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    echo "✓ Backup: $BACKUP_FILE"
else
    rm -f "$BACKUP_FILE" 2>/dev/null
    echo "ℹ No data to backup"
fi
