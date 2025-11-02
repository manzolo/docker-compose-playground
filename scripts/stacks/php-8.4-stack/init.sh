#!/bin/bash
# Script: php-8.4-stack/init.sh
# Purpose: Initialize PHP 8.4 stack with Xdebug and Composer
# Usage: init.sh <container-name>

set -euo pipefail

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../lib/common.sh"

# --- Configuration ---
CONTAINER_NAME="${1:-}"
validate_container_name "$CONTAINER_NAME"

# --- Main Logic ---
main() {
    log_info "Setting up PHP 8.4 for development..."

    # Check if Composer is already installed
    install_if_missing "$CONTAINER_NAME" \
        'command -v composer >/dev/null 2>&1' \
        'curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer --quiet && chmod +x /usr/local/bin/composer' \
        "Composer"

    # Check if Xdebug is already installed
    install_if_missing "$CONTAINER_NAME" \
        'php -m | grep -q xdebug' \
        'apt-get update -qq >/dev/null 2>&1 && apt-get install -y git unzip -qq >/dev/null 2>&1 && pecl install xdebug >/dev/null 2>&1 && docker-php-ext-enable xdebug >/dev/null 2>&1' \
        "Xdebug"

    # Configure Xdebug for remote debugging
    log_info "Configuring Xdebug..."
    docker_exec "$CONTAINER_NAME" bash -c 'cat > /usr/local/etc/php/conf.d/xdebug.ini << "EOF"
[xdebug]
xdebug.mode=develop,debug
xdebug.client_host=code-server-php-stack
xdebug.start_with_request=yes
xdebug.log=/tmp/xdebug.log
xdebug.idekey=VSCODE
xdebug.client_port=9003
EOF'

    # Create workspace directory if not exists
    docker_exec "$CONTAINER_NAME" mkdir -p /workspace

    # Create helper script for starting PHP server
    docker_exec "$CONTAINER_NAME" bash -c 'cat > /usr/local/bin/start-php-server << "EOF"
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

    docker_exec "$CONTAINER_NAME" bash -c '/usr/local/bin/start-php-server &'

    log_success "PHP 8.4 configured with Xdebug and Composer"
    echo "🐘 PHP version: $(docker_exec "$CONTAINER_NAME" php -v | head -1)"
    echo "🐛 Xdebug port: 9003"
    echo "🌐 Built-in server: start-php-server (access at http://localhost:8082)"
    echo "📦 Composer: $(docker_exec "$CONTAINER_NAME" composer --version --no-ansi 2>/dev/null || echo 'installed')"
    echo "📁 Workspace: /workspace (shared with Code Server)"
}

main "$@"
