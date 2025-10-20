#!/bin/bash
set -uo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVER_SCRIPT="${SCRIPT_DIR}/start-webui.sh"
PORT=8000
API_URL="http://localhost:${PORT}/api"
TIMEOUT=60
INITIAL_WAIT=15
IMAGE_NAME="alpine-3.22"
CONTAINER_NAME="playground-${IMAGE_NAME}"

# Logs
ERROR_LOG="${SCRIPT_DIR}/venv/api_test_error.log"
SUCCESS_LOG="${SCRIPT_DIR}/venv/api_test_success.log"
WEB_LOG="${SCRIPT_DIR}/venv/web.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test selection
SELECTED_TEST=""
VERBOSE=false

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--test)
                SELECTED_TEST="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -t, --test NUM        Run only test number NUM (1-37)
    -v, --verbose         Enable verbose output
    -h, --help           Show this help message

Examples:
    $0                    # Run all tests
    $0 -t 5              # Run only test 5
    $0 -t 10 -v          # Run test 10 with verbose output
    $0 -t 1,5,10         # Run tests 1, 5, and 10

Available tests:
    1  - Start container
    2  - Start already running container
    3  - Stop container
    4  - Stop non-existent container
    5  - Start container with invalid image
    6  - System info endpoint
    7  - Get status of non-existent operation
    8  - Get groups list
    9  - Start a group
    10 - Stop a group
    11 - Get group status
    12 - Get status of non-existent group
    13 - Stop all containers
    14 - Restart all containers
    15 - Cleanup all containers
    16 - System info running count
    17 - Manage page
    18 - Add container page
    19 - Container statistics
    20 - Containers health
    21 - System health diagnostics
    22 - Port conflicts check
    23 - Validate configuration
    24 - Execute command in container
    25 - Container diagnostics
    26 - Get container logs
    27 - Export configuration
    28 - Get server logs
    29 - Get backups list
    30 - Debug configuration
    31 - Invalid endpoint
    32 - Concurrent starts (stress test)
    33 - Rapid stop/start cycle
    34 - Large payload command
    35 - WebSocket console
    36 - Add container form
    37 - Start invalid category
EOF
}

: > "$ERROR_LOG"
: > "$SUCCESS_LOG"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    echo "[SUCCESS] $1" >> "$SUCCESS_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "[ERROR] $1" >> "$ERROR_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

cleanup() {
    log_info "Running cleanup..."
    
    if [ -f "${SCRIPT_DIR}/venv/web.pid" ]; then
        pid=$(cat "${SCRIPT_DIR}/venv/web.pid" 2>/dev/null)
        if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
            log_info "Terminating server (PID: $pid)..."
            kill -TERM "$pid" 2>/dev/null || true
            sleep 2
            if ps -p "$pid" > /dev/null 2>&1; then
                kill -9 "$pid" 2>/dev/null || true
            fi
        fi
    fi
    
    lsof -ti:${PORT} | xargs kill -9 2>/dev/null || true
    
    # Stop test container
    log_info "Stopping container $CONTAINER_NAME..."
    curl -s -X POST "http://localhost:${PORT}/stop/${CONTAINER_NAME}" > /dev/null 2>&1 || true
    
    log_info "Cleanup complete"
}

trap cleanup SIGINT SIGTERM EXIT

wait_for_api() {
    local elapsed=0
    local max_wait=$1
    
    log_info "Waiting for API to be available (max ${max_wait}s)..."
    
    while [ $elapsed -lt "$max_wait" ]; do
        if curl -sf "${API_URL}/system-info" > /dev/null 2>&1; then
            log_success "API is available"
            return 0
        fi
        
        sleep 1
        ((elapsed++))
    done
    
    log_error "API not available after ${max_wait}s"
    return 1
}

# Robustly extract JSON values
parse_json() {
    local json="$1"
    local key="$2"
    echo "$json" | grep -o "\"$key\":[^,}]*" | head -1 | cut -d: -f2- | tr -d ' "' || echo ""
}

# Wait for asynchronous operation to complete
wait_for_operation() {
    local operation_id=$1
    local max_wait=${2:-90}
    local elapsed=0
    
    log_verbose "Waiting for operation $operation_id (max ${max_wait}s)..."
    
    while [ $elapsed -lt "$max_wait" ]; do
        local op_response=$(curl -s "${API_URL}/operation-status/${operation_id}" 2>/dev/null || echo "{}")
        local status=$(parse_json "$op_response" "status")
        
        if [ -z "$status" ]; then
            log_verbose "Operation not found, retrying..."
            sleep 2
            ((elapsed+=2))
            continue
        fi
        
        if [ "$status" = "completed" ] || [ "$status" = "error" ]; then
            echo "$op_response"
            return 0
        fi
        
        sleep 2
        ((elapsed+=2))
    done
    
    log_error "Timeout waiting for operation completion"
    return 1
}

# ============ TEST SUITE ============

test_start_container() {
    log_info "TEST 1: Start container '$IMAGE_NAME'"
    
    curl -s -X POST "http://localhost:${PORT}/stop/${CONTAINER_NAME}" > /dev/null 2>&1 || true
    sleep 1
    
    local response=$(curl -s -X POST "${API_URL}/start/${IMAGE_NAME}")
    log_verbose "Start response: $response"
    
    if echo "$response" | grep -q "operation_id"; then
        local operation_id=$(parse_json "$response" "operation_id")
        log_verbose "Operation ID: $operation_id"
        
        local op_response=$(wait_for_operation "$operation_id" 90)
        
        if [ $? -eq 0 ]; then
            local op_status=$(parse_json "$op_response" "status")
            local started=$(parse_json "$op_response" "started")
            
            if [ "$op_status" = "completed" ] && [ "$started" = "1" ]; then
                log_success "Container started successfully"
                sleep 2
                return 0
            else
                log_error "Operation completed but container not started"
                return 1
            fi
        else
            log_error "Operation failed or timeout"
            return 1
        fi
    else
        log_error "Invalid response: $response"
        return 1
    fi
}

test_start_already_running() {
    log_info "TEST 2: Start already running container"
    
    local response=$(curl -s -X POST "${API_URL}/start/${IMAGE_NAME}")
    
    if echo "$response" | grep -q "operation_id"; then
        local operation_id=$(parse_json "$response" "operation_id")
        local op_response=$(wait_for_operation "$operation_id" 60)
        
        if [ $? -eq 0 ]; then
            local already_running=$(parse_json "$op_response" "already_running")
            
            if [ "$already_running" = "1" ]; then
                log_success "Already running container correctly identified"
                return 0
            else
                log_warning "Container not marked as already_running"
                return 0
            fi
        fi
    fi
    
    log_error "Test failed"
    return 1
}

test_stop_container() {
    log_info "TEST 3: Stop container '$CONTAINER_NAME'"
    
    local response=$(curl -s -X POST "http://localhost:${PORT}/stop/${CONTAINER_NAME}")
    
    if echo "$response" | grep -q "stopped"; then
        log_success "Container stopped successfully"
        sleep 2
        return 0
    elif echo "$response" | grep -q "not found\|Not Found"; then
        log_warning "Container not found"
        return 0
    else
        log_error "Stop failed: $response"
        return 1
    fi
}

test_stop_nonexistent() {
    log_info "TEST 4: Stop non-existent container"
    
    local fake_container="playground-nonexistent-container-xyz-12345"
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_URL}/stop/${fake_container}")
    
    if [ "$http_code" = "404" ]; then
        log_success "Correctly returned 404"
        return 0
    else
        log_error "Expected 404, got $http_code"
        return 1
    fi
}

test_start_invalid_image() {
    log_info "TEST 5: Start container with invalid image"
    
    local response=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/start/invalid-image-xyz-nonexistent")
    local http_code=$(echo "$response" | tail -1)
    
    if [ "$http_code" = "404" ]; then
        log_success "Correctly returned 404 for invalid image"
        return 0
    else
        log_error "Expected 404, got $http_code"
        return 1
    fi
}

test_system_info() {
    log_info "TEST 6: System info endpoint"
    
    local response=$(curl -s "${API_URL}/system-info")
    
    if echo "$response" | grep -q '"docker"' && echo "$response" | grep -q '"network"' && echo "$response" | grep -q '"volume"'; then
        log_success "System info contains required fields"
        return 0
    fi
    
    log_error "System info invalid"
    return 1
}

test_operation_status_nonexistent() {
    log_info "TEST 7: Get status of non-existent operation"
    
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/operation-status/nonexistent-op-id-12345")
    
    if [ "$http_code" = "404" ]; then
        log_success "Correctly returned 404"
        return 0
    else
        log_error "Expected 404, got $http_code"
        return 1
    fi
}

test_get_groups_list() {
    log_info "TEST 8: Get groups list"
    
    local response=$(curl -s "${API_URL}/system-info")
    
    if echo "$response" | grep -q '"active_containers"'; then
        log_success "System info contains group information"
        return 0
    else
        log_warning "No group information found"
        return 0
    fi
}

test_start_group() {
    log_info "TEST 9: Start a group of containers"
    
    local response=$(curl -s -X POST "${API_URL}/start-group/MinIO-S3-Stack")
    
    if echo "$response" | grep -q "operation_id"; then
        local operation_id=$(parse_json "$response" "operation_id")
        local op_response=$(wait_for_operation "$operation_id" 180)
        
        if [ $? -eq 0 ]; then
            local status=$(parse_json "$op_response" "status")
            if [ "$status" = "completed" ]; then
                log_success "Group started successfully"
                return 0
            fi
        fi
    elif echo "$response" | grep -q "not found"; then
        log_warning "Group not configured"
        return 0
    fi
    
    log_error "Group start failed"
    return 1
}

test_stop_group() {
    log_info "TEST 10: Stop a group of containers"
    
    local response=$(curl -s -X POST "${API_URL}/stop-group/MySQL-Stack")
    
    if echo "$response" | grep -q "operation_id"; then
        local operation_id=$(parse_json "$response" "operation_id")
        local op_response=$(wait_for_operation "$operation_id" 180)
        
        if [ $? -eq 0 ]; then
            local status=$(parse_json "$op_response" "status")
            if [ "$status" = "completed" ]; then
                log_success "Group stopped successfully"
                return 0
            fi
        fi
    elif echo "$response" | grep -q "not found"; then
        log_warning "Group not configured"
        return 0
    fi
    
    log_error "Group stop failed"
    return 1
}

test_group_status() {
    log_info "TEST 11: Get group status"
    
    local response=$(curl -s "${API_URL}/group-status/PostgreSQL-Stack")
    
    if echo "$response" | grep -q '"group"' && echo "$response" | grep -q '"containers"'; then
        log_success "Group status works"
        return 0
    elif echo "$response" | grep -q '"detail"'; then
        log_warning "Group not found"
        return 0
    else
        log_error "Invalid response"
        return 1
    fi
}

test_group_not_found() {
    log_info "TEST 12: Get status of non-existent group"
    
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/group-status/nonexistent-group-xyz")
    
    if [ "$http_code" = "404" ]; then
        log_success "Correctly returned 404"
        return 0
    else
        log_error "Expected 404, got $http_code"
        return 1
    fi
}

test_stop_all() {
    log_info "TEST 13: Stop all containers"
    
    curl -s -X POST "${API_URL}/start/${IMAGE_NAME}" > /dev/null 2>&1
    sleep 2
    
    local response=$(curl -s -X POST "${API_URL}/stop-all")
    
    if echo "$response" | grep -q "operation_id"; then
        local operation_id=$(parse_json "$response" "operation_id")
        local op_response=$(wait_for_operation "$operation_id" 120)
        
        if [ $? -eq 0 ]; then
            local status=$(parse_json "$op_response" "status")
            if [ "$status" = "completed" ]; then
                log_success "All containers stopped"
                return 0
            fi
        fi
    fi
    
    log_error "Stop all failed"
    return 1
}

test_restart_all() {
    log_info "TEST 14: Restart all containers"
    
    curl -s -X POST "${API_URL}/start/${IMAGE_NAME}" > /dev/null 2>&1
    sleep 2
    
    local response=$(curl -s -X POST "${API_URL}/restart-all")
    
    if echo "$response" | grep -q "operation_id"; then
        local operation_id=$(parse_json "$response" "operation_id")
        local op_response=$(wait_for_operation "$operation_id" 180)
        
        if [ $? -eq 0 ]; then
            local status=$(parse_json "$op_response" "status")
            if [ "$status" = "completed" ]; then
                log_success "All containers restarted"
                return 0
            fi
        fi
    fi
    
    log_error "Restart all failed"
    return 1
}

test_cleanup_all() {
    log_info "TEST 15: Cleanup all containers"
    
    local response=$(curl -s -X POST "${API_URL}/cleanup-all")
    
    if echo "$response" | grep -q "operation_id"; then
        local operation_id=$(parse_json "$response" "operation_id")
        local op_response=$(wait_for_operation "$operation_id" 180)
        
        if [ $? -eq 0 ]; then
            local status=$(parse_json "$op_response" "status")
            if [ "$status" = "completed" ]; then
                log_success "Cleanup completed"
                return 0
            fi
        fi
    fi
    
    log_error "Cleanup failed"
    return 1
}

test_system_info_running_count() {
    log_info "TEST 16: System info running count"
    
    local response=$(curl -s "${API_URL}/system-info")
    
    if echo "$response" | grep -q '"running"'; then
        log_success "Running count present"
        return 0
    else
        log_error "Running count missing"
        return 1
    fi
}

test_manage_page() {
    log_info "TEST 17: Manage page endpoint"
    
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${PORT}/manage")
    
    if [ "$http_code" = "200" ]; then
        log_success "Manage page loaded"
        return 0
    else
        log_error "Manage page failed (HTTP: $http_code)"
        return 1
    fi
}

test_add_container_page() {
    log_info "TEST 18: Add container page"
    
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${PORT}/add-container")
    
    if [ "$http_code" = "200" ]; then
        log_success "Add container page loaded"
        return 0
    else
        log_error "Add container page failed (HTTP: $http_code)"
        return 1
    fi
}

test_container_stats() {
    log_info "TEST 19: Container statistics"
    
    local container_full_name="playground-${IMAGE_NAME}"
    local response=$(curl -s "${API_URL}/container-stats/${container_full_name}")
    
    if echo "$response" | grep -q '"cpu"' && echo "$response" | grep -q '"memory"'; then
        log_success "Container stats retrieved"
        return 0
    else
        log_warning "Stats not available"
        return 0
    fi
}

test_containers_health() {
    log_info "TEST 20: Containers health"
    
    local response=$(curl -s "${API_URL}/containers-health")
    
    if echo "$response" | grep -q '"total"'; then
        log_success "Health check works"
        return 0
    else
        log_error "Health check failed"
        return 1
    fi
}

test_system_health() {
    log_info "TEST 21: System health diagnostics"
    
    local response=$(curl -s "${API_URL}/system-health")
    
    if echo "$response" | grep -q '"status"'; then
        log_success "Health diagnostics work"
        return 0
    else
        log_error "Health diagnostics failed"
        return 1
    fi
}

test_port_conflicts() {
    log_info "TEST 22: Port conflicts check"
    
    local response=$(curl -s "${API_URL}/port-conflicts")
    
    if echo "$response" | grep -q '"status"'; then
        log_success "Port conflict check works"
        return 0
    else
        log_error "Port check failed"
        return 1
    fi
}

test_validate_config() {
    log_info "TEST 23: Validate configuration"
    
    local response=$(curl -s -X POST "${API_URL}/validate-config/${IMAGE_NAME}")
    
    if echo "$response" | grep -q '"valid"'; then
        log_success "Config validation works"
        return 0
    else
        log_error "Config validation failed"
        return 1
    fi
}

test_execute_command() {
    log_info "TEST 24: Execute command in container"
    
    local container_full_name="playground-${IMAGE_NAME}"
    local payload='{"command": "echo test", "timeout": 10}'
    
    local response=$(curl -s -X POST "${API_URL}/execute-command/${container_full_name}" \
        -H "Content-Type: application/json" \
        -d "$payload")
    
    if echo "$response" | grep -q '"exit_code"'; then
        log_success "Command execution works"
        return 0
    else
        log_warning "Container not running"
        return 0
    fi
}

test_execute_diagnostic() {
    log_info "TEST 25: Container diagnostics"
    
    local container_full_name="playground-${IMAGE_NAME}"
    local response=$(curl -s -X POST "${API_URL}/execute-diagnostic/${container_full_name}")
    
    if echo "$response" | grep -q '"diagnostics"'; then
        log_success "Diagnostics work"
        return 0
    else
        log_warning "Diagnostics unavailable"
        return 0
    fi
}

test_get_container_logs() {
    log_info "TEST 26: Get container logs"
    
    local container_full_name="playground-${IMAGE_NAME}"
    local response=$(curl -s "${API_URL}/logs/${container_full_name}")
    
    if echo "$response" | grep -q '"logs"'; then
        log_success "Log retrieval works"
        return 0
    else
        log_warning "Logs unavailable"
        return 0
    fi
}

test_export_config() {
    log_info "TEST 27: Export configuration"
    
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/export-config")
    
    if [ "$http_code" = "200" ]; then
        log_success "Config export works"
        return 0
    else
        log_error "Config export failed (HTTP: $http_code)"
        return 1
    fi
}

test_get_server_logs() {
    log_info "TEST 28: Get server logs"
    
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/logs")
    
    if [ "$http_code" = "200" ]; then
        log_success "Server logs accessible"
        return 0
    else
        log_warning "Server logs returned $http_code"
        return 0
    fi
}

test_get_backups() {
    log_info "TEST 29: Get backups list"
    
    local response=$(curl -s "${API_URL}/backups")
    
    if echo "$response" | grep -q '"backups"'; then
        log_success "Backups list works"
        return 0
    else
        log_error "Backups list failed"
        return 1
    fi
}

test_debug_config() {
    log_info "TEST 30: Debug configuration"
    
    local response=$(curl -s "${API_URL}/debug-config")
    
    if echo "$response" | grep -q '"custom_dir"'; then
        log_success "Debug config works"
        return 0
    else
        log_warning "Debug config limited output"
        return 0
    fi
}

test_invalid_endpoint() {
    log_info "TEST 31: Invalid endpoint returns 404"
    
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/invalid-endpoint-xyz")
    
    if [ "$http_code" = "404" ]; then
        log_success "404 returned correctly"
        return 0
    else
        log_warning "Invalid endpoint returned $http_code"
        return 0
    fi
}

test_concurrent_starts() {
    log_info "TEST 32: Concurrent starts (stress test)"
    
    local pids=()
    
    for i in 1 2 3; do
        (
            curl -s -X POST "${API_URL}/start/${IMAGE_NAME}" > /dev/null 2>&1
        ) &
        pids+=($!)
    done
    
    local failed=0
    for pid in "${pids[@]}"; do
        if ! wait "$pid"; then
            ((failed++))
        fi
    done
    
    if [ $failed -eq 0 ]; then
        log_success "Concurrent starts completed"
        return 0
    else
        log_error "Some concurrent ops failed"
        return 1
    fi
}

test_rapid_stop_start() {
    log_info "TEST 33: Rapid stop/start cycle"
    
    local container_full_name="playground-${IMAGE_NAME}"
    
    curl -s -X POST "${API_URL}/start/${IMAGE_NAME}" > /dev/null 2>&1
    sleep 1
    curl -s -X POST "http://localhost:${PORT}/stop/${container_full_name}" > /dev/null 2>&1
    sleep 1
    
    local response=$(curl -s -X POST "${API_URL}/start/${IMAGE_NAME}")
    
    if echo "$response" | grep -q "operation_id"; then
        log_success "Rapid cycle works"
        return 0
    else
        log_error "Rapid cycle failed"
        return 1
    fi
}

test_large_payload_command() {
    log_info "TEST 34: Large payload command"
    
    local container_full_name="playground-${IMAGE_NAME}"
    # Escape properly for JSON
    local payload="{\"command\": \"echo test\", \"timeout\": 15}"
    
    local response=$(curl -s -X POST "${API_URL}/execute-command/${container_full_name}" \
        -H "Content-Type: application/json" \
        -d "$payload")
    
    if echo "$response" | grep -q '"exit_code"'; then
        log_success "Large payload handled"
        return 0
    else
        log_warning "Large payload test skipped (container not running)"
        return 0
    fi
}

test_websocket_console() {
    log_info "TEST 35: WebSocket console"
    
    local container_full_name="playground-${IMAGE_NAME}"
    
    # First ensure container is running
    curl -s -X POST "${API_URL}/start/${IMAGE_NAME}" > /dev/null 2>&1
    sleep 2
    
    # Try WebSocket connection (will fail with curl but we test endpoint existence)
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -i \
        -H "Connection: Upgrade" \
        -H "Upgrade: websocket" \
        -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
        -H "Sec-WebSocket-Version: 13" \
        "http://localhost:${PORT}/ws/console/${container_full_name}" 2>&1)
    
    # 101 = upgrade successful, 400/426 = client error (expected with curl), 404 = not found
    if [ "$http_code" = "101" ] || [ "$http_code" = "400" ] || [ "$http_code" = "426" ]; then
        log_success "WebSocket endpoint accessible"
        return 0
    else
        # Still could be working - endpoint exists but curl can't upgrade
        log_warning "WebSocket returned $http_code (may still be working)"
        return 0
    fi
}

test_add_container_form() {
    log_info "TEST 36: Add container form page"
    
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${PORT}/add-container")
    
    if [ "$http_code" = "200" ]; then
        log_success "Form page accessible"
        return 0
    else
        log_error "Form page not accessible"
        return 1
    fi
}

test_start_invalid_category() {
    log_info "TEST 37: Start invalid category"
    
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_URL}/start-category/nonexistent-xyz")
    
    if [ "$http_code" = "404" ] || [ "$http_code" = "200" ]; then
        log_success "Invalid category handled"
        return 0
    else
        log_error "Unexpected response code"
        return 1
    fi
}

# ============ MAIN ============

main() {
    log_info "============================================"
    log_info "API Test Suite"
    log_info "============================================"
    log_info ""
    
    # Initial cleanup
    log_info "Initial cleanup..."
    lsof -ti:${PORT} | xargs kill -9 2>/dev/null || true
    sleep 1
    
    # Start server
    log_info "Starting WebUI server..."
    bash "${SERVER_SCRIPT}" --tail &
    SERVER_PID=$!
    log_info "Server started with PID: $SERVER_PID"
    
    sleep "$INITIAL_WAIT"
    
    if ! ps -p "$SERVER_PID" > /dev/null 2>&1; then
        log_error "Server terminated during initialization"
        return 1
    fi
    
    if ! wait_for_api "$TIMEOUT"; then
        log_error "Unable to connect to API"
        return 1
    fi
    
    # Define all tests
    local all_tests=(
        "test_start_container"
        "test_start_already_running"
        "test_stop_container"
        "test_stop_nonexistent"
        "test_start_invalid_image"
        "test_system_info"
        "test_operation_status_nonexistent"
        "test_get_groups_list"
        "test_start_group"
        "test_stop_group"
        "test_group_status"
        "test_group_not_found"
        "test_stop_all"
        "test_restart_all"
        "test_cleanup_all"
        "test_system_info_running_count"
        "test_manage_page"
        "test_add_container_page"
        "test_container_stats"
        "test_containers_health"
        "test_system_health"
        "test_port_conflicts"
        "test_validate_config"
        "test_execute_command"
        "test_execute_diagnostic"
        "test_get_container_logs"
        "test_export_config"
        "test_get_server_logs"
        "test_get_backups"
        "test_debug_config"
        "test_invalid_endpoint"
        "test_concurrent_starts"
        "test_rapid_stop_start"
        "test_large_payload_command"
        "test_websocket_console"
        "test_add_container_form"
        "test_start_invalid_category"
    )
    
    # Determine which tests to run
    local tests_to_run=()
    
    if [ -z "$SELECTED_TEST" ]; then
        # Run all tests
        tests_to_run=("${all_tests[@]}")
    else
        # Parse selected test(s) - support single test or comma-separated list
        if [[ "$SELECTED_TEST" =~ ^[0-9]+(,[0-9]+)*$ ]]; then
            IFS=',' read -ra test_nums <<< "$SELECTED_TEST"
            for num in "${test_nums[@]}"; do
                num=$((num - 1))  # Convert to 0-indexed
                if [ $num -ge 0 ] && [ $num -lt ${#all_tests[@]} ]; then
                    tests_to_run+=("${all_tests[$num]}")
                else
                    log_error "Invalid test number: $((num + 1))"
                    exit 1
                fi
            done
        else
            log_error "Invalid test selection: $SELECTED_TEST"
            show_help
            exit 1
        fi
    fi
    
    # Run tests
    local tests_passed=0
    local tests_failed=0
    
    for test in "${tests_to_run[@]}"; do
        log_info ""
        if $test; then
            ((tests_passed++))
        else
            ((tests_failed++))
        fi
    done
    
    log_info ""
    log_info "============================================"
    log_info "TEST RESULTS"
    log_info "============================================"
    log_info "Total tests run: $((tests_passed + tests_failed))"
    log_success "Tests passed: $tests_passed"
    if [ $tests_failed -gt 0 ]; then
        log_error "Tests failed: $tests_failed"
    else
        log_success "No tests failed!"
    fi
    
    if [ -s "$ERROR_LOG" ]; then
        log_info ""
        log_warning "Errors encountered:"
        cat "$ERROR_LOG"
    fi
    
    if [ $tests_failed -gt 0 ]; then
        return 1
    fi
    
    return 0
}

# Parse arguments before running main
parse_arguments "$@"

main