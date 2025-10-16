#!/bin/bash

#############################################
# Improved Web Panel Starter
# Enhanced process management & reliability
#############################################

set -o pipefail

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
readonly HEALTH_CHECK_URL="http://localhost:${PORT}/"
readonly HEALTH_CHECK_TIMEOUT=30
readonly STARTUP_TIMEOUT=60

# Process management
WEB_PID=""
EXIT_CODE=0
SHUTDOWN_IN_PROGRESS=false

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
    [[ -z "$python_cmd" ]] && { log_error "No Python interpreter found. Please install Python 3.10+"; }
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
# Logging System
# =============================================================================

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

    local output="[$timestamp] [PID:$$] [$caller] [$level] $message"
    
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
    log_info "Log configuration:"
    log_info "  Level: $LOG_LEVEL"
    log_info "  File: $LOG_FILE"
    log_info "  Error file: $ERROR_LOG_FILE"
    log_info "  JSON file: $JSON_LOG_FILE"
}

show_environment() {
    log_info "Environment:"
    log_info "  Python: $PYTHON_CMD (detected)"
    log_info "  Virtualenv: $VENV_NAME"
    log_info "  Project: $PROJECT_DIR"
    log_info "  Port: $PORT"
}

kill_port() {
    local port=$1
    local pids
    pids=$(lsof -ti:"$port" 2>/dev/null)
    if [[ -n "$pids" ]]; then
        log_warning "Found processes on port $port. Terminating gracefully first..."
        echo "$pids" | xargs kill -TERM 2>/dev/null || true
        sleep 2
        # Force kill if still running
        pids=$(lsof -ti:"$port" 2>/dev/null)
        if [[ -n "$pids" ]]; then
            log_warning "Force killing remaining processes on port $port"
            echo "$pids" | xargs kill -9 2>/dev/null || true
        fi
        sleep 1
    fi
}

check_dependencies() {
    local deps=("$PYTHON_CMD" "docker" "lsof" "curl")
    local missing=()
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            missing+=("$dep")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${missing[*]}"
    fi
    
    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon is not running. Please start Docker."
    fi
}

create_virtualenv() {
    log_info "Setting up Python virtual environment..."
    [[ -d "$VENV_BASE_DIR" ]] && rm -rf "$VENV_BASE_DIR"
    mkdir -p "$VENV_BASE_DIR" "$(dirname "$LOG_FILE")"
    
    if ! "$PYTHON_CMD" -m venv "$VENV_PATH"; then
        log_error "Failed to create virtual environment"
    fi
    
    source "$VENV_PATH/bin/activate"
    
    if ! pip install --upgrade pip --quiet; then
        log_error "Failed to upgrade pip"
    fi
}

install_dependencies() {
    log_info "Installing dependencies from requirements..."
    cat > "$REQ_FILE" << 'EOF'
typer>=0.12.5
docker>=7.1.0
pyyaml>=6.0.2
fastapi>=0.115.0
uvicorn[standard]>=0.30.6
jinja2>=3.1.4
EOF
    
    if ! pip install -r "$REQ_FILE" --quiet; then
        log_error "Failed to install dependencies"
    fi
    
    log_info "Dependencies installed successfully"
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

health_check() {
    local elapsed=0
    log_info "Waiting for server to be ready (timeout: ${HEALTH_CHECK_TIMEOUT}s)..."
    
    while [[ $elapsed -lt $HEALTH_CHECK_TIMEOUT ]]; do
        if curl -sf "$HEALTH_CHECK_URL" >/dev/null 2>&1; then
            log_info "Server is healthy and ready!"
            return 0
        fi
        
        # Check if process is still alive
        if ! ps -p "$WEB_PID" >/dev/null 2>&1; then
            log_error "Server process died before becoming healthy. Check logs."
        fi
        
        sleep 1
        ((elapsed++))
    done
    
    log_error "Server health check timed out after ${HEALTH_CHECK_TIMEOUT}s"
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
        uvicorn "${uvicorn_args[@]}" 2>&1 | tee -a "$LOG_FILE"
    ) &
    
    WEB_PID=$!
    echo "$WEB_PID" > "$PID_FILE"
    log_info "Server process started with PID: $WEB_PID"
    
    # Wait for server to be healthy
    if ! health_check; then
        kill "$WEB_PID" 2>/dev/null || true
        exit 1
    fi
    
    # Monitor the process
    wait "$WEB_PID"
    EXIT_CODE=$?
    
    if [[ $EXIT_CODE -eq 0 ]]; then
        log_info "Web server stopped cleanly"
    else
        log_error "Web server exited with code $EXIT_CODE (see $LOG_FILE for details)"
    fi
}

graceful_shutdown() {
    if [[ "$SHUTDOWN_IN_PROGRESS" == true ]]; then
        return
    fi
    SHUTDOWN_IN_PROGRESS=true
    
    log_info "Interrupt received. Starting graceful shutdown..."
    
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        
        if ps -p "$pid" >/dev/null 2>&1; then
            log_info "Sending SIGTERM to process $pid for graceful shutdown..."
            kill -TERM "$pid" 2>/dev/null
            
            # Wait up to 15 seconds for graceful shutdown
            local wait_count=0
            while ps -p "$pid" >/dev/null 2>&1 && [[ $wait_count -lt 15 ]]; do
                sleep 1
                ((wait_count++))
            done
            
            # Force kill if still running
            if ps -p "$pid" >/dev/null 2>&1; then
                log_warning "Process did not exit gracefully. Force killing..."
                kill -9 "$pid" 2>/dev/null || true
            fi
        fi
        
        rm -f "$PID_FILE"
    fi
    
    kill_port "$PORT"
    log_info "Shutdown completed. Bye!"
    exit 0
}

show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
  --debug              Enable debug logging (sets log level to DEBUG)
  --log-level LEVEL    Set log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
                       (default: INFO)
  --help               Show this help message

Examples:
  $0                   # Run with default settings
  $0 --debug           # Run with debug logging
  $0 --log-level DEBUG # Run with debug level

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
                LOG_LEVEL="$2"
                if ! [[ "$LOG_LEVEL" =~ ^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$ ]]; then
                    echo "Invalid log level: $LOG_LEVEL" >&2
                    show_help
                    exit 1
                fi
                shift 2
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                echo "Unknown option: $1" >&2
                show_help
                exit 1
                ;;
        esac
    done
}

# =============================================================================
# Main
# =============================================================================

main() {
    parse_arguments "$@"
    
    # Clean logs at startup
    rm -f "$LOG_FILE" "$ERROR_LOG_FILE" "$JSON_LOG_FILE"
    mkdir -p "$PROJECT_DIR/venv"
    
    # Set up signal handlers
    trap graceful_shutdown SIGINT SIGTERM EXIT
    
    setup_logging
    show_environment
    check_dependencies
    kill_port "$PORT"
    create_virtualenv
    install_dependencies
    
    # Verify app.py exists
    if [[ ! -f "$PROJECT_DIR/src/web/app.py" ]]; then
        log_error "Missing application file: $PROJECT_DIR/src/web/app.py"
    fi
    
    start_server
}

main "$@"