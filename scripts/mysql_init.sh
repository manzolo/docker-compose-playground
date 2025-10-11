#!/bin/bash
# Post-start script for MySQL containers
CONTAINER_NAME="$1"

echo "🐬 Initializing MySQL for $CONTAINER_NAME..."

# Wait for MySQL to be ready
sleep 5

# Create example table
docker exec "playground-$CONTAINER_NAME" mysql -u playground -pplayground playground -e "
CREATE TABLE IF NOT EXISTS playground_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message TEXT
);

INSERT INTO playground_info (message) VALUES ('MySQL initialized by playground manager');
" 2>/dev/null

echo "✓ MySQL initialized"
