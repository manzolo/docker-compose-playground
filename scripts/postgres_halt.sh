#!/bin/bash
# PostgreSQL Backup Script

CONTAINER_NAME="$1"
IMAGE_NAME="${CONTAINER_NAME#playground-}"
SHARED_DIR="${SHARED_DIR:-./shared-volumes}"
BACKUP_BASE="${SHARED_DIR}/data/backups"
BACKUP_DIR="${BACKUP_BASE}/${CONTAINER_NAME#playground-}"

echo "💾 Backing up PostgreSQL from ${CONTAINER_NAME}..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/postgres_${TIMESTAMP}.sql.gz"

# Check if PostgreSQL is responding
if ! docker exec "${CONTAINER_NAME}" pg_isready -U postgres &>/dev/null; then
    echo "⚠️  Warning: PostgreSQL is not responding, backup may be incomplete"
fi

# Create backup using pg_dumpall (all databases)
docker exec "$CONTAINER_NAME" bash -c '
    # Get postgres user from environment (default: postgres)
    PGUSER="${POSTGRES_USER:-postgres}"
    export PGPASSWORD="${POSTGRES_PASSWORD}"
    
    # Dump all databases
    pg_dumpall -U "$PGUSER" -h localhost | gzip
' > "$BACKUP_FILE"

# Verify the backup
if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    # Check if gzip file is valid
    if gzip -t "$BACKUP_FILE" 2>/dev/null; then
        SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        echo "✅ PostgreSQL backup successful: $(basename $BACKUP_FILE) (${SIZE})"
        
        # Keep only last 5 backups
        cd "$BACKUP_DIR" && ls -t postgres_*.sql.gz 2>/dev/null | tail -n +6 | xargs -r rm
        echo "✅ Cleaned old backups (keeping last 5)"
    else
        echo "❌ Backup file is corrupted"
        rm -f "$BACKUP_FILE"
        exit 1
    fi
else
    echo "❌ PostgreSQL backup failed - no file created or file is empty"
    rm -f "$BACKUP_FILE" 2>/dev/null
    exit 1
fi