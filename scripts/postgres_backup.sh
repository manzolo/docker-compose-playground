#!/bin/bash
CONTAINER_NAME="$1"
echo "💾 Backing up PostgreSQL from $CONTAINER_NAME..."
BACKUP_DIR="${SHARED_DIR:-./shared-volumes}/backups"
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/postgres_${CONTAINER_NAME}_$(date +%Y%m%d_%H%M%S).sql"
docker exec "playground-$CONTAINER_NAME" pg_dump -U playground playground > "$BACKUP_FILE" 2>/dev/null
if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    echo "✓ Backup: $BACKUP_FILE"
else
    rm -f "$BACKUP_FILE" 2>/dev/null
    echo "✗ Backup failed"
fi
