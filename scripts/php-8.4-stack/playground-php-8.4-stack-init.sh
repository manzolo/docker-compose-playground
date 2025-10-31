#!/bin/bash
# Post-start script for php-8.4-stack
# Sets up PHP development environment with Xdebug and Composer

CONTAINER_NAME="$1"

echo "Setting up PHP 8.4 for development..."

# Check if Composer is already installed
COMPOSER_INSTALLED=$(docker exec "${CONTAINER_NAME}" bash -c 'command -v composer >/dev/null 2>&1 && echo "yes" || echo "no"')

if [ "$COMPOSER_INSTALLED" = "yes" ]; then
  echo "✓ Composer already installed, skipping"
else
  # Install Composer
  echo "Installing Composer..."
  docker exec "${CONTAINER_NAME}" bash -c '
    curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer --quiet
    chmod +x /usr/local/bin/composer
    echo "✓ Composer installed"
  '
fi

# Check if Xdebug is already installed
XDEBUG_INSTALLED=$(docker exec "${CONTAINER_NAME}" php -m | grep -q xdebug && echo "yes" || echo "no")

if [ "$XDEBUG_INSTALLED" = "yes" ]; then
  echo "✓ Xdebug already installed, skipping"
else
  # Install Xdebug
  echo "Installing Xdebug..."
  docker exec "${CONTAINER_NAME}" bash -c '
    apt-get update -qq 2>/dev/null
    apt-get install -y git unzip -qq 2>/dev/null
    pecl install xdebug 2>/dev/null
    docker-php-ext-enable xdebug
    echo "✓ Xdebug installed"
  '
fi

# Configure Xdebug for remote debugging
echo "Configuring Xdebug..."
docker exec "${CONTAINER_NAME}" bash -c 'cat > /usr/local/etc/php/conf.d/xdebug.ini << "EOF"
[xdebug]
xdebug.mode=develop,debug
xdebug.client_host=code-server-php-stack
xdebug.start_with_request=yes
xdebug.log=/tmp/xdebug.log
xdebug.idekey=VSCODE
xdebug.client_port=9003
EOF'

# Create workspace directory if not exists
docker exec "${CONTAINER_NAME}" mkdir -p /workspace

# Create helper script for starting PHP server
docker exec "${CONTAINER_NAME}" bash -c 'cat > /usr/local/bin/start-php-server << "EOF"
#!/bin/bash
# Helper script to start PHP built-in server

echo "Starting PHP built-in server..."
echo "Access at: http://localhost:8082"
echo "Document root: /workspace"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd /workspace
exec php -S 0.0.0.0:8000
EOF
chmod +x /usr/local/bin/start-php-server'

docker exec "${CONTAINER_NAME}" bash -c '/usr/local/bin/start-php-server &'

echo "✅ PHP 8.4 configured with Xdebug and Composer"
echo "🐘 PHP version: $(docker exec "${CONTAINER_NAME}" php -v | head -1)"
echo "🐛 Xdebug port: 9003"
echo "🌐 Built-in server: start-php-server (access at http://localhost:8082)"
echo "📦 Composer: $(docker exec "${CONTAINER_NAME}" composer --version --no-ansi 2>/dev/null || echo 'installed')"
echo "📁 Workspace: /workspace (shared with Code Server)"
