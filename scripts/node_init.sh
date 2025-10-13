#!/bin/bash
# Post-start script for Node.js containers
CONTAINER_NAME="$1"

echo "🟢 Initializing Node.js environment for $CONTAINER_NAME..."

# Create package.json in shared folder if not exists
if [ ! -f "/shared/package.json" ]; then
    docker exec "$CONTAINER_NAME" sh -c "
        cd /shared && npm init -y 2>/dev/null
        npm install express axios 2>/dev/null
    "
fi

echo "✓ Node.js environment initialized"
