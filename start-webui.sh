#!/bin/bash

#############################################
# Simplified Web Panel Starter
# Fixed port cleanup and proper process management
#############################################

# Directory dello script
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_BASE_DIR="${PROJECT_DIR}/venv/environments"
VENV_NAME="python-3.12"
VENV_PATH="${VENV_BASE_DIR}/${VENV_NAME}"
REQ_FILE="${PROJECT_DIR}/venv/requirements.txt"
LOG_FILE="${PROJECT_DIR}/venv/web.log"
PID_FILE="${PROJECT_DIR}/venv/web.pid"
PORT=8000

rm -f $LOG_FILE

# Funzioni di logging
log_info() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*" | tee -a "$LOG_FILE"
}

log_error() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" | tee -a "$LOG_FILE"
  exit 1
}

# Funzione per killare processi sulla porta
kill_port() {
  local port=$1
  log_info "Checking for processes on port $port..."
  
  # Trova e killa processi sulla porta
  local pids=$(lsof -ti:$port 2>/dev/null)
  if [ -n "$pids" ]; then
    log_info "Killing processes on port $port: $pids"
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 1
  fi
}

# Funzione di cleanup
cleanup() {
  log_info "Received Ctrl+C, stopping web server and cleaning up..."
  
  # Kill il processo se esiste
  if [ -f "$PID_FILE" ]; then
    local pid=$(cat "$PID_FILE")
    if ps -p "$pid" >/dev/null 2>&1; then
      log_info "Stopping web server (PID $pid)..."
      kill "$pid" 2>/dev/null
      sleep 2
      if ps -p "$pid" >/dev/null 2>&1; then
        log_info "Forcing termination..."
        kill -9 "$pid" 2>/dev/null
      fi
    fi
    rm -f "$PID_FILE"
  fi
  
  # Assicurati che la porta sia libera
  kill_port $PORT
  
  # Rimuovi virtual environment
  if [ -d "$VENV_BASE_DIR" ]; then
    log_info "Removing virtual environment..."
    rm -rf "$VENV_BASE_DIR"
  fi
  
  log_info "Cleanup completed"
  exit 0
}

# Imposta il trap per Ctrl+C
trap cleanup SIGINT SIGTERM

# Verifica dipendenze
if ! command -v python3 >/dev/null 2>&1; then
  log_error "Python3 not found. Install: sudo apt-get install python3"
fi
if ! command -v docker >/dev/null 2>&1; then
  log_error "Docker not found. Install: sudo apt-get install docker.io"
fi
if ! command -v lsof >/dev/null 2>&1; then
  log_info "Installing lsof for port management..."
  sudo apt-get install -y lsof >/dev/null 2>&1
fi

# Killa eventuali processi sulla porta prima di iniziare
kill_port $PORT

# Cancella venv esistente
if [ -d "$VENV_BASE_DIR" ]; then
  log_info "Removing existing venv..."
  rm -rf "$VENV_BASE_DIR"
fi

# Crea directory
mkdir -p "$VENV_BASE_DIR" "$(dirname "$LOG_FILE")"

# Crea virtual environment
log_info "Creating Python virtual environment..."
python3 -m venv "$VENV_PATH" || log_error "Failed to create venv"

# Attiva venv
source "$VENV_PATH/bin/activate"

# Aggiorna pip
log_info "Upgrading pip..."
pip install --upgrade pip --quiet || log_error "Failed to upgrade pip"

# Crea requirements.txt
log_info "Creating requirements.txt..."
cat > "$REQ_FILE" << 'EOF'
typer>=0.12.5
docker>=7.1.0
pyyaml>=6.0.2
fastapi>=0.115.0
uvicorn[standard]>=0.30.6
jinja2>=3.1.4
EOF

# Installa dipendenze
log_info "Installing dependencies..."
pip install -r "$REQ_FILE" --quiet || log_error "Failed to install dependencies"

# Verifica modulo web
if [ ! -f "$PROJECT_DIR/src/web/app.py" ]; then
  log_error "Web module not found at $PROJECT_DIR/src/web/app.py"
fi

# Avvia server
log_info "Starting web server at http://localhost:$PORT..."
log_info "Press Ctrl+C to stop"

uvicorn src.web.app:app --host 0.0.0.0 --port $PORT 2>&1 | tee -a "$LOG_FILE" &
WEB_PID=$!
echo "$WEB_PID" > "$PID_FILE"

# Verifica avvio
sleep 2
if ! ps -p "$WEB_PID" >/dev/null 2>&1; then
  log_error "Failed to start web server. Check $LOG_FILE"
fi

log_info "Web server running (PID $WEB_PID)"
log_info "Access: http://localhost:$PORT"

# Aspetta che il processo termini
wait "$WEB_PID"