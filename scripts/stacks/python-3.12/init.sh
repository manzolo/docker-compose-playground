#!/bin/bash
# Script: python-3.12/init.sh
# Purpose: Initialize Python 3.12 stack with debugging support
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
    log_info "Setting up Python 3.12 for development..."

    # Upgrade pip
    log_info "Upgrading pip..."
    docker_exec "$CONTAINER_NAME" pip install --upgrade pip setuptools wheel --quiet

    # Install debugpy for remote debugging
    log_info "Installing debugpy for remote debugging..."
    docker_exec "$CONTAINER_NAME" pip install debugpy ipython ipdb --quiet

    # Install common development tools
    log_info "Installing development tools..."
    docker_exec "$CONTAINER_NAME" pip install --quiet \
        black \
        pylint \
        flake8 \
        mypy \
        pytest \
        pytest-cov \
        pytest-mock \
        requests \
        python-dotenv \
        pydantic

    # Create workspace directory if not exists
    docker_exec "$CONTAINER_NAME" mkdir -p /workspace

    # Create helper script for debugging
    docker_exec "$CONTAINER_NAME" bash -c 'cat > /usr/local/bin/debug-script << "EOF"
#!/bin/bash
# Helper script to run Python scripts with debugpy
# Usage: debug-script your_script.py

if [ -z "$1" ]; then
    echo "Usage: debug-script <python_file>"
    echo "Example: debug-script /workspace/src/main.py"
    exit 1
fi

echo "Starting Python script with debugpy..."
echo "Listening on 0.0.0.0:5678"
echo "Connect from Code Server with \"Python: Remote Attach\" configuration"
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client "$@"
EOF
chmod +x /usr/local/bin/debug-script'

    log_success "Python 3.12 configured with debugging support"
    echo "🐛 Debug port: 5678 (use debug-script command)"
    echo "🌐 Web server ports: 8001 (FastAPI/Django), 5010 (Flask)"
    echo "📁 Workspace: /workspace (shared with Code Server)"
}

main "$@"
