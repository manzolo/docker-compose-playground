#!/bin/bash
CONTAINER_NAME="$1"
echo "🐧 Initializing Ubuntu for $CONTAINER_NAME..."

# Install packages silently in background to avoid blocking
docker exec "$CONTAINER_NAME" bash -c '
export DEBIAN_FRONTEND=noninteractive
(
apt-get update -qq >/dev/null 2>&1 && \
apt-get install -y -qq \
    vim curl wget git build-essential \
    net-tools iputils-ping dnsutils telnet \
    htop tree less >/dev/null 2>&1
) &
' 2>/dev/null

echo "✓ Ubuntu $CONTAINER_NAME initialization started in background"