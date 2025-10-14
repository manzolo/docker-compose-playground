#!/bin/bash

#############################################
# Simplified Web Panel Starter
# Fixed port cleanup and proper process management
#############################################

# =============================================================================
# Configuration Section
# =============================================================================

# Directory dello script
readonly PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly VENV_BASE_DIR="${PROJECT_DIR}/venv/environments"
readonly REQ_FILE="${PROJECT_DIR}/venv/requirements.txt"
readonly LOG_FILE="${PROJECT_DIR}/venv/web.log"
readonly PID_FILE="${PROJECT_DIR}/venv/web.pid"
readonly PORT=8000

# Rileva automaticamente Python
detect_python() {
    local python_cmd
    # Prova python3.12, python3.11, python3.10, poi python3
    for cmd in python3.12 python3.11 python3.10 python3; do
        if command -v "$cmd" >/dev/null 2>&1; then
            python_cmd="$cmd"
            break
        fi
    done
    
    if [[ -z "$python_cmd" ]]; then
        log_error "No Python interpreter found. Please install Python 3.10+"
    fi
    
    # Estrai versione per il nome del venv
    local version=$("$python_cmd" -c "import sys; print(f'python-{sys.version_info.major}.{sys.version_info.minor}')")
    
    echo "$python_cmd:$version"
}

# Configura Python e VENV_PATH
python_info=$(detect_python)
readonly PYTHON_CMD="${python_info%:*}"
readonly VENV_NAME="${python_info#*:}"
readonly VENV_PATH="${VENV_BASE_DIR}/${VENV_NAME}"

# Configurazione del livello di log
LOG_LEVEL="${LOG_LEVEL:-INFO}"
declare -A LOG_LEVELS=(
    ["DEBUG"]="debug:DEBUG"
    ["INFO"]="info:WARNING" 
    ["WARNING"]="warning:ERROR"
    ["ERROR"]="error:CRITICAL"
    ["CRITICAL"]="critical:CRITICAL"
)

# =============================================================================
# Logging Functions
# =============================================================================

log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    if [[ "$level" == "DEBUG" && "$LOG_LEVEL" != "DEBUG" ]]; then
        return
    fi
    
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

log_debug() { log "DEBUG" "$*"; }
log_info() { log "INFO" "$*"; }
log_warning() { log "WARNING" "$*"; }
log_error() { log "ERROR" "$*"; exit 1; }

# =============================================================================
# Utility Functions  
# =============================================================================

setup_logging() {
    IFS=':' read -r UVICORN_LOG_LEVEL PYTHON_LOG_LEVEL <<< "${LOG_LEVELS[$LOG_LEVEL]:-info:WARNING}"
    
    log_info "Log configuration:"
    log_info "  Script level: $LOG_LEVEL"
    log_info "  Uvicorn level: $UVICORN_LOG_LEVEL"
    log_info "  Python level: $PYTHON_LOG_LEVEL"
    log_info "  Log file: $LOG_FILE"
}

show_environment() {
    log_info "Environment:"
    log_info "  Python: $PYTHON_CMD"
    log_info "  Virtualenv: $VENV_NAME"
    log_info "  Project: $PROJECT_DIR"
}

kill_port() {
    local port=$1
    log_debug "Checking for processes on port $port..."
    
    local pids=$(lsof -ti:"$port" 2>/dev/null)
    if [[ -n "$pids" ]]; then
        log_info "Killing processes on port $port: $pids"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 1
    else
        log_debug "No processes found on port $port"
    fi
}

check_dependencies() {
    local deps=("$PYTHON_CMD" "docker")
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            log_error "$dep not found. Please install it."
        fi
    done
    
    if ! command -v lsof >/dev/null 2>&1; then
        log_info "Installing lsof for port management..."
        sudo apt-get install -y lsof >/dev/null 2>&1
    fi
}

create_virtualenv() {
    log_info "Setting up Python virtual environment..."
    log_info "Using $PYTHON_CMD -> $VENV_NAME"
    
    # Clean existing venv
    [[ -d "$VENV_BASE_DIR" ]] && rm -rf "$VENV_BASE_DIR"
    
    # Create directories
    mkdir -p "$VENV_BASE_DIR" "$(dirname "$LOG_FILE")"
    
    # Create virtual environment
    "$PYTHON_CMD" -m venv "$VENV_PATH" || log_error "Failed to create virtual environment"
    
    # Activate and setup
    source "$VENV_PATH/bin/activate"
    pip install --upgrade pip --quiet || log_error "Failed to upgrade pip"
}

install_dependencies() {
    log_info "Installing Python dependencies..."
    
    cat > "$REQ_FILE" << 'EOF'
typer>=0.12.5
docker>=7.1.0
pyyaml>=6.0.2
fastapi>=0.115.0
uvicorn[standard]>=0.30.6
jinja2>=3.1.4
EOF

    pip install -r "$REQ_FILE" --quiet || log_error "Failed to install dependencies"
}

create_python_log_config() {
    local log_config_file="${PROJECT_DIR}/venv/python_logging.conf"
    IFS=':' read -r UVICORN_LOG_LEVEL PYTHON_LOG_LEVEL <<< "${LOG_LEVELS[$LOG_LEVEL]}"
    
    cat > "$log_config_file" << EOF
[loggers]
keys=root,uvicorn,uvicorn.access,uvicorn.error

[handlers]
keys=consoleHandler

[formatters]
keys=simpleFormatter

[logger_root]
level=$PYTHON_LOG_LEVEL
handlers=consoleHandler

[logger_uvicorn]
level=$PYTHON_LOG_LEVEL
handlers=consoleHandler
qualname=uvicorn
propagate=0

[logger_uvicorn.access]
level=$PYTHON_LOG_LEVEL
handlers=consoleHandler
qualname=uvicorn.access
propagate=0

[logger_uvicorn.error]
level=$PYTHON_LOG_LEVEL
handlers=consoleHandler
qualname=uvicorn.error
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=$PYTHON_LOG_LEVEL
formatter=simpleFormatter
args=(sys.stderr,)

[formatter_simpleFormatter]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
datefmt=%Y-%m-%d %H:%M:%S
EOF
    
    echo "$log_config_file"
}

start_server() {
    log_info "Starting web server at http://localhost:$PORT..."
    log_info "Press Ctrl+C to stop"

    IFS=':' read -r UVICORN_LOG_LEVEL PYTHON_LOG_LEVEL <<< "${LOG_LEVELS[$LOG_LEVEL]}"
    local python_log_config=$(create_python_log_config)
    
    local uvicorn_args=(
        "src.web.app:app"
        "--host" "0.0.0.0"
        "--port" "$PORT"
        "--log-level" "$UVICORN_LOG_LEVEL"
        "--log-config" "$python_log_config"
    )
    
    [[ "$LOG_LEVEL" != "DEBUG" ]] && uvicorn_args+=("--no-access-log")
    
    # Set Python environment variables
    export DOCKER_LOG_LEVEL="error"
    export PYTHONWARNINGS="ignore"
    [[ "$LOG_LEVEL" != "DEBUG" ]] && export PYTHONUNBUFFERED=1
    
    log_debug "Starting uvicorn with: ${uvicorn_args[*]}"
    
    # Start server
    uvicorn "${uvicorn_args[@]}" 2>&1 | tee -a "$LOG_FILE" &
    WEB_PID=$!
    echo "$WEB_PID" > "$PID_FILE"
    
    # Verify startup
    sleep 2
    if ! ps -p "$WEB_PID" >/dev/null 2>&1; then
        log_error "Failed to start web server. Check $LOG_FILE"
    fi
    
    log_info "Web server running (PID $WEB_PID)"
    log_info "Access: http://localhost:$PORT"
    
    wait "$WEB_PID"
}

# =============================================================================
# Cleanup Functions
# =============================================================================

cleanup() {
    log_info "Received interrupt signal, cleaning up..."
    
    # Stop web server
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" >/dev/null 2>&1; then
            log_info "Stopping web server (PID $pid)..."
            kill "$pid" 2>/dev/null
            sleep 2
            ps -p "$pid" >/dev/null 2>&1 && kill -9 "$pid" 2>/dev/null
        fi
        rm -f "$PID_FILE"
    fi
    
    # Clean port and venv
    kill_port "$PORT"
    [[ -d "$VENV_BASE_DIR" ]] && rm -rf "$VENV_BASE_DIR"
    
    log_info "Cleanup completed"
    exit 0
}

# =============================================================================
# CLI Functions
# =============================================================================

show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
  --debug          Enable debug logging
  --log-level LEVEL Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  --help           Show this help message

Environment variables:
  LOG_LEVEL        Set log level (default: INFO)

Examples:
  $0                    # Run with INFO level
  $0 --debug           # Run with DEBUG level  
  LOG_LEVEL=DEBUG $0   # Run with DEBUG level
  $0 --log-level DEBUG # Run with DEBUG level
EOF
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --debug)
                LOG_LEVEL="DEBUG"
                shift
                ;;
            --log-level)
                if [[ -n "$2" ]]; then
                    LOG_LEVEL="$2"
                    shift 2
                else
                    log_error "--log-level requires a value"
                fi
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                ;;
        esac
    done
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    parse_arguments "$@"
    
    # Initialize
    rm -f "$LOG_FILE"
    trap cleanup SIGINT SIGTERM
    setup_logging
    show_environment
    
    # Pre-flight checks
    check_dependencies
    kill_port "$PORT"
    
    # Setup environment
    create_virtualenv
    install_dependencies
    
    # Verify application
    [[ ! -f "$PROJECT_DIR/src/web/app.py" ]] && \
        log_error "Web module not found at $PROJECT_DIR/src/web/app.py"
    
    # Start server
    start_server
}

# Entry point
main "$@"