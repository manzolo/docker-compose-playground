#!/bin/bash
# Post-start script for Python containers
CONTAINER_NAME="$1"

echo "🐍 Initializing Python environment for $CONTAINER_NAME..."

# Upgrade pip
docker exec "$CONTAINER_NAME" pip install --upgrade pip --quiet 2>/dev/null

# Install common packages
docker exec "$CONTAINER_NAME" pip install --quiet \
    requests \
    beautifulsoup4 \
    pandas \
    numpy 2>/dev/null

echo "✓ Python environment initialized"
