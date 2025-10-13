#!/bin/bash
CONTAINER_NAME="$1"
IMAGE_NAME="${CONTAINER_NAME#playground-}"

BACKUP_BASE="${SHARED_DIR:-./shared-volumes}/backups"
BACKUP_DIR="$BACKUP_BASE/${IMAGE_NAME}"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/${IMAGE_NAME}_${TIMESTAMP}.sql.gz"

echo "💾 Backing up PostgreSQL: $CONTAINER_NAME"

# Usa le environment variables del container PostgreSQL
docker exec "$CONTAINER_NAME" bash -c '
  # Usa le env di PostgreSQL
  export PGPASSWORD="${POSTGRES_PASSWORD:-$POSTGRES_PASSWORD}"
  
  # Esegui il backup di tutti i database
  pg_dumpall -U "${POSTGRES_USER:-postgres}" -h localhost | gzip
' > "$BACKUP_FILE"

# Verifica il backup
if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    # Verifica che il file gz sia valido
    if gzip -t "$BACKUP_FILE" 2>/dev/null; then
        echo "✅ PostgreSQL backup successful: ${BACKUP_FILE} (${SIZE})"
    else
        echo "❌ Backup file is corrupted or empty"
        rm -f "$BACKUP_FILE"
        exit 1
    fi
else
    echo "❌ PostgreSQL backup failed - no file created or file is empty"
    # Debug: mostra i primi bytes del file se esiste
    if [ -f "$BACKUP_FILE" ]; then
        echo "📄 File content (first 100 bytes):"
        head -c 100 "$BACKUP_FILE" | hexdump -C || true
        rm -f "$BACKUP_FILE"
    fi
    exit 1
fi