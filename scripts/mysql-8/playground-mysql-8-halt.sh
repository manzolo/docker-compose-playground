#!/bin/bash
CONTAINER_NAME="$1"
echo "💾 Backing up MySQL databases from $CONTAINER_NAME..."

BACKUP_DIR="${SHARED_DIR:-./shared-volumes}/backups/${CONTAINER_NAME#playground-}"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Try backup with multiple attempts
MAX_ATTEMPTS=3
ATTEMPT=1
SUCCESS=false

while [ $ATTEMPT -le $MAX_ATTEMPTS ] && [ "$SUCCESS" = "false" ]; do
echo "Backup attempt $ATTEMPT/$MAX_ATTEMPTS..."

# Check if container is still running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "⚠ Container already stopped, cannot backup"
    break
fi

# Check if MySQL responds
if docker exec "$CONTAINER_NAME" mysqladmin ping -u root -pplayground --silent 2>/dev/null; then
    echo "✓ MySQL is responding, creating backup..."
    
    # Backup playground database
    BACKUP_FILE="$BACKUP_DIR/mysql_playground_${TIMESTAMP}.sql"
    
    # Use timeout to prevent hanging
    timeout 30 docker exec "$CONTAINER_NAME" \
    mysqldump -u root -pplayground --single-transaction --quick playground \
    > "$BACKUP_FILE" 2>/dev/null
    
    MYSQLDUMP_EXIT=$?
    
    if [ $MYSQLDUMP_EXIT -eq 0 ] && [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✓ Database backup saved: backups/mysql-8/mysql_playground_${TIMESTAMP}.sql ($SIZE)"
    SUCCESS=true
    
    # Backup list of databases
    docker exec "$CONTAINER_NAME" \
        mysql -u root -pplayground -e "SHOW DATABASES;" > \
        "$BACKUP_DIR/databases_${TIMESTAMP}.txt" 2>/dev/null || true
    
    break
    else
    echo "⚠ Backup attempt $ATTEMPT failed (exit code: $MYSQLDUMP_EXIT)"
    rm -f "$BACKUP_FILE"
    fi
else
    echo "⚠ MySQL not responding on attempt $ATTEMPT"
fi

ATTEMPT=$((ATTEMPT + 1))
[ $ATTEMPT -le $MAX_ATTEMPTS ] && sleep 1
done

if [ "$SUCCESS" = "true" ]; then
echo "✓ Backup completed successfully"
exit 0
else
echo "⚠ All backup attempts failed"
exit 1
fi