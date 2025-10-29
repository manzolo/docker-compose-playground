# Init/Halt Scripts Best Practices

## Overview

Docker Playground supports two types of lifecycle scripts:
- **post_start (init)**: Runs after container starts
- **pre_stop (halt)**: Runs before container stops

## Script Naming Convention

### Default Scripts (in `scripts/` directory)
```
scripts/CONTAINER_NAME/playground-CONTAINER_NAME-init.sh
scripts/CONTAINER_NAME/playground-CONTAINER_NAME-halt.sh
```

### Custom Scripts (defined in YAML)
```yaml
scripts:
  post_start: custom_script.sh        # Can be inline or external
  pre_stop: backup_script.sh
```

## Execution Order

1. **Default script** (if exists in scripts/ directory)
2. **Custom script** (if defined in YAML)

Both scripts execute if present.

## Init Scripts (post_start) Best Practices

### Purpose
Initialize the container after it starts:
- Install additional packages
- Configure services
- Create default data
- Set up environment
- Wait for services to be ready

### Template Structure
```bash
#!/bin/bash
# Init script for CONTAINER_NAME
# Purpose: Brief description

set -e  # Exit on error

CONTAINER_NAME="$1"
LOG_PREFIX="[CONTAINER_NAME-init]"

echo "$LOG_PREFIX Starting initialization..."

# 1. Wait for service to be ready
wait_for_service() {
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if docker exec "$CONTAINER_NAME" SERVICE_CHECK_CMD 2>/dev/null; then
            echo "$LOG_PREFIX Service is ready"
            return 0
        fi
        echo "$LOG_PREFIX Waiting for service... ($attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done

    echo "$LOG_PREFIX ERROR: Service failed to start"
    return 1
}

# 2. Install packages (if needed)
install_packages() {
    echo "$LOG_PREFIX Installing additional packages..."
    docker exec "$CONTAINER_NAME" bash -c "
        PACKAGE_INSTALL_CMD package1 package2 package3
    "
}

# 3. Initialize data/configuration
initialize_data() {
    echo "$LOG_PREFIX Creating default data..."
    docker exec "$CONTAINER_NAME" bash -c "
        # Your initialization commands here
    "
}

# Main execution
wait_for_service || exit 1
install_packages
initialize_data

echo "$LOG_PREFIX Initialization complete"
```

### Database Init Example (PostgreSQL)
```bash
#!/bin/bash
set -e

CONTAINER_NAME="$1"
LOG_PREFIX="[postgres-init]"

echo "$LOG_PREFIX Waiting for PostgreSQL to be ready..."

# Wait for PostgreSQL to accept connections
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker exec "$CONTAINER_NAME" pg_isready -U playground 2>/dev/null; then
        echo "$LOG_PREFIX PostgreSQL is ready"
        break
    fi
    sleep 2
    ((attempt++))
done

# Create additional databases/users
echo "$LOG_PREFIX Creating additional schemas..."
docker exec "$CONTAINER_NAME" psql -U playground -d playground <<EOF
CREATE SCHEMA IF NOT EXISTS app;
CREATE TABLE IF NOT EXISTS app.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO app.users (username) VALUES ('admin') ON CONFLICT DO NOTHING;
EOF

echo "$LOG_PREFIX Database initialization complete"
```

### Programming Language Init Example (Python)
```bash
#!/bin/bash
set -e

CONTAINER_NAME="$1"
LOG_PREFIX="[python-init]"

echo "$LOG_PREFIX Installing common Python packages..."

docker exec "$CONTAINER_NAME" bash -c "
    pip install --quiet --no-cache-dir \
        ipython \
        jupyter \
        pandas \
        numpy \
        requests \
        pytest

    # Create workspace directory
    mkdir -p /shared/projects

    # Create a sample project
    if [ ! -f /shared/projects/hello.py ]; then
        cat > /shared/projects/hello.py <<'PYTHON'
#!/usr/bin/env python3
print('Hello from Docker Playground!')
PYTHON
        chmod +x /shared/projects/hello.py
    fi
"

echo "$LOG_PREFIX Python environment ready"
```

## Halt Scripts (pre_stop) Best Practices

### Purpose
Prepare container for shutdown:
- Backup important data
- Save state
- Gracefully stop services
- Clean temporary files

### Template Structure
```bash
#!/bin/bash
# Halt script for CONTAINER_NAME
# Purpose: Backup and cleanup before shutdown

set -e

CONTAINER_NAME="$1"
SHARED_DIR="${2:-./shared-volumes}"
BACKUP_DIR="$SHARED_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_PREFIX="[CONTAINER_NAME-halt]"

echo "$LOG_PREFIX Starting pre-shutdown procedures..."

# 1. Create backup directory
mkdir -p "$BACKUP_DIR"

# 2. Backup data
backup_data() {
    echo "$LOG_PREFIX Creating backup..."

    # Your backup commands here
    docker exec "$CONTAINER_NAME" bash -c "
        # Export data to /shared
    " > "$BACKUP_DIR/CONTAINER_NAME_$TIMESTAMP.backup"

    echo "$LOG_PREFIX Backup saved: $BACKUP_DIR/CONTAINER_NAME_$TIMESTAMP.backup"
}

# 3. Cleanup temporary files
cleanup_temp() {
    echo "$LOG_PREFIX Cleaning temporary files..."
    docker exec "$CONTAINER_NAME" bash -c "
        rm -rf /tmp/*
        # Other cleanup tasks
    "
}

# 4. Save state (if applicable)
save_state() {
    echo "$LOG_PREFIX Saving state..."
    # Save any runtime state that should persist
}

# Main execution
backup_data
cleanup_temp
save_state

echo "$LOG_PREFIX Pre-shutdown complete"
```

### Database Halt Example (PostgreSQL)
```bash
#!/bin/bash
set -e

CONTAINER_NAME="$1"
SHARED_DIR="${2:-./shared-volumes}"
BACKUP_DIR="$SHARED_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_PREFIX="[postgres-halt]"

echo "$LOG_PREFIX Starting PostgreSQL backup..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Full database backup
echo "$LOG_PREFIX Dumping database..."
docker exec "$CONTAINER_NAME" pg_dump -U playground -Fc playground > \
    "$BACKUP_DIR/postgres_playground_$TIMESTAMP.dump"

echo "$LOG_PREFIX Backup size: $(du -h "$BACKUP_DIR/postgres_playground_$TIMESTAMP.dump" | cut -f1)"

# Keep only last 7 backups
echo "$LOG_PREFIX Rotating old backups..."
cd "$BACKUP_DIR"
ls -t postgres_playground_*.dump | tail -n +8 | xargs -r rm

echo "$LOG_PREFIX Backup complete: $BACKUP_DIR/postgres_playground_$TIMESTAMP.dump"
```

### Database Halt Example (MongoDB)
```bash
#!/bin/bash
set -e

CONTAINER_NAME="$1"
SHARED_DIR="${2:-./shared-volumes}"
BACKUP_DIR="$SHARED_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_PREFIX="[mongodb-halt]"

echo "$LOG_PREFIX Starting MongoDB backup..."

mkdir -p "$BACKUP_DIR"

# Export all databases
echo "$LOG_PREFIX Dumping all databases..."
docker exec "$CONTAINER_NAME" mongodump --out=/tmp/backup

# Copy backup to host
docker cp "$CONTAINER_NAME:/tmp/backup" "$BACKUP_DIR/mongodb_$TIMESTAMP"

# Compress backup
cd "$BACKUP_DIR"
tar -czf "mongodb_$TIMESTAMP.tar.gz" "mongodb_$TIMESTAMP"
rm -rf "mongodb_$TIMESTAMP"

echo "$LOG_PREFIX Backup complete: $BACKUP_DIR/mongodb_$TIMESTAMP.tar.gz"

# Cleanup old backups (keep last 5)
ls -t mongodb_*.tar.gz | tail -n +6 | xargs -r rm
```

## Group Stack Scripts

### Stack Init Best Practices
For stacks, coordinate initialization across containers:

```bash
#!/bin/bash
# Stack init script
set -e

LOG_PREFIX="[STACK_NAME-init]"

# 1. Wait for all services to be ready
wait_for_database() {
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if docker exec playground-mysql-stack mysqladmin ping -h localhost -u root -pplayground 2>/dev/null; then
            return 0
        fi
        sleep 2
        ((attempt++))
    done
    return 1
}

wait_for_web() {
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if docker exec playground-phpmyadmin-stack curl -f http://localhost:80 2>/dev/null; then
            return 0
        fi
        sleep 2
        ((attempt++))
    done
    return 1
}

# 2. Initialize in correct order
echo "$LOG_PREFIX Waiting for database..."
wait_for_database || { echo "Database failed to start"; exit 1; }

echo "$LOG_PREFIX Initializing database schema..."
docker exec playground-mysql-stack mysql -u root -pplayground <<EOF
CREATE DATABASE IF NOT EXISTS app;
USE app;
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
EOF

echo "$LOG_PREFIX Waiting for web interface..."
wait_for_web || { echo "Web interface failed to start"; exit 1; }

echo "$LOG_PREFIX Stack initialization complete"
echo "$LOG_PREFIX Access phpmyadmin at: http://localhost:8088"
```

### Stack Halt Best Practices
Backup all components in correct order:

```bash
#!/bin/bash
set -e

SHARED_DIR="${SHARED_DIR:-./shared-volumes}"
BACKUP_DIR="$SHARED_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_PREFIX="[STACK_NAME-halt]"

mkdir -p "$BACKUP_DIR"

echo "$LOG_PREFIX Starting stack backup..."

# Backup database first
docker exec playground-mysql-stack mysqldump -u root -pplayground --all-databases > \
    "$BACKUP_DIR/stack_mysql_$TIMESTAMP.sql"

# Backup any uploaded files
if docker exec playground-phpmyadmin-stack test -d /var/www/html/upload 2>/dev/null; then
    docker cp playground-phpmyadmin-stack:/var/www/html/upload \
        "$BACKUP_DIR/stack_uploads_$TIMESTAMP"
fi

# Create manifest
cat > "$BACKUP_DIR/stack_manifest_$TIMESTAMP.txt" <<EOF
Backup created: $(date)
Components:
  - MySQL database: stack_mysql_$TIMESTAMP.sql
  - Uploaded files: stack_uploads_$TIMESTAMP/
EOF

echo "$LOG_PREFIX Stack backup complete"
```

## Error Handling

Always include error handling:

```bash
#!/bin/bash
set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Catch errors in pipes

# Trap errors
trap 'echo "ERROR: Script failed at line $LINENO"; exit 1' ERR

# Your script logic here
```

## Logging

Use consistent logging:

```bash
LOG_PREFIX="[container-name-init]"

log_info() {
    echo "$LOG_PREFIX [INFO] $*"
}

log_error() {
    echo "$LOG_PREFIX [ERROR] $*" >&2
}

log_info "Starting process..."
log_error "Something went wrong"
```

## Testing Scripts

Test scripts before deployment:

```bash
# Test init script
bash scripts/mysql/playground-mysql-init.sh playground-mysql

# Test halt script
bash scripts/mysql/playground-mysql-halt.sh playground-mysql ./shared-volumes

# Check exit codes
echo "Exit code: $?"
```

## Summary

### DO:
✅ Wait for services to be ready before initialization
✅ Create backups before shutdown
✅ Use error handling (set -e)
✅ Log operations clearly
✅ Test scripts thoroughly
✅ Keep backups in /shared directory
✅ Rotate old backups

### DON'T:
❌ Assume services are immediately ready
❌ Skip error handling
❌ Store backups inside containers
❌ Ignore exit codes
❌ Use hardcoded paths
❌ Skip testing
