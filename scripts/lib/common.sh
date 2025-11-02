#!/bin/bash
# Common utilities library for Docker Compose Playground scripts
# Source this file in your scripts: source "$(dirname "$0")/../lib/common.sh" || source "$(dirname "$0")/../../lib/common.sh"

# --- Logging Functions ---

log_info() {
    echo "ℹ️  $1"
}

log_success() {
    echo "✅ $1"
}

log_error() {
    echo "❌ $1" >&2
}

log_warning() {
    echo "⚠️  $1"
}

# --- Docker Helper Functions ---

docker_exec() {
    local container=$1
    shift
    docker exec "$container" "$@"
}

docker_exec_quiet() {
    local container=$1
    shift
    docker exec "$container" "$@" 2>/dev/null
}

# --- Service Waiting Functions ---

wait_for_service() {
    local container=$1
    local check_cmd=$2
    local max_wait=${3:-60}
    local count=0

    log_info "Waiting for service in ${container}..."

    while [ $count -lt $max_wait ]; do
        if eval "$check_cmd" 2>/dev/null; then
            log_success "Service is ready!"
            return 0
        fi
        sleep 2
        count=$((count + 2))
    done

    log_error "Service not available after ${max_wait} seconds"
    return 1
}

wait_for_mysql() {
    local container=$1
    local user=${2:-root}
    local password=${3:-playground}
    local max_wait=${4:-60}

    wait_for_service "$container" \
        "docker exec '$container' mysqladmin ping -u '$user' -p'$password' --silent" \
        "$max_wait"
}

wait_for_postgres() {
    local container=$1
    local user=${2:-postgres}
    local max_wait=${3:-60}

    wait_for_service "$container" \
        "docker exec '$container' pg_isready -U '$user'" \
        "$max_wait"
}

# --- Backup Functions ---

create_backup_dir() {
    local backup_dir="${SHARED_DIR:-./shared-volumes}/data/backups/$1"
    mkdir -p "$backup_dir"
    echo "$backup_dir"
}

get_timestamp() {
    date +%Y%m%d_%H%M%S
}

# --- Validation Functions ---

validate_container_name() {
    if [ -z "${1:-}" ]; then
        log_error "Usage: $0 <container-name>"
        exit 1
    fi
}

container_exists() {
    docker ps -a --format '{{.Names}}' | grep -q "^$1$"
}

container_is_running() {
    docker ps --format '{{.Names}}' | grep -q "^$1$"
}

# --- Package Installation Functions ---

install_if_missing() {
    local container=$1
    local check_cmd=$2
    local install_cmd=$3
    local package_name=$4

    if docker_exec_quiet "$container" bash -c "$check_cmd"; then
        log_info "${package_name} already installed, skipping"
        return 0
    else
        log_info "Installing ${package_name}..."
        docker_exec "$container" bash -c "$install_cmd"
        log_success "${package_name} installed"
    fi
}
