#!/bin/bash
BACKUP_DIR="${SHARED_DIR}/backups/${CONTAINER_NAME#playground-}"
mkdir -p "${BACKUP_DIR}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

docker exec "${CONTAINER_NAME}" mysqldump -u root -pplayground playground > "${BACKUP_DIR}/mysql_${TIMESTAMP}.sql" 2>/dev/null
gzip "${BACKUP_DIR}/mysql_${TIMESTAMP}.sql"
echo "✓ Backup created"
