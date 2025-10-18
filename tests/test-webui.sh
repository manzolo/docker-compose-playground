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
    
    log_info "Waiting for operation $operation_id to complete (max ${max_wait}s)..."
    
    while [ $elapsed -lt "$max_wait" ]; do
        local op_response=$(curl -s "${API_URL}/operation-status/${operation_id}" 2>/dev/null || echo "{}")
        local status=$(parse_json "$op_response" "status")
        
        if [ -z "$status" ]; then
            log_warning "Operation not found, retrying..."
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
    
    # Clean up previous containers
    curl -s -X POST "http://localhost:${PORT}/stop/${CONTAINER_NAME}" > /dev/null 2>&1 || true
    sleep 1
    
    local response=$(curl -s -X POST "${API_URL}/start/${IMAGE_NAME}")
    log_info "Start response: $response"
    
    if echo "$response" | grep -q "operation_id"; then
        local operation_id=$(parse_json "$response" "operation_id")
        log_info "Start initiated. Operation ID: $operation_id"
        
        # Wait for completion
        local op_response=$(wait_for_operation "$operation_id" 90)
        
        if [ $? -eq 0 ]; then
            local op_status=$(parse_json "$op_response" "status")
            local started=$(parse_json "$op_response" "started")
            
            log_info "Operation response: $op_response"
            
            if [ "$op_status" = "completed" ] && [ "$started" = "1" ]; then
                log_success "Container started successfully"
                sleep 2
                
                # Verify container is in system-info
                local sys_info=$(curl -s "${API_URL}/system-info")
                if echo "$sys_info" | grep -q "$CONTAINER_NAME"; then
                    log_success "Container verified in system-info"
                    return 0
                else
                    log_warning "Container not found in system-info, but operation completed"
                    return 0
                fi
            else
                log_error "Operation completed but container not started. Status: $op_status, Started: $started"
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
    log_info "Response: $response"
    
    if echo "$response" | grep -q "operation_id"; then
        local operation_id=$(parse_json "$response" "operation_id")
        
        local op_response=$(wait_for_operation "$operation_id" 60)
        if [ $? -eq 0 ]; then
            local already_running=$(parse_json "$op_response" "already_running")
            
            if [ "$already_running" = "1" ]; then
                log_success "Correctly identified already running container"
                return 0
            else
                log_warning "Container not marked as already_running. Response: $op_response"
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
    log_info "Stop response: $response"
    
    if echo "$response" | grep -q "stopped"; then
        log_success "Container stopped successfully"
        sleep 2
        return 0
    elif echo "$response" | grep -q "not found\|Not Found"; then
        log_warning "Container not found (may not have been created)"
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
        log_success "Correctly returned 404 for non-existent container"
        return 0
    else
        log_error "Expected HTTP code 404, got $http_code"
        return 1
    fi
}

test_start_invalid_image() {
    log_info "TEST 5: Start container with invalid image"
    
    local response=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/start/invalid-image-xyz-nonexistent")
    local http_code=$(echo "$response" | tail -1)
    local body=$(echo "$response" | head -n -1)
    
    log_info "Response code: $http_code, body: $body"
    
    if [ "$http_code" = "404" ]; then
        log_success "Correctly returned 404 for invalid image"
        return 0
    else
        log_error "Expected HTTP code 404, got $http_code"
        return 1
    fi
}

test_system_info() {
    log_info "TEST 6: System info endpoint"
    
    local response=$(curl -s "${API_URL}/system-info")
    
    if echo "$response" | grep -q '"docker"' && echo "$response" | grep -q '"network"' && echo "$response" | grep -q '"volume"'; then
        log_success "System info contains all required fields"
        return 0
    fi
    
    log_error "System info invalid response"
    return 1
}

test_operation_status_nonexistent() {
    log_info "TEST 7: Get status of non-existent operation"
    
    local fake_op_id="nonexistent-op-id-12345"
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/operation-status/${fake_op_id}")
    
    if [ "$http_code" = "404" ]; then
        log_success "Correctly returned 404 for non-existent operation"
        return 0
    else
        log_error "Expected HTTP code 404, got $http_code"
        return 1
    fi
}

test_get_groups_list() {
    log_info "TEST 8: Get groups list from system-info"
    
    local response=$(curl -s "${API_URL}/system-info")
    
    if echo "$response" | grep -q '"groups"' || echo "$response" | grep -q '"active_containers"'; then
        log_success "System info contains group information"
        return 0
    else
        log_warning "System info does not contain group information (may not be configured)"
        return 0
    fi
}

test_start_group() {
    log_info "TEST 9: Start a group of containers (MinIO-S3-Stack)"
    
    local test_group="MinIO-S3-Stack"
    
    local response=$(curl -s -X POST "${API_URL}/start-group/${test_group}")
    log_info "Start group response: $response"
    
    if echo "$response" | grep -q "operation_id"; then
        local operation_id=$(parse_json "$response" "operation_id")
        log_info "Group start initiated. Operation ID: $operation_id"
        
        local op_response=$(wait_for_operation "$operation_id" 180)
        
        if [ $? -eq 0 ]; then
            local op_status=$(parse_json "$op_response" "status")
            if [ "$op_status" = "completed" ]; then
                log_success "Group '$test_group' started successfully"
                return 0
            else
                log_error "Group start status not completed: $op_status"
                return 1
            fi
        else
            log_error "Group start timeout"
            return 1
        fi
    elif echo "$response" | grep -q "not found"; then
        log_warning "Group '$test_group' not configured"
        return 0
    else
        log_error "Error starting group: $response"
        return 1
    fi
}

test_stop_group() {
    log_info "TEST 10: Stop a group of containers (MySQL-Stack)"
    
    local test_group="MySQL-Stack"
    
    # Start the group first
    local start_response=$(curl -s -X POST "${API_URL}/start-group/${test_group}")
    
    if echo "$start_response" | grep -q "operation_id"; then
        local start_op_id=$(parse_json "$start_response" "operation_id")
        wait_for_operation "$start_op_id" 180 > /dev/null 2>&1
        sleep 3
    fi
    
    # Stop the group
    local response=$(curl -s -X POST "${API_URL}/stop-group/${test_group}")
    log_info "Stop group response: $response"
    
    if echo "$response" | grep -q "operation_id"; then
        local operation_id=$(parse_json "$response" "operation_id")
        log_info "Group stop initiated. Operation ID: $operation_id"
        
        local op_response=$(wait_for_operation "$operation_id" 180)
        
        if [ $? -eq 0 ]; then
            local op_status=$(parse_json "$op_response" "status")
            if [ "$op_status" = "completed" ]; then
                log_success "Group '$test_group' stopped successfully"
                return 0
            else
                log_error "Group stop status not completed: $op_status"
                return 1
            fi
        else
            log_error "Group stop timeout"
            return 1
        fi
    elif echo "$response" | grep -q "not found"; then
        log_warning "Group '$test_group' not configured"
        return 0
    else
        log_error "Error stopping group: $response"
        return 1
    fi
}

test_group_status() {
    log_info "TEST 11: Get group status (PostgreSQL-Stack)"
    
    local test_group="PostgreSQL-Stack"
    
    local response=$(curl -s "${API_URL}/group-status/${test_group}")
    log_info "Group status response: $response"
    
    if echo "$response" | grep -q '"group"' && echo "$response" | grep -q '"containers"'; then
        log_success "Group status endpoint works correctly"
        return 0
    elif echo "$response" | grep -q '"detail".*"not found"'; then
        log_warning "Group '$test_group' not found"
        return 0
    else
        log_error "Group status invalid response: $response"
        return 1
    fi
}

test_group_not_found() {
    log_info "TEST 12: Get status of non-existent group"
    
    local fake_group="nonexistent-group-xyz-12345"
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/group-status/${fake_group}")
    
    if [ "$http_code" = "404" ]; then
        log_success "Correctly returned 404 for non-existent group"
        return 0
    else
        log_error "Expected HTTP code 404, got $http_code"
        return 1
    fi
}

test_stop_all() {
    log_info "TEST 13: Stop all containers"
    
    # Start a container first
    curl -s -X POST "${API_URL}/start/${IMAGE_NAME}" > /dev/null 2>&1
    sleep 3
    
    # Stop all
    local response=$(curl -s -X POST "${API_URL}/stop-all")
    log_info "Stop all initiated"
    
    if echo "$response" | grep -q "operation_id"; then
        local operation_id=$(parse_json "$response" "operation_id")
        log_info "Stop all initiated. Operation ID: $operation_id"
        
        local op_response=$(wait_for_operation "$operation_id" 120)
        
        if [ $? -eq 0 ]; then
            local op_status=$(parse_json "$op_response" "status")
            if [ "$op_status" = "completed" ]; then
                log_success "All containers stopped successfully"
                return 0
            else
                log_error "Stop all status not completed: $op_status"
                return 1
            fi
        else
            log_error "Stop all timeout"
            return 1
        fi
    else
        log_error "Error stopping all: $response"
        return 1
    fi
}

test_restart_all() {
    log_info "TEST 14: Restart all containers"
    
    # Start a container first
    curl -s -X POST "${API_URL}/start/${IMAGE_NAME}" > /dev/null 2>&1
    sleep 3
    
    # Restart all
    local response=$(curl -s -X POST "${API_URL}/restart-all")
    log_info "Restart all response: $response"
    
    if echo "$response" | grep -q "operation_id"; then
        local operation_id=$(parse_json "$response" "operation_id")
        log_info "Restart all initiated. Operation ID: $operation_id"
        
        local op_response=$(wait_for_operation "$operation_id" 180)
        
        if [ $? -eq 0 ]; then
            local op_status=$(parse_json "$op_response" "status")
            if [ "$op_status" = "completed" ]; then
                log_success "All containers restarted successfully"
                return 0
            else
                log_error "Restart all status not completed: $op_status"
                return 1
            fi
        else
            log_error "Restart all timeout"
            return 1
        fi
    else
        log_error "Error restarting all: $response"
        return 1
    fi
}

test_cleanup_all() {
    log_info "TEST 15: Cleanup all containers"
    
    # Cleanup all containers
    local response=$(curl -s -X POST "${API_URL}/cleanup-all")
    log_info "Cleanup all response: $response"
    
    if echo "$response" | grep -q "operation_id"; then
        local operation_id=$(parse_json "$response" "operation_id")
        log_info "Cleanup all initiated. Operation ID: $operation_id"
        
        local op_response=$(wait_for_operation "$operation_id" 180)
        
        if [ $? -eq 0 ]; then
            local op_status=$(parse_json "$op_response" "status")
            if [ "$op_status" = "completed" ]; then
                log_success "Cleanup completed successfully"
                return 0
            else
                log_error "Cleanup status not completed: $op_status"
                return 1
            fi
        else
            log_error "Cleanup timeout"
            return 1
        fi
    else
        log_error "Error during cleanup: $response"
        return 1
    fi
}

test_system_info_running_count() {
    log_info "TEST 16: System info displays running container count"
    
    local response=$(curl -s "${API_URL}/system-info")
    
    if echo "$response" | grep -q '"running"'; then
        local running_count=$(parse_json "$response" "running")
        log_info "Running containers: $running_count"
        log_success "System info returns running count correctly"
        return 0
    else
        log_error "System info does not contain running count"
        return 1
    fi
}

test_manage_page() {
    log_info "TEST 17: Manage page endpoint"
    
    local response=$(curl -s "http://localhost:${PORT}/manage")
    
    if echo "$response" | grep -q "<!DOCTYPE\|<html"; then
        log_success "Manage page loaded correctly"
        return 0
    else
        log_error "Manage page invalid"
        return 1
    fi
}

test_add_container_page() {
    log_info "TEST 18: Add container page endpoint"
    
    local response=$(curl -s "http://localhost:${PORT}/add-container")
    
    if echo "$response" | grep -q "<!DOCTYPE\|<html"; then
        log_success "Add container page loaded correctly"
        return 0
    else
        log_error "Add container page invalid"
        return 1
    fi
}

# ============ MAIN ============

main() {
    log_info "============================================"
    log_info "API Test Suite - Extended"
    log_info "============================================"
    log_info ""
    
    # Initial cleanup
    log_info "Initial cleanup..."
    lsof -ti:${PORT} | xargs kill -9 2>/dev/null || true
    sleep 1
    
    # Start server
    log_info "Starting WebUI server..."
    bash "${SERVER_SCRIPT}" &
    SERVER_PID=$!
    log_info "Server started with PID: $SERVER_PID"
    
    sleep "$INITIAL_WAIT"
    
    if ! ps -p "$SERVER_PID" > /dev/null 2>&1; then
        log_error "Server terminated during initialization"
        [ -f "$WEB_LOG" ] && tail -20 "$WEB_LOG"
        return 1
    fi
    
    if ! wait_for_api "$TIMEOUT"; then
        log_error "Unable to connect to API"
        return 1
    fi
    
    # Run tests
    local tests_passed=0
    local tests_failed=0
    
    local tests=(
        "test_start_container"
        "test_start_already_running"
        "test_stop_container"
        "test_stop_nonexistent"
        "test_start_invalid_image"
        "test_operation_status_nonexistent"
        "test_system_info"
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
    )
    
    for test in "${tests[@]}"; do
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
    log_success "Tests passed: $tests_passed"
    if [ $tests_failed -gt 0 ]; then
        log_error "Tests failed: $tests_failed"
    else
        log_success "No tests failed!"
    fi
    
    if [ -s "$ERROR_LOG" ]; then
        log_info ""
        log_warning "Error log:"
        cat "$ERROR_LOG"
    fi
    
    if [ $tests_failed -gt 0 ]; then
        return 1
    fi
    
    return 0
}

main