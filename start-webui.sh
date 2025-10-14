#!/bin/bash

#############################################
# Simplified Web Panel Starter (Monochrome)
# Advanced logging & process management
#############################################

# =============================================================================
# Configuration Section
# =============================================================================

readonly PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly VENV_BASE_DIR="${PROJECT_DIR}/venv/environments"
readonly REQ_FILE="${PROJECT_DIR}/venv/requirements.txt"
readonly LOG_FILE="${PROJECT_DIR}/venv/web.log"
readonly ERROR_LOG_FILE="${PROJECT_DIR}/venv/web_error.log"
readonly JSON_LOG_FILE="${PROJECT_DIR}/venv/web.jsonl"
readonly PID_FILE="${PROJECT_DIR}/venv/web.pid"
readonly PORT=8000

# =============================================================================
# Detect Python
# =============================================================================
detect_python() {
    local python_cmd
    for cmd in python3.12 python3.11 python3.10 python3; do
        if command -v "$cmd" >/dev/null 2>&1; then
            python_cmd="$cmd"
            break
        fi
    done
    [[ -z "$python_cmd" ]] && log_error "No Python interpreter found. Please install Python 3.10+"
    local version=$("$python_cmd" -c "import sys; print(f'python-{sys.version_info.major}.{sys.version_info.minor}')")
    echo "$python_cmd:$version"
}

python_info=$(detect_python)
readonly PYTHON_CMD="${python_info%:*}"
readonly VENV_NAME="${python_info#*:}"
readonly VENV_PATH="${VENV_BASE_DIR}/${VENV_NAME}"

# =============================================================================
# Log Configuration
# =============================================================================

LOG_LEVEL="${LOG_LEVEL:-INFO}"
declare -A LOG_PRIORITY=(
    [DEBUG]=0 [INFO]=1 [WARNING]=2 [ERROR]=3 [CRITICAL]=4
)
declare -A LOG_LEVELS=(
    ["DEBUG"]="debug:DEBUG"
    ["INFO"]="info:WARNING"
    ["WARNING"]="warning:ERROR"
    ["ERROR"]="error:CRITICAL"
    ["CRITICAL"]="critical:CRITICAL"
)

# =============================================================================
# Logging System (Monochrome)
# =============================================================================

# I colori ANSI sono stati rimossi.

rotate_logs() {
    local max_size=1048576  # 1 MB
    local backup_count=5
    if [[ -f "$LOG_FILE" && $(stat -c%s "$LOG_FILE") -ge $max_size ]]; then
        mv "$LOG_FILE" "${LOG_FILE}.0"
        for ((i=backup_count; i>0; i--)); do
            [[ -f "${LOG_FILE}.$((i-1))" ]] && mv "${LOG_FILE}.$((i-1))" "${LOG_FILE}.$i"
        done
        touch "$LOG_FILE"
    fi
}

should_log() {
    local msg_level="$1"
    [[ ${LOG_PRIORITY[$msg_level]} -ge ${LOG_PRIORITY[$LOG_LEVEL]} ]]
}

log_json() {
    local level="$1"
    local message="$2"
    local timestamp
    timestamp=$(date -Iseconds)
    # Assicurati che il messaggio sia escapato per JSON
    local escaped_message
    escaped_message=$(echo "$message" | sed 's/"/\\"/g')
    echo "{\"timestamp\":\"$timestamp\",\"level\":\"$level\",\"pid\":$$,\"message\":\"$escaped_message\"}" >> "$JSON_LOG_FILE"
}

log() {
    local level="$1"
    shift
    local message="$*"
    should_log "$level" || return 0
    rotate_logs

    local timestamp caller
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    caller="${FUNCNAME[1]:-main}"

    # La logica di selezione del colore è stata rimossa.

    local output="[$timestamp] [PID:$$] [$caller] [$level] $message"
    
    # Stampa in testo standard sulla console e salva nel log principale.
    printf "%s\n" "$output" | tee -a "$LOG_FILE"

    [[ "$level" =~ ^(ERROR|CRITICAL)$ ]] && echo "$output" >> "$ERROR_LOG_FILE"
    log_json "$level" "$message"
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
    log_info "Log setup:"
    log_info "  Level: $LOG_LEVEL"
    log_info "  File: $LOG_FILE"
    log_info "  Error file: $ERROR_LOG_FILE"
    log_info "  JSON file: $JSON_LOG_FILE"
}

show_environment() {
    log_info "Environment:"
    log_info "  Python: $PYTHON_CMD"
    log_info "  Virtualenv: $VENV_NAME"
    log_info "  Project: $PROJECT_DIR"
}

kill_port() {
    local port=$1
    local pids
    pids=$(lsof -ti:"$port" 2>/dev/null)
    if [[ -n "$pids" ]]; then
        log_warning "Killing processes on port $port: $pids"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

check_dependencies() {
    local deps=("$PYTHON_CMD" "docker" "lsof")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            log_error "$dep not found. Please install it."
        fi
    done
}

create_virtualenv() {
    log_info "Setting up Python virtual environment..."
    [[ -d "$VENV_BASE_DIR" ]] && rm -rf "$VENV_BASE_DIR"
    mkdir -p "$VENV_BASE_DIR" "$(dirname "$LOG_FILE")"
    "$PYTHON_CMD" -m venv "$VENV_PATH" || log_error "Failed to create virtual environment"
    source "$VENV_PATH/bin/activate"
    pip install --upgrade pip --quiet || log_error "Failed to upgrade pip"
}

install_dependencies() {
    log_info "Installing dependencies..."
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
    local file="${PROJECT_DIR}/venv/python_logging.conf"
    IFS=':' read -r UVICORN_LOG_LEVEL PYTHON_LOG_LEVEL <<< "${LOG_LEVELS[$LOG_LEVEL]}"
    cat > "$file" << EOF
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
    echo "$file"
}

# =============================================================================
# Web Server Management
# =============================================================================

start_server() {
    log_info "Starting web server at http://localhost:$PORT..."
    IFS=':' read -r UVICORN_LOG_LEVEL PYTHON_LOG_LEVEL <<< "${LOG_LEVELS[$LOG_LEVEL]}"
    local python_log_config
    python_log_config=$(create_python_log_config)

    local uvicorn_args=(
        "src.web.app:app"
        "--host" "0.0.0.0"
        "--port" "$PORT"
        "--log-level" "$UVICORN_LOG_LEVEL"
        "--log-config" "$python_log_config"
    )
    [[ "$LOG_LEVEL" != "DEBUG" ]] && uvicorn_args+=("--no-access-log")

    export DOCKER_LOG_LEVEL="error"
    export PYTHONWARNINGS="ignore"
    export PYTHONUNBUFFERED=1

    log_info "Press Ctrl+C to stop"

    (
        source "$VENV_PATH/bin/activate"
        # Il codice che colorava l'output di Uvicorn è stato rimosso. 
        # L'output va direttamente su console e log in testo standard.
        uvicorn "${uvicorn_args[@]}" 2>&1 | tee -a "$LOG_FILE"
    ) &
    WEB_PID=$!
    echo "$WEB_PID" > "$PID_FILE"

    wait "$WEB_PID"
    EXIT_CODE=$?
    [[ $EXIT_CODE -ne 0 ]] && log "ERROR" "Web server exited with code $EXIT_CODE (see $LOG_FILE)" || log_info "Web server stopped cleanly."
}

cleanup() {
    log_info "Interrupt received, stopping web server..."
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if ps -p "$pid" >/dev/null 2>&1; then
            log_info "Stopping process $pid..."
            kill "$pid" 2>/dev/null
            wait "$pid" 2>/dev/null
        fi
        rm -f "$PID_FILE"
    fi
    kill_port "$PORT"
    log_info "Cleanup completed. Bye!"
    exit 0
}

show_help() {
    cat << EOF
Usage: $0 [OPTIONS]
  --debug           Enable debug logging
  --log-level LEVEL Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  --help            Show this help message
EOF
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --debug) LOG_LEVEL="DEBUG"; shift ;;
            --log-level) LOG_LEVEL="$2"; shift 2 ;;
            --help) show_help; exit 0 ;;
            *) log_error "Unknown option: $1" ;;
        esac
    done
}

main() {
    parse_arguments "$@"
    # Pulisci i log all'inizio
    rm -f "$LOG_FILE" "$ERROR_LOG_FILE" "$JSON_LOG_FILE"
    mkdir -p "$PROJECT_DIR/venv"
    trap cleanup SIGINT SIGTERM
    setup_logging
    show_environment
    check_dependencies
    kill_port "$PORT"
    create_virtualenv
    install_dependencies
    [[ ! -f "$PROJECT_DIR/src/web/app.py" ]] && log_error "Missing app.py"
    start_server
}

main "$@"