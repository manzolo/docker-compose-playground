#!/bin/bash
# Post-start script for code-server-python-stack
# Configures VS Code Server for Python development with debugging support

CONTAINER_NAME="$1"

echo "Setting up Code Server for Python development..."

# Install Python in code-server container (needed for IntelliSense and local debugging)
echo "Installing Python 3 in code-server container..."
docker exec "${CONTAINER_NAME}" bash -c '
  apt-get update -qq 2>/dev/null
  apt-get install -y python3 python3-pip python3-venv -qq 2>/dev/null
  ln -sf /usr/bin/python3 /usr/bin/python 2>/dev/null || true
  echo "✓ Python 3 installed"
'

# Wait for code-server to be ready (check if process is running)
echo "Waiting for code-server to start..."
MAX_WAIT=60
COUNT=0
while [ $COUNT -lt $MAX_WAIT ]; do
  if docker exec "${CONTAINER_NAME}" pgrep -f "code-server" > /dev/null 2>&1; then
    echo "✓ Code-server process detected"
    break
  fi
  sleep 2
  COUNT=$((COUNT + 2))
done

# Additional wait for code-server to be fully ready
sleep 5

# Check if extensions are already installed
EXTENSIONS_EXIST=$(docker exec "${CONTAINER_NAME}" bash -c '
  [ -d /config/extensions ] && ls -1 /config/extensions | grep -q "ms-python.python" && echo "yes" || echo "no"
')

if [ "$EXTENSIONS_EXIST" = "yes" ]; then
  echo "✓ Python extensions already installed, skipping"
else
  # Install Python extension and debugpy (run as user abc with correct HOME)
  echo "Installing VS Code Python extensions..."
  docker exec -u abc "${CONTAINER_NAME}" bash -c '
    export HOME=/config

    # Install Python extension (ms-python.python)
    /app/code-server/bin/code-server --extensions-dir /config/extensions --install-extension ms-python.python 2>/dev/null || true

    # Install Pylance for better IntelliSense
    /app/code-server/bin/code-server --extensions-dir /config/extensions --install-extension ms-python.vscode-pylance 2>/dev/null || true

    # Install additional useful extensions
    /app/code-server/bin/code-server --extensions-dir /config/extensions --install-extension ms-python.debugpy 2>/dev/null || true
    /app/code-server/bin/code-server --extensions-dir /config/extensions --install-extension donjayamanne.python-environment-manager 2>/dev/null || true
    /app/code-server/bin/code-server --extensions-dir /config/extensions --install-extension KevinRose.vsc-python-indent 2>/dev/null || true
    /app/code-server/bin/code-server --extensions-dir /config/extensions --install-extension njpwerner.autodocstring 2>/dev/null || true
  '

  echo "✓ Extensions installation triggered (may complete in background)"
fi

# Create workspace settings for Python debugging (as user abc)
echo "Configuring Python debugger..."
docker exec -u abc "${CONTAINER_NAME}" bash -c 'mkdir -p /workspace/.vscode'

# Create launch.json for debugging (only if not exists)
if docker exec "${CONTAINER_NAME}" [ ! -f /workspace/.vscode/launch.json ]; then
  echo "Creating launch.json..."
  docker exec "${CONTAINER_NAME}" bash -c 'cat > /workspace/.vscode/launch.json << "EOF"
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "justMyCode": true
        },
        {
            "name": "Python: Remote Attach",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "python-3.12-stack",
                "port": 5678
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/workspace"
                }
            ]
        },
        {
            "name": "Python: Django",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/manage.py",
            "args": [
                "runserver",
                "0.0.0.0:8000"
            ],
            "django": true,
            "justMyCode": true
        },
        {
            "name": "Python: Flask",
            "type": "python",
            "request": "launch",
            "module": "flask",
            "env": {
                "FLASK_APP": "app.py",
                "FLASK_DEBUG": "1"
            },
            "args": [
                "run",
                "--host=0.0.0.0",
                "--port=5000"
            ],
            "jinja": true,
            "justMyCode": true
        },
        {
            "name": "Python: FastAPI",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "main:app",
                "--reload",
                "--host",
                "0.0.0.0",
                "--port",
                "8000"
            ],
            "jinja": true,
            "justMyCode": true
        }
    ]
}
EOF'
else
  echo "✓ launch.json already exists, skipping"
fi

# Create settings.json (only if not exists)
if docker exec "${CONTAINER_NAME}" [ ! -f /workspace/.vscode/settings.json ]; then
  echo "Creating settings.json..."
  docker exec "${CONTAINER_NAME}" bash -c 'cat > /workspace/.vscode/settings.json << "EOF"
{
    "python.defaultInterpreterPath": "/usr/bin/python3",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.analysis.typeCheckingMode": "basic",
    "python.analysis.autoImportCompletions": true,
    "files.watcherExclude": {
        "**/.git/objects/**": true,
        "**/.git/subtree-cache/**": true,
        "**/node_modules/*/**": true,
        "**/__pycache__/**": true,
        "**/.venv/**": true
    },
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
EOF'
else
  echo "✓ settings.json already exists, skipping"
fi

# Create tasks.json for common Python tasks (only if not exists)
if docker exec "${CONTAINER_NAME}" [ ! -f /workspace/.vscode/tasks.json ]; then
  echo "Creating tasks.json..."
  docker exec "${CONTAINER_NAME}" bash -c 'cat > /workspace/.vscode/tasks.json << "EOF"
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Install Requirements",
            "type": "shell",
            "command": "docker exec playground-python-3.12-stack pip install -r /workspace/requirements.txt",
            "problemMatcher": []
        },
        {
            "label": "Run Python Script",
            "type": "shell",
            "command": "docker exec playground-python-3.12-stack python /workspace/${relativeFile}",
            "problemMatcher": []
        },
        {
            "label": "Run Tests",
            "type": "shell",
            "command": "docker exec playground-python-3.12-stack pytest /workspace/tests",
            "problemMatcher": []
        }
    ]
}
EOF'
else
  echo "✓ tasks.json already exists, skipping"
fi

# Create sample Python project (only if not exists)
if docker exec "${CONTAINER_NAME}" [ ! -f /workspace/src/main.py ]; then
  echo "Creating sample Python project..."

  # Create project structure
  docker exec "${CONTAINER_NAME}" bash -c 'mkdir -p /workspace/src /workspace/tests'

  # Create main.py with sample code
  docker exec "${CONTAINER_NAME}" bash -c 'cat > /workspace/src/main.py << "EOF"
"""
Sample Python application for debugging demonstration.
"""

def greet(name: str) -> str:
    """Generate a greeting message."""
    return f"Hello, {name}! Welcome to Python Dev Stack."


def calculate_fibonacci(n: int) -> list[int]:
    """Calculate Fibonacci sequence up to n terms."""
    if n <= 0:
        return []
    elif n == 1:
        return [0]

    sequence = [0, 1]
    for i in range(2, n):
        sequence.append(sequence[i-1] + sequence[i-2])

    return sequence


def main():
    """Main application entry point."""
    print("🐍 Python Development Stack Demo")
    print("=" * 50)

    # Greeting demo
    name = "Developer"
    message = greet(name)
    print(f"\n{message}")

    # Fibonacci demo
    print("\nFibonacci Sequence (10 terms):")
    fib_sequence = calculate_fibonacci(10)
    print(fib_sequence)

    # Debugging breakpoint example
    # Set a breakpoint on the next line to test debugging
    result = sum(fib_sequence)
    print(f"\nSum of Fibonacci sequence: {result}")

    print("\n✅ Demo completed successfully!")


if __name__ == "__main__":
    main()
EOF'

# Create requirements.txt
docker exec "${CONTAINER_NAME}" bash -c 'cat > /workspace/requirements.txt << "EOF"
# Core development tools
debugpy==1.8.0
ipython==8.18.0
ipdb==0.13.13

# Testing
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0

# Code quality
black==23.12.0
pylint==3.0.3
flake8==6.1.0
mypy==1.7.1

# Web frameworks (optional)
fastapi==0.104.1
uvicorn[standard]==0.24.0
flask==3.0.0

# Common utilities
requests==2.31.0
python-dotenv==1.0.0
pydantic==2.5.2
EOF'

# Create README
docker exec "${CONTAINER_NAME}" bash -c 'cat > /workspace/README.md << "EOF"
# Python Development Stack

Complete Python development environment with VS Code Server and Python 3.12.

## 🚀 Quick Start

1. **Access Code Server**: http://localhost:8444
   - Password: `pythondev`

2. **Run the demo**:
   ```bash
   python src/main.py
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 🐛 Debugging

### Local Debugging (Current File)
1. Open `src/main.py` in Code Server
2. Set a breakpoint by clicking left of line number
3. Press F5 or use "Run and Debug" panel
4. Select "Python: Current File"

### Remote Debugging (Python container)
1. In Python container, install debugpy: `pip install debugpy`
2. Run your script with debugpy:
   ```bash
   python -m debugpy --listen 0.0.0.0:5678 --wait-for-client src/main.py
   ```
3. In Code Server, press F5 and select "Python: Remote Attach"
4. Debugger will connect to Python container

## 📦 Pre-configured Frameworks

Launch configurations included for:
- **Django**: For Django web applications
- **Flask**: For Flask web applications
- **FastAPI**: For FastAPI applications

## 🔧 VS Code Tasks

Use Ctrl+Shift+P → "Tasks: Run Task" to run:
- Install Requirements
- Run Python Script
- Run Tests

## 📁 Project Structure

```
/workspace/
├── src/           # Source code
├── tests/         # Test files
├── .vscode/       # VS Code configurations
└── requirements.txt
```

## 💡 Tips

- Code is shared between code-server and python-3.12-stack containers
- Use the integrated terminal in Code Server to run commands
- Python interpreter path: `/usr/local/bin/python`
- Extensions auto-installed: Python, Pylance, debugpy
EOF'
else
  echo "✓ Sample project already exists, skipping"
fi

# Fix ownership of all created files to match PUID:PGID (1000:1000)
echo "Setting correct permissions..."
docker exec "${CONTAINER_NAME}" chown -R 1000:1000 /workspace/.vscode 2>/dev/null || true
docker exec "${CONTAINER_NAME}" chown -R 1000:1000 /workspace/src 2>/dev/null || true
docker exec "${CONTAINER_NAME}" chown -R 1000:1000 /workspace/tests 2>/dev/null || true
docker exec "${CONTAINER_NAME}" chown 1000:1000 /workspace/requirements.txt 2>/dev/null || true
docker exec "${CONTAINER_NAME}" chown 1000:1000 /workspace/README.md 2>/dev/null || true

echo "✅ Code Server configured for Python development"
echo "🌐 Access at: http://localhost:8444"
echo "🔑 Password: pythondev"
echo "📁 Workspace: ./shared-volumes/python-dev-workspace"
echo "📁 Config: ./shared-volumes/python-dev-config"
echo "🐍 Python interpreter: /usr/bin/python3"
echo ""
echo "⚠️  NOTE: Python extensions may take 30-60 seconds to fully activate"
echo "   If you see 'debug type python not supported', wait and reload the window"
