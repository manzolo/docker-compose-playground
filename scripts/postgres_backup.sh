#!/bin/bash
# PostgreSQL Backup Script

CONTAINER_NAME="$1"
<<<<<<< Updated upstream
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
=======
SHARED_DIR="${SHARED_DIR:-/opt/docker-playground/shared-volumes}"
BACKUP_DIR="${SHARED_DIR}/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="postgres_backup_${TIMESTAMP}.sql"

echo "Creating PostgreSQL backup for ${CONTAINER_NAME}"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Check if PostgreSQL is running
if ! docker exec "${CONTAINER_NAME}" pg_isready -U playground -d playground &>/dev/null; then
    echo "Warning: PostgreSQL is not responding, backup may be incomplete"
fi

# Create backup
docker exec "${CONTAINER_NAME}" pg_dump -U playground -d playground > "${BACKUP_DIR}/${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    # Compress backup
    gzip "${BACKUP_DIR}/${BACKUP_FILE}"
    
    BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}.gz" | cut -f1)
    echo "✓ Backup created: ${BACKUP_FILE}.gz (${BACKUP_SIZE})"
    
    # Keep only last 5 backups
    cd "${BACKUP_DIR}" && ls -t postgres_backup_*.sql.gz | tail -n +6 | xargs -r rm
    echo "✓ Cleaned old backups (keeping last 5)"
else
    echo "✗ Backup failed!"
    rm -f "${BACKUP_DIR}/${BACKUP_FILE}"
    exit 1
fi
>>>>>>> Stashed changes
