# Python Dev Stack - Troubleshooting Guide

## Common Issues and Solutions

### 1. "Configured debug type 'python' is not supported"

**Cause**: Python extension not fully loaded yet.

**Solutions**:
1. **Wait 30-60 seconds** after container starts for extensions to install and activate
2. **Reload VS Code window**:
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
   - Type "Developer: Reload Window"
   - Press Enter
3. **Manually verify extensions**:
   - Click Extensions icon in sidebar (or `Ctrl+Shift+X`)
   - Search for "Python"
   - Check if "ms-python.python" is installed and enabled

**Prevention**: The init script now waits for code-server to be ready before installing extensions. If you still see this, just reload the window.

---

### 2. "EACCES: permission denied" when saving .vscode files

**Cause**: Files created with wrong ownership (root instead of user abc).

**Solution**: The init script now automatically fixes permissions with `chown 1000:1000`. If you still see this:

```bash
# Manually fix permissions
docker exec playground-code-server-python-stack chown -R 1000:1000 /workspace
```

**Prevention**: All files are now created with correct ownership automatically.

---

### 3. Extensions not installing

**Symptoms**: Extensions panel shows no Python extensions after several minutes.

**Solutions**:

1. **Manual installation** (from inside Code Server):
   ```
   Ctrl+Shift+X → Search "Python" → Install "Python" by Microsoft
   ```

2. **Command line installation** (from host):
   ```bash
   docker exec -u abc playground-code-server-python-stack bash -c \
     'export HOME=/config && /app/code-server/bin/code-server --extensions-dir /config/extensions --install-extension ms-python.python'
   ```

3. **Check extension directory**:
   ```bash
   # Inside container
   docker exec playground-code-server-python-stack ls -la /config/extensions/

   # From host (bind mount)
   ls -la shared-volumes/python-dev-config/extensions/
   ```

---

### 4. Remote debugging not connecting to Python container

**Symptoms**: "Python: Remote Attach" configuration fails to connect.

**Checks**:

1. **Verify Python container is running**:
   ```bash
   docker ps | grep python-3.12-stack
   ```

2. **Check debugpy is installed**:
   ```bash
   docker exec playground-python-3.12-stack pip show debugpy
   ```

3. **Verify port 5678 is listening**:
   ```bash
   docker exec playground-python-3.12-stack python -m debugpy --listen 0.0.0.0:5678 --wait-for-client /workspace/src/main.py
   ```

4. **Check network connectivity**:
   ```bash
   docker exec playground-code-server-python-stack ping -c 3 playground-python-3.12-stack
   ```

**Common mistake**: Not running `debug-script` or `python -m debugpy` in the Python container before connecting from Code Server.

---

### 5. Workspace folder is empty

**Cause**: Volume not mounted or sample project not created.

**Solutions**:

1. **Check volume mount**:
   ```bash
   docker exec playground-code-server-python-stack ls -la /workspace
   ```

2. **Manually create sample project**:
   ```bash
   docker exec playground-code-server-python-stack bash -c '
     mkdir -p /workspace/src /workspace/tests
     echo "print(\"Hello from Python!\")" > /workspace/src/main.py
     chown -R 1000:1000 /workspace
   '
   ```

3. **Restart the stack**:
   ```bash
   ./playground group stop Python-Dev-Stack
   ./playground group start Python-Dev-Stack
   ```

---

### 6. Web framework ports not accessible

**Symptoms**: Cannot access http://localhost:8001 or http://localhost:5001

**Checks**:

1. **Verify ports are mapped**:
   ```bash
   docker port playground-python-3.12-stack
   ```

2. **Check if service is running**:
   ```bash
   # For FastAPI
   docker exec playground-python-3.12-stack netstat -tuln | grep 8000

   # For Flask
   docker exec playground-python-3.12-stack netstat -tuln | grep 5000
   ```

3. **Start a test server**:
   ```bash
   docker exec playground-python-3.12-stack python -m http.server 8000
   ```
   Then access: http://localhost:8001

**Remember**:
- Internal port `8000` → External port `8001` (FastAPI/Django)
- Internal port `5000` → External port `5001` (Flask)

---

### 7. Code changes not reflected in debugger

**Cause**: Python caches bytecode in `__pycache__` directories.

**Solutions**:

1. **Set environment variable** (already configured in stack):
   ```bash
   PYTHONDONTWRITEBYTECODE=1
   ```

2. **Manually clear cache**:
   ```bash
   docker exec playground-python-3.12-stack find /workspace -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
   ```

3. **Restart debugger** after code changes (or use `--reload` for web frameworks)

---

### 8. "Module not found" errors

**Cause**: Dependencies not installed in Python container.

**Solutions**:

1. **Install requirements.txt**:
   ```bash
   docker exec playground-python-3.12-stack pip install -r /workspace/requirements.txt
   ```

2. **Install specific package**:
   ```bash
   docker exec playground-python-3.12-stack pip install package_name
   ```

3. **Use VS Code task** (from Code Server):
   - `Ctrl+Shift+P` → "Tasks: Run Task" → "Install Requirements"

---

## Quick Recovery Commands

### Full reset of workspace permissions
```bash
docker exec playground-code-server-python-stack chown -R 1000:1000 /workspace
```

### Reinstall Python extensions
```bash
docker exec -u abc playground-code-server-python-stack bash -c '
  export HOME=/config
  /app/code-server/bin/code-server --extensions-dir /config/extensions --install-extension ms-python.python
  /app/code-server/bin/code-server --extensions-dir /config/extensions --install-extension ms-python.vscode-pylance
  /app/code-server/bin/code-server --extensions-dir /config/extensions --install-extension ms-python.debugpy
'
```

### Verify stack health
```bash
# Check both containers are running
docker ps | grep -E "code-server-python-stack|python-3.12-stack"

# Check logs
./playground logs code-server-python-stack
./playground logs python-3.12-stack

# Test network connectivity
docker exec playground-code-server-python-stack ping -c 3 playground-python-3.12-stack
```

### Complete restart
```bash
# Stop stack
./playground group stop Python-Dev-Stack

# Optional: Remove workspace data (WARNING: deletes all files)
rm -rf shared-volumes/python-dev-workspace
rm -rf shared-volumes/python-dev-config

# Start fresh
./playground group start Python-Dev-Stack
```

---

## Getting Help

1. **Check logs**: `./playground logs <container-name>`
2. **Inspect container**: `docker exec -it playground-<container-name> bash`
3. **Verify configuration**: `cat custom.d/stack-dev-python.yml`
4. **Review init scripts**:
   - `scripts/code-server-python-stack/playground-code-server-python-stack-init.sh`
   - `scripts/python-3.12-stack/playground-python-3.12-stack-init.sh`

---

## Best Practices

1. **Wait for initialization**: Allow 1-2 minutes after starting stack for all services to be ready
2. **Use debug-script**: Always use `debug-script /workspace/script.py` for remote debugging
3. **Keep requirements.txt updated**: Document all pip packages you install
4. **Reload VS Code window**: After installing new extensions, reload the window
5. **Check container logs**: Most issues are visible in container logs

---

Last updated: 2025-10-30
