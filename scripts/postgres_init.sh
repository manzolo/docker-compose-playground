#!/bin/bash
# Post-start script for PostgreSQL containers
CONTAINER_NAME="$1"

echo "🐘 Initializing PostgreSQL for $CONTAINER_NAME..."

# Wait for PostgreSQL to be ready
sleep 3

# Create example table
docker exec "playground-$CONTAINER_NAME" psql -U playground -d playground -c "
CREATE TABLE IF NOT EXISTS playground_info (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message TEXT
);

INSERT INTO playground_info (message) VALUES ('PostgreSQL initialized by playground manager');
" 2>/dev/null

echo "✓ PostgreSQL initialized"
