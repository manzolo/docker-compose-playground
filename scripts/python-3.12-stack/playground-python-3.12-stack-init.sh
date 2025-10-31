#!/bin/bash
# Post-start script for python-3.12-stack
# Sets up Python development environment with debugging support

CONTAINER_NAME="$1"

echo "Setting up Python 3.12 for development..."

# Upgrade pip
echo "Upgrading pip..."
docker exec "${CONTAINER_NAME}" pip install --upgrade pip setuptools wheel --quiet

# Install debugpy for remote debugging
echo "Installing debugpy for remote debugging..."
docker exec "${CONTAINER_NAME}" pip install debugpy ipython ipdb --quiet

# Install common development tools
echo "Installing development tools..."
docker exec "${CONTAINER_NAME}" pip install --quiet \
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
docker exec "${CONTAINER_NAME}" mkdir -p /workspace

# Create helper script for debugging
docker exec "${CONTAINER_NAME}" bash -c 'cat > /usr/local/bin/debug-script << "EOF"
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

echo "✅ Python 3.12 configured with debugging support"
echo "🐛 Debug port: 5678 (use debug-script command)"
echo "🌐 Web server ports: 8001 (FastAPI/Django), 5010 (Flask)"
echo "📁 Workspace: /workspace (shared with Code Server)"
