#!/bin/bash
# PostgreSQL Initialization Script

CONTAINER_NAME="$1"
SHARED_DIR="${SHARED_DIR:-/opt/docker-playground/shared-volumes}"

echo "Initializing PostgreSQL for ${CONTAINER_NAME}"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to accept connections..."
MAX_WAIT=30
COUNT=0

<<<<<<< Updated upstream
# Create example table
docker exec "playground-$CONTAINER_NAME" psql -U playground -d playground -c "
CREATE TABLE IF NOT EXISTS playground_info (
=======
while [ $COUNT -lt $MAX_WAIT ]; do
    if docker exec "${CONTAINER_NAME}" pg_isready -U playground -d playground &>/dev/null; then
        echo "PostgreSQL is ready!"
        break
    fi
    sleep 1
    COUNT=$((COUNT + 1))
done

if [ $COUNT -ge $MAX_WAIT ]; then
    echo "Warning: PostgreSQL may not be ready"
    exit 1
fi

# Create extension and sample schema
docker exec "${CONTAINER_NAME}" psql -U playground -d playground -c "
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE SCHEMA IF NOT EXISTS playground;
SET search_path TO playground, public;

-- Sample table
CREATE TABLE IF NOT EXISTS playground.welcome (
>>>>>>> Stashed changes
    id SERIAL PRIMARY KEY,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert welcome message
INSERT INTO playground.welcome (message) 
VALUES ('Welcome to Docker Playground PostgreSQL!') 
ON CONFLICT DO NOTHING;
" &>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ PostgreSQL initialization complete!"
    echo "✓ Created schema: playground"
    echo "✓ Created sample table: welcome"
else
    echo "⚠ PostgreSQL initialization had some errors"
fi