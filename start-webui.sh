#!/bin/bash

#############################################
# Simplified Web Panel Starter
# Deletes existing venv, creates a new one, installs dependencies,
# starts the web server with live logs, and cleans up on exit
# Independent from Docker Playground
#############################################

# Directory dello script
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_BASE_DIR="${PROJECT_DIR}/venv/environments"
VENV_NAME="python-3.12"
VENV_PATH="${VENV_BASE_DIR}/${VENV_NAME}"
REQ_FILE="${PROJECT_DIR}/venv/requirements.txt"
LOG_FILE="${PROJECT_DIR}/venv/web.log"
PID_FILE="${PROJECT_DIR}/venv/web.pid"

# Funzioni di logging
log_info() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*" | tee -a "$LOG_FILE"
}

log_error() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" | tee -a "$LOG_FILE"
  exit 1
}

# Funzione di cleanup
cleanup() {
  log_info "Received Ctrl+C, stopping web server and cleaning up..."
  if [ -f "$PID_FILE" ]; then
    local pid=$(cat "$PID_FILE")
    if ps -p "$pid" >/dev/null 2>&1; then
      kill "$pid" 2>/dev/null
      sleep 1
      if ps -p "$pid" >/dev/null 2>&1; then
        log_info "Forcing termination of web server (PID $pid)..."
        kill -9 "$pid" 2>/dev/null
      fi
    fi
    rm -f "$PID_FILE"
  fi
  log_info "Removing virtual environment at $VENV_BASE_DIR..."
  rm -rf "$VENV_BASE_DIR"
  log_info "Cleanup completed"
  exit 0
}

# Imposta il trap per Ctrl+C
trap cleanup SIGINT

# Verifica dipendenze
if ! command -v python3 >/dev/null 2>&1; then
  log_error "Python3 not found on host. Install it with 'sudo apt-get install python3'"
fi
if ! python3 -m venv --help >/dev/null 2>&1; then
  log_error "Python venv module not available. Install it with 'sudo apt-get install python3-venv'"
fi
if ! command -v docker >/dev/null 2>&1; then
  log_error "Docker not found on host. Install it with 'sudo apt-get install docker.io'"
fi

# Cancella la directory venv esistente
if [ -d "$VENV_BASE_DIR" ]; then
  log_info "Removing existing venv directory at $VENV_BASE_DIR..."
  rm -rf "$VENV_BASE_DIR"
fi

# Crea la directory venv
mkdir -p "$VENV_BASE_DIR" "$(dirname "$LOG_FILE")"

# Crea il virtual environment
log_info "Creating Python virtual environment at $VENV_PATH..."
python3 -m venv "$VENV_PATH" 2>/tmp/venv_error.log
if [ $? -ne 0 ]; then
  local error_msg=$(cat /tmp/venv_error.log)
  log_error "Failed to create virtual environment: $error_msg"
fi
rm -f /tmp/venv_error.log

# Attiva il virtual environment
source "$VENV_PATH/bin/activate"

# Aggiorna pip
log_info "Upgrading pip..."
pip install --upgrade pip --quiet 2>/tmp/venv_error.log
if [ $? -ne 0 ]; then
  local error_msg=$(cat /tmp/venv_error.log)
  log_error "Failed to upgrade pip: $error_msg"
fi
rm -f /tmp/venv_error.log

# Crea requirements.txt
log_info "Creating requirements.txt at $REQ_FILE..."
cat > "$REQ_FILE" << EOF2
typer>=0.12.5
docker>=7.1.0
pyyaml>=6.0.2
fastapi>=0.115.0
uvicorn[standard]>=0.30.6
jinja2>=3.1.4
EOF2

# Installa le dipendenze
log_info "Installing dependencies from $REQ_FILE..."
pip install -r "$REQ_FILE" --quiet 2>/tmp/venv_error.log
if [ $? -ne 0 ]; then
  local error_msg=$(cat /tmp/venv_error.log)
  log_error "Failed to install dependencies: $error_msg"
fi
rm -f /tmp/venv_error.log

# Verifica se il modulo web esiste
if [ ! -f "$PROJECT_DIR/src/web/app.py" ]; then
  log_error "Web panel module not found at $PROJECT_DIR/src/web/app.py"
fi

# Avvia il server web
log_info "Starting web server at http://localhost:8000..."
uvicorn src.web.app:app --host 0.0.0.0 --port 8000 2>&1 | tee -a "$LOG_FILE" &
WEB_PID=$!
echo "$WEB_PID" > "$PID_FILE"

# Verifica se il server si è avviato correttamente
sleep 2
if ! ps -p "$WEB_PID" >/dev/null 2>&1; then
  log_error "Failed to start web server. Check $LOG_FILE for details"
fi

log_info "Web server running with PID $WEB_PID. Press Ctrl+C to stop and cleanup."
wait "$WEB_PID"