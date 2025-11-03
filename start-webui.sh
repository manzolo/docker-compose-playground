#!/usr/bin/env bash

# Improved Web Panel Starter
# Version: 2.0.0
# Author: xAI
# License: MIT
# Description: A robust script to start a Python-based web server with process management, logging, and health checks.

#############################################
# Configuration Section
#############################################

set -o pipefail

readonly PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load configuration from .env file if present
if [[ -f "${PROJECT_DIR}/.env" ]]; then
    set -a
    source "${PROJECT_DIR}/.env"
    set +a
fi
readonly VENV_BASE_DIR="${PROJECT_DIR}/venv/environments"
readonly REQ_FILE="${PROJECT_DIR}/venv/requirements.txt"
readonly REQ_CHECKSUM_FILE="${PROJECT_DIR}/venv/.requirements.checksum"
readonly LOG_FILE="${PROJECT_DIR}/venv/web.log"
readonly ERROR_LOG_FILE="${PROJECT_DIR}/venv/web_error.log"
readonly JSON_LOG_FILE="${PROJECT_DIR}/venv/web.jsonl"
readonly PID_FILE="${PROJECT_DIR}/venv/web.pid"
readonly PORT="${PORT:-8000}"
readonly HEALTH_CHECK_ENDPOINT="${HEALTH_CHECK_ENDPOINT:-/}"
readonly HEALTH_CHECK_URL="http://localhost:${PORT}${HEALTH_CHECK_ENDPOINT}"
readonly HEALTH_CHECK_TIMEOUT=30
readonly STARTUP_TIMEOUT=60
readonly USE_DOCKER="${USE_DOCKER:-false}"
readonly INSTALL_RETRIES=3
readonly INSTALL_RETRY_WAIT=5

# Process management
WEB_PID=""
MONITOR_PID=""
EXIT_CODE=0
SHUTDOWN_IN_PROGRESS=false
TAIL_PROCESS_PID=""
ENABLE_TAIL=false
FORCE_REINSTALL=false

# Log configuration
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

#############################################
# Logging System
#############################################

rotate_logs() {
    local max_size=1048576  # 1 MB
    local backup_count=5
    local stat_cmd
    if [[ "$(uname)" == "Darwin" ]]; then
        stat_cmd="stat -f%z"
    else
        stat_cmd="stat -c%s"
    fi
    if [[ -f "$LOG_FILE" && $(${stat_cmd} "$LOG_FILE") -ge $max_size ]]; then
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
    
    # Color coding for console
    local color
    case "$level" in
        "DEBUG")    color="\033[0;36m" ;; # Cyan
        "INFO")     color="\033[0;32m" ;; # Green
        "WARNING")  color="\033[0;33m" ;; # Yellow
        "ERROR")    color="\033[0;31m" ;; # Red
        "CRITICAL") color="\033[1;31m" ;; # Bold Red
    esac
    # Output to console with color
    printf "${color}%s\033[0m\n" "$output"
    # Write to log file without console output
    printf "%s\n" "$output" >> "$LOG_FILE"

    [[ "$level" =~ ^(ERROR|CRITICAL)$ ]] && printf "%s\n" "$output" >> "$ERROR_LOG_FILE"
    log_json "$level" "$message"
}

log_debug() { log "DEBUG" "$*"; }
log_info() { log "INFO" "$*"; }
log_warning() { log "WARNING" "$*"; }
log_error() { log "ERROR" "$*"; exit 1; }

#############################################
# Utility Functions
#############################################

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
    log_info "  Health check endpoint: $HEALTH_CHECK_ENDPOINT"
    [[ "$ENABLE_TAIL" == true ]] && log_info "  Live logs: ENABLED (tail -f)"
    [[ "$USE_DOCKER" == true ]] && log_info "  Docker support: ENABLED"
}

validate_environment() {
    log_info "Validating environment variables..."
    
    if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [[ "$PORT" -lt 1 ]] || [[ "$PORT" -gt 65535 ]]; then
        log_error "Invalid PORT: $PORT (must be 1-65535)"
    fi
    
    if [[ ! "$HEALTH_CHECK_ENDPOINT" =~ ^/ ]]; then
        log_error "Invalid HEALTH_CHECK_ENDPOINT: must start with /"
    fi
    
    if [[ ! "$LOG_LEVEL" =~ ^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$ ]]; then
        log_error "Invalid LOG_LEVEL: $LOG_LEVEL"
    fi
}

detect_python() {
    local python_cmd
    python_cmd=$(command -v python3 || command -v python)
    if [[ -z "$python_cmd" ]]; then
        log_error "No Python interpreter found. Please install Python 3.10 or higher."
    fi
    local version
    version=$("$python_cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ "${version%%.*}" -lt 3 || "${version##*.}" -lt 10 ]]; then
        log_error "Python version $version is not supported. Please install Python 3.10 or higher."
    fi
    echo "$python_cmd:python-$version"
}

kill_port() {
    local port=$1
    local force=${2:-false}
    local pids
    
    if command -v lsof >/dev/null 2>&1; then
        pids=$(lsof -ti:"$port" 2>/dev/null)
    elif command -v ss >/dev/null 2>&1; then
        pids=$(ss -tuln | grep ":$port" | awk '{print $NF}' | cut -d'/' -f1 | sort -u)
    elif command -v netstat >/dev/null 2>&1; then
        pids=$(netstat -tuln | grep ":$port" | awk '{print $NF}' | cut -d'/' -f1 | sort -u)
    else
        log_warning "No lsof, ss, or netstat found. Cannot check for port conflicts."
        return
    fi
    
    if [[ -n "$pids" ]]; then
        log_warning "Port $port is in use by processes: $pids"
        
        # Check if interactive (tty available)
        if [[ "$force" == true ]] || [[ ! -t 0 ]]; then
            log_warning "Auto-terminating processes on port $port (non-interactive mode)..."
        else
            # Interactive mode - ask user
            read -p "Do you want to terminate these processes? [y/N] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_error "Port $port is in use. Exiting."
            fi
            log_warning "Terminating processes on port $port gracefully..."
        fi
        
        # Graceful termination
        echo "$pids" | xargs -r kill -TERM 2>/dev/null || true
        sleep 2
        
        # Check if still running
        pids=$(lsof -ti:"$port" 2>/dev/null || true)
        if [[ -n "$pids" ]]; then
            log_warning "Force killing remaining processes on port $port"
            echo "$pids" | xargs -r kill -9 2>/dev/null || true
        fi
        sleep 1
    fi
}

preflight_checks() {
    log_info "Running preflight checks..."
    
    # Check disk space (minimum 100MB)
    local available_space
    available_space=$(df "$PROJECT_DIR" 2>/dev/null | awk 'NR==2 {print $4}')
    if [[ -n "$available_space" && $available_space -lt 104857600 ]]; then
        log_warning "Less than 100MB disk space available"
    fi
    
    # Check Python modules availability
    if ! "$PYTHON_CMD" -c "import sys; print(f'Python {sys.version}')" >/dev/null 2>&1; then
        log_error "Python is not working correctly"
    fi
    
    # Check app.py syntax
    if [[ -f "$PROJECT_DIR/src/web/app.py" ]]; then
        if ! "$PYTHON_CMD" -m py_compile "$PROJECT_DIR/src/web/app.py" 2>/dev/null; then
            log_warning "Syntax errors detected in app.py. Server may fail to start."
        fi
    fi
}

check_dependencies() {
    local deps=("$PYTHON_CMD" "curl" "grep")
    local missing=()
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            missing+=("$dep")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${missing[*]}"
    fi
    
    if [[ "$USE_DOCKER" == true ]]; then
        if ! command -v docker >/dev/null 2>&1; then
            log_error "Docker is required but not installed."
        fi
        if ! docker info >/dev/null 2>&1; then
            log_error "Docker daemon is not running. Please start Docker."
        fi
    fi
}

compute_requirements_checksum() {
    if [[ -f "$REQ_FILE" ]]; then
        if command -v sha256sum >/dev/null 2>&1; then
            sha256sum "$REQ_FILE" | awk '{print $1}'
        elif command -v shasum >/dev/null 2>&1; then
            shasum -a 256 "$REQ_FILE" | awk '{print $1}'
        else
            # Fallback: use md5
            if command -v md5sum >/dev/null 2>&1; then
                md5sum "$REQ_FILE" | awk '{print $1}'
            elif command -v md5 >/dev/null 2>&1; then
                md5 -q "$REQ_FILE"
            else
                # Last resort: just use file modification time
                stat -c %Y "$REQ_FILE" 2>/dev/null || stat -f %m "$REQ_FILE" 2>/dev/null
            fi
        fi
    fi
}

check_venv_needs_recreation() {
    # Check if venv directory exists
    if [[ ! -d "$VENV_PATH" ]]; then
        log_info "Virtual environment not found - will create new one"
        return 0  # needs recreation
    fi

    # Check if activation script exists
    if [[ ! -f "$VENV_PATH/bin/activate" ]]; then
        log_warning "Virtual environment is incomplete - will recreate"
        return 0  # needs recreation
    fi

    # Check if requirements file exists
    if [[ ! -f "$REQ_FILE" ]]; then
        log_info "No requirements.txt found - will create with defaults"
        return 0  # needs recreation
    fi

    # Check if checksum file exists
    if [[ ! -f "$REQ_CHECKSUM_FILE" ]]; then
        log_info "No checksum file found - requirements may have changed"
        return 0  # needs recreation
    fi

    # Compare checksums
    local current_checksum
    local stored_checksum
    current_checksum=$(compute_requirements_checksum)
    stored_checksum=$(cat "$REQ_CHECKSUM_FILE" 2>/dev/null)

    if [[ "$current_checksum" != "$stored_checksum" ]]; then
        log_info "Requirements have changed - will recreate virtual environment"
        log_debug "  Old checksum: $stored_checksum"
        log_debug "  New checksum: $current_checksum"
        return 0  # needs recreation
    fi

    # All checks passed - venv is up to date
    log_info "Virtual environment is up to date - reusing existing installation"
    return 1  # does NOT need recreation
}

create_virtualenv() {
    log_info "Setting up Python virtual environment..."
    [[ -d "$VENV_BASE_DIR" ]] && rm -rf "$VENV_BASE_DIR"
    mkdir -p "$VENV_BASE_DIR" "$(dirname "$LOG_FILE")"

    if ! "$PYTHON_CMD" -m venv "$VENV_PATH"; then
        log_error "Failed to create virtual environment"
    fi

    source "$VENV_PATH/bin/activate"

    if [[ -z "$VIRTUAL_ENV" ]]; then
        log_error "Failed to activate virtual environment"
    fi

    if ! pip install --upgrade pip --quiet; then
        log_error "Failed to upgrade pip"
    fi
}

install_dependencies() {
    log_info "Checking for requirements file at $REQ_FILE..."
    
    if [[ ! -f "$REQ_FILE" ]]; then
        log_info "Creating default requirements.txt..."
        cat > "$REQ_FILE" << 'EOF'
typer>=0.12.5
docker>=7.1.0
pyyaml>=6.0.2
fastapi>=0.115.0
uvicorn[standard]>=0.30.6
jinja2>=3.1.4
slowapi>=0.1.9
psutil>=5.9.0
watchdog>=3.0.0
EOF
    fi
    
    log_info "Installing dependencies from $REQ_FILE..."
    
    local retry_count=0
    local success=false
    
    while [[ $retry_count -lt $INSTALL_RETRIES ]] && [[ "$success" == false ]]; do
        log_info "Installation attempt $((retry_count + 1))/$INSTALL_RETRIES..."
        
        if pip install -r "$REQ_FILE" --quiet --retries 5; then
            success=true
            log_info "Dependencies installed successfully"
        else
            ((retry_count++))
            if [[ $retry_count -lt $INSTALL_RETRIES ]]; then
                log_warning "Installation failed. Retrying in ${INSTALL_RETRY_WAIT}s..."
                sleep "$INSTALL_RETRY_WAIT"
            fi
        fi
    done
    
    if [[ "$success" == false ]]; then
        log_error "Failed to install dependencies after $INSTALL_RETRIES attempts"
    fi

    # Save checksum for future comparisons
    local checksum
    checksum=$(compute_requirements_checksum)
    echo "$checksum" > "$REQ_CHECKSUM_FILE"
    log_debug "Saved requirements checksum: $checksum"
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
    log_info "Waiting for server to be ready at $HEALTH_CHECK_URL (timeout: ${HEALTH_CHECK_TIMEOUT}s)..."
    
    while [[ $elapsed -lt $HEALTH_CHECK_TIMEOUT ]]; do
        # Try curl first
        if command -v curl >/dev/null 2>&1; then
            if curl -sf --connect-timeout 2 --max-time 5 "$HEALTH_CHECK_URL" >/dev/null 2>&1; then
                log_info "Server is healthy and ready at $HEALTH_CHECK_URL"
                return 0
            fi
        # Fallback: netcat
        elif command -v nc >/dev/null 2>&1; then
            if nc -z -w 1 localhost "$PORT" >/dev/null 2>&1; then
                log_info "Server is responding on port $PORT"
                return 0
            fi
        # Last resort: bash TCP socket
        else
            if (echo > /dev/tcp/localhost/"$PORT") 2>/dev/null; then
                log_info "Server is responding on port $PORT"
                return 0
            fi
        fi
        
        # Check if process is still alive
        if ! ps -p "$WEB_PID" >/dev/null 2>&1; then
            log_error "Server process died before becoming healthy. Check $LOG_FILE for details."
        fi
        
        sleep 1
        ((elapsed++))
    done
    
    log_error "Server health check timed out after ${HEALTH_CHECK_TIMEOUT}s"
}

monitor_resources() {
    local last_check=0
    local check_interval=60
    
    log_debug "Resource monitor started for PID $WEB_PID"
    
    while ps -p "$WEB_PID" >/dev/null 2>&1; do
        # Check every 10 seconds if process is alive, log every 60
        if ! sleep 1; then
            break
        fi
        
        ((last_check++))
        
        # Only log metrics every 60 seconds
        if [[ $((last_check % 60)) -eq 0 ]]; then
            if ps -p "$WEB_PID" >/dev/null 2>&1; then
                local cpu mem
                cpu=$(ps -p "$WEB_PID" -o %cpu 2>/dev/null | tail -n1)
                mem=$(ps -p "$WEB_PID" -o %mem 2>/dev/null | tail -n1)
                log_debug "Resource usage - CPU: ${cpu}%, Memory: ${mem}%"
            fi
        fi
    done
    
    # Process died - this will be caught by the main wait
    log_debug "Resource monitor: Process $WEB_PID is no longer running"
}

#############################################
# Tail Logs Management
#############################################

start_tail_logs() {
    if [[ "$ENABLE_TAIL" == true ]]; then
        log_info "Starting live log viewer (tail -f)..."
        sleep 1
        tail -f "$LOG_FILE" 2>/dev/null &
        TAIL_PROCESS_PID=$!
        log_info "Live log viewer started (PID: $TAIL_PROCESS_PID)"
    fi
}

stop_tail_logs() {
    if [[ -n "$TAIL_PROCESS_PID" ]] && ps -p "$TAIL_PROCESS_PID" >/dev/null 2>&1; then
        log_debug "Stopping tail process..."
        kill "$TAIL_PROCESS_PID" 2>/dev/null || true
        wait "$TAIL_PROCESS_PID" 2>/dev/null || true
    fi
}

#############################################
# Web Server Management
#############################################

start_server() {
    local start_time
    start_time=$(date +%s)
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
    
    # Handle access log flag compatibility
    if [[ "$LOG_LEVEL" != "DEBUG" ]]; then
        # Try the newer flag format first
        if uvicorn --help 2>/dev/null | grep -q "\-\-access-log"; then
            uvicorn_args+=("--access-log")
        fi
    fi

    export DOCKER_LOG_LEVEL="error"
    export PYTHONWARNINGS="ignore"
    export PYTHONUNBUFFERED=1

    log_info "Press Ctrl+C to stop"

    (
        source "$VENV_PATH/bin/activate"
        if [[ "$ENABLE_TAIL" == true ]]; then
            # If tail is enabled, only write to log file (tail will display it)
            uvicorn "${uvicorn_args[@]}" >> "$LOG_FILE" 2>&1
        else
            # If tail is disabled, show logs in console and write to file
            uvicorn "${uvicorn_args[@]}" 2>&1 | tee -a "$LOG_FILE"
        fi
    ) &
    
    WEB_PID=$!
    echo "$WEB_PID" > "$PID_FILE"
    log_info "Server process started with PID: $WEB_PID"
    
    start_tail_logs
    
    # Start resource monitor in background
    monitor_resources &
    MONITOR_PID=$!
    
    if health_check; then
        local end_time
        end_time=$(date +%s)
        log_info "Server startup completed in $((end_time - start_time)) seconds"
    else
        kill "$WEB_PID" 2>/dev/null || true
        kill "$MONITOR_PID" 2>/dev/null || true
        exit 1
    fi
    
    # Wait for server process
    wait "$WEB_PID"
    EXIT_CODE=$?
    
    # Cleanup monitor
    kill "$MONITOR_PID" 2>/dev/null || true
    
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
    
    stop_tail_logs
    
    # Use PID from memory, not file (avoid stale PID issues)
    if [[ -n "$WEB_PID" ]] && ps -p "$WEB_PID" >/dev/null 2>&1; then
        log_info "Sending SIGTERM to process $WEB_PID for graceful shutdown..."
        kill -TERM "$WEB_PID" 2>/dev/null
        
        local wait_count=0
        local max_wait=15
        while ps -p "$WEB_PID" >/dev/null 2>&1 && [[ $wait_count -lt $max_wait ]]; do
            sleep 1
            ((wait_count++))
        done
        
        if ps -p "$WEB_PID" >/dev/null 2>&1; then
            log_warning "Process did not exit gracefully. Force killing..."
            kill -9 "$WEB_PID" 2>/dev/null || true
        fi
    fi
    
    # Cleanup monitor process
    if [[ -n "$MONITOR_PID" ]] && ps -p "$MONITOR_PID" >/dev/null 2>&1; then
        kill "$MONITOR_PID" 2>/dev/null || true
    fi
    
    # Cleanup PID file
    rm -f "$PID_FILE"
    
    # Cleanup port
    kill_port "$PORT" true
    
    log_info "Shutdown completed. Bye!"
    exit 0
}

show_status() {
    if [[ -n "$WEB_PID" ]] && ps -p "$WEB_PID" >/dev/null 2>&1; then
        local uptime cpu mem
        uptime=$(ps -p "$WEB_PID" -o etime 2>/dev/null | tail -n1)
        cpu=$(ps -p "$WEB_PID" -o %cpu 2>/dev/null | tail -n1)
        mem=$(ps -p "$WEB_PID" -o %mem 2>/dev/null | tail -n1)
        
        log_info "Web server status:"
        log_info "  PID: $WEB_PID"
        log_info "  Uptime: $uptime"
        log_info "  CPU: ${cpu}%"
        log_info "  Memory: ${mem}%"
        log_info "  URL: http://localhost:$PORT"
    else
        log_info "Web server is not running"
    fi
}

show_help() {
    cat << EOF
Improved Web Panel Starter (v2.0.0)

A Bash script to start a Python-based web server with robust process management,
logging, and health checks.

Usage: $0 [OPTIONS]

Options:
  --debug              Enable debug logging (sets log level to DEBUG)
  --log-level LEVEL    Set log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
                       (default: INFO)
  --tail               Enable live log viewing (tail -f $LOG_FILE)
  --use-docker         Enable Docker dependency checks
  --force-reinstall    Force recreation of virtual environment (ignores cache)
  --health-check-endpoint ENDPOINT
                       Set custom health check endpoint (default: /)
  --status             Show server status and exit
  --help               Display this help message and exit

Environment Variables:
  LOG_LEVEL            Set default log level (default: INFO)
  USE_DOCKER          Enable Docker support (default: false)
  PORT                Set server port (default: 8000)
  HEALTH_CHECK_ENDPOINT
                      Set health check endpoint (default: /)

Examples:
  $0                        # Start server with default settings (fast if venv exists)
  $0 --debug --tail         # Start with debug logging and live logs
  $0 --log-level WARNING    # Start with WARNING log level
  $0 --use-docker           # Start with Docker support enabled
  $0 --force-reinstall      # Force recreate virtual environment
  $0 --health-check-endpoint /health  # Use custom health check endpoint
  $0 --status               # Show server status

Logs are written to:
  - $LOG_FILE
  - $ERROR_LOG_FILE (errors only)
  - $JSON_LOG_FILE (JSON format)

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
            --tail)
                ENABLE_TAIL=true
                shift
                ;;
            --use-docker)
                USE_DOCKER=true
                shift
                ;;
            --force-reinstall)
                FORCE_REINSTALL=true
                shift
                ;;
            --health-check-endpoint)
                HEALTH_CHECK_ENDPOINT="$2"
                shift 2
                ;;
            --status)
                # Show status and exit
                mkdir -p "$PROJECT_DIR/venv" 2>/dev/null
                show_status
                exit 0
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

#############################################
# Main
#############################################

main() {
    parse_arguments "$@"

    # Detect Python version first (needed for venv path)
    python_info=$(detect_python)
    readonly PYTHON_CMD="${python_info%:*}"
    readonly VENV_NAME="${python_info#*:}"
    readonly VENV_PATH="${VENV_BASE_DIR}/${VENV_NAME}"

    # Clean old logs but keep venv directory structure
    mkdir -p "$PROJECT_DIR/venv"
    rm -f "$LOG_FILE" "$ERROR_LOG_FILE" "$JSON_LOG_FILE"

    trap graceful_shutdown SIGINT SIGTERM EXIT

    setup_logging
    validate_environment
    show_environment

    # Smart venv management
    local needs_venv_setup=true

    if [[ "$FORCE_REINSTALL" == true ]]; then
        log_warning "Force reinstall requested - will recreate virtual environment"
        rm -rf "$VENV_BASE_DIR"
        rm -f "$REQ_CHECKSUM_FILE"
    else
        # Check if we can reuse existing venv
        if check_venv_needs_recreation; then
            needs_venv_setup=true
        else
            needs_venv_setup=false
        fi
    fi

    preflight_checks
    check_dependencies
    kill_port "$PORT" true

    # Only recreate venv if needed
    if [[ "$needs_venv_setup" == true ]]; then
        create_virtualenv
        install_dependencies
    else
        # Just activate existing venv
        log_info "Activating existing virtual environment..."
        source "$VENV_PATH/bin/activate"
        if [[ -z "$VIRTUAL_ENV" ]]; then
            log_error "Failed to activate virtual environment"
        fi
        log_info "✓ Virtual environment activated (fast startup)"
    fi

    if [[ ! -f "$PROJECT_DIR/src/web/app.py" ]]; then
        log_error "Missing application file: $PROJECT_DIR/src/web/app.py"
    fi

    start_server
}

main "$@"