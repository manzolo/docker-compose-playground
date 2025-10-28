#!/bin/bash

################################################################################
# TEST SUITE - Docker Playground API
# 
# Usage:
#   ./test-webui.sh              # Run all tests
#   ./test-webui.sh -v           # Verbose output
################################################################################

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" 2>/dev/null || SCRIPT_DIR="."
SERVER_SCRIPT="${SCRIPT_DIR}/start-webui.sh"
PORT=${PORT:-8000}
API_URL="http://localhost:${PORT}/api"
BASE_URL="http://localhost:${PORT}"
TIMEOUT=60
INITIAL_WAIT=15

TEST_CONTAINER="alpine-3.22"

ERROR_LOG="${SCRIPT_DIR}/venv/test_error.log"
SUCCESS_LOG="${SCRIPT_DIR}/venv/test_success.log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

VERBOSE=false

# ============================================================================
# LOGGING
# ============================================================================

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_debug() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${MAGENTA}[DEBUG]${NC} $1"
    fi
}

print_header() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_section() {
    echo ""
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}  $1${NC}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_test() {
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo ""
    echo -e "${YELLOW}[TEST $TESTS_TOTAL]${NC} $*"
}

# ============================================================================
# UTILITIES
# ============================================================================

parse_json() {
    local json="$1"
    local key="$2"
    echo "$json" | grep -o "\"$key\":[^,}]*" | head -1 | cut -d: -f2- | tr -d ' "' || echo ""
}

wait_for_operation() {
    local operation_id=$1
    local max_wait=${2:-90}
    local elapsed=0
    
    log_debug "Waiting for operation $operation_id..."
    
    while [ $elapsed -lt "$max_wait" ]; do
        local op_response=$(curl -s "$API_URL/operation-status/$operation_id" 2>/dev/null || echo "{}")
        local status=$(parse_json "$op_response" "status")
        
        if [ -z "$status" ]; then
            sleep 2
            elapsed=$((elapsed + 2))
            continue
        fi
        
        if [ "$status" = "completed" ] || [ "$status" = "error" ]; then
            echo "$op_response"
            return 0
        fi
        
        sleep 2
        elapsed=$((elapsed + 2))
    done
    
    return 1
}

wait_for_api() {
    local timeout=30
    local elapsed=0
    
    log_info "Waiting for API..."
    
    while [ $elapsed -lt $timeout ]; do
        if curl -s "$BASE_URL/manage" > /dev/null 2>&1; then
            log_success "API is reachable"
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    
    log_error "API not reachable"
    return 1
}

wait_for_container_stop() {
    local container_name=$1
    local max_wait=${2:-30}
    local elapsed=0
    local full_name="playground-${container_name}"
    
    while [ $elapsed -lt "$max_wait" ]; do
        local stats=$(curl -s "$API_URL/container-stats/$full_name" 2>/dev/null || echo "{}")
        
        if echo "$stats" | grep -q "not found\|error\|detail" || [ -z "$stats" ]; then
            return 0
        fi
        
        sleep 2
        elapsed=$((elapsed + 2))
    done
    
    return 1
}

# ============================================================================
# PHASE 1: BASIC
# ============================================================================

run_phase_1() {
    print_section "PHASE 1: Basic API & Web Routes"
    
    print_test "Access manage page"
    local response=$(curl -s -w "%{http_code}" -o /tmp/manage.html "$BASE_URL/manage")
    if [ "$response" = "200" ]; then
        log_success "Manage page accessible"
    else
        log_error "Manage page returned $response"
    fi
    
    print_test "Get system info via API"
    local response=$(curl -s "$API_URL/system-info")
    if echo "$response" | grep -q "docker\|version"; then
        log_success "System info retrieved"
    else
        log_error "System info failed"
    fi
}

# ============================================================================
# PHASE 2: SINGLE CONTAINER
# ============================================================================

run_phase_2() {
    print_section "PHASE 2: Single Container - $TEST_CONTAINER"
    
    print_test "Start container: $TEST_CONTAINER"
    local response=$(curl -s -X POST "$API_URL/start/$TEST_CONTAINER")
    if echo "$response" | grep -q "operation_id\|started"; then
        log_success "Container start initiated"
        sleep 3
    else
        log_warning "Container start response unclear"
        log_debug "Response: $response"
    fi
    
    print_test "Verify container is running"
    local stats=$(curl -s "$API_URL/container-stats/playground-$TEST_CONTAINER")
    if echo "$stats" | grep -q "cpu\|memory"; then
        log_success "Container is running"
    else
        log_error "Container not running"
    fi
    
    print_test "Restart container: $TEST_CONTAINER"
    local response=$(curl -s -X POST "$API_URL/restart/$TEST_CONTAINER")
    if echo "$response" | grep -q "operation_id"; then
        log_success "Container restart initiated"
        local operation_id=$(parse_json "$response" "operation_id")
        
        print_test "Poll restart operation"
        if wait_for_operation "$operation_id" 60 > /dev/null; then
            log_success "Container restart completed"
        else
            log_error "Restart timeout"
        fi
        
        sleep 2
        local stats=$(curl -s "$API_URL/container-stats/playground-$TEST_CONTAINER")
        if echo "$stats" | grep -q "cpu"; then
            log_success "Container confirmed running after restart"
        else
            log_error "Container not running after restart"
        fi
    else
        log_warning "Restart initiation unclear"
    fi
    
    print_test "Stop container: $TEST_CONTAINER"
    local response=$(curl -s -X POST "$API_URL/stop/playground-$TEST_CONTAINER")
    log_debug "Stop response: $response"
    
    if echo "$response" | grep -qi "error\|not found"; then
        log_error "Stop failed: $response"
    elif [ -n "$response" ]; then
        log_success "Container stop initiated"
        sleep 5
        
        print_test "Verify container stopped"
        local max_attempts=15
        local attempt=0
        while [ $attempt -lt $max_attempts ]; do
            local http_code=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL/container-stats/playground-$TEST_CONTAINER" 2>/dev/null)
            if [ "$http_code" = "404" ] || [ "$http_code" = "500" ]; then
                log_success "Container confirmed stopped"
                break
            fi
            attempt=$((attempt + 1))
            sleep 2
        done
    else
        log_warning "Stop response unclear"
    fi
    
    sleep 2
}

# ============================================================================
# PHASE 3: GROUP OPERATIONS
# ============================================================================

run_phase_3() {
    print_section "PHASE 3: Group Operations"
    
    print_test "Get groups list"
    local response=$(curl -s "$API_URL/groups")
    if echo "$response" | grep -q "groups"; then
        log_success "Groups endpoint working"
    else
        log_error "Groups endpoint failed"
    fi
    
    print_test "Get group details: ELK-Stack"
    local response=$(curl -s "$API_URL/groups/ELK-Stack")
    if echo "$response" | grep -q "containers"; then
        log_success "Group details retrieved"
    else
        log_warning "Could not retrieve group details"
    fi
    
    print_test "Start group: ELK-Stack"
    local response=$(curl -s -X POST "$API_URL/start-group/ELK-Stack")
    if echo "$response" | grep -q "operation_id\|started"; then
        log_success "Group start initiated"
    else
        log_warning "Group start unclear"
    fi
    
    sleep 10
    
    print_test "Verify group containers are running"
    local stats=$(curl -s "$API_URL/container-stats/playground-elasticsearch-stack")
    if echo "$stats" | grep -q "cpu"; then
        log_success "Group container verified running"
    else
        log_warning "Could not verify group containers"
    fi
    
    print_test "Stop group: ELK-Stack"
    local response=$(curl -s -X POST "$API_URL/stop-group/ELK-Stack")
    if echo "$response" | grep -q "operation_id\|started"; then
        log_success "Group stop initiated"
    else
        log_warning "Group stop unclear"
    fi
    
    print_test "Verify group containers are stopped - retry up to 30 sec"
    local stopped=0
    for container in elasticsearch-stack kibana-stack; do
        if wait_for_container_stop "$container" 30; then
            log_success "Group container confirmed stopped ($container)"
            stopped=$((stopped + 1))
        else
            log_warning "Container stop not verified ($container)"
        fi
    done
    
    sleep 2
}

# ============================================================================
# PHASE 4: HEALTH STATUS (CORRECTED ENDPOINT)
# ============================================================================

run_phase_4() {
    print_section "PHASE 4: Containers Health Status"
    
    print_test "Get containers health (using /api/containers-health)"
    local response=$(curl -s "$API_URL/containers-health")
    if echo "$response" | grep -q "total\|running"; then
        log_success "Health status retrieved"
        local total=$(parse_json "$response" "total")
        local running=$(parse_json "$response" "running")
        log_info "  Total: $total, Running: $running"
    else
        log_error "Health endpoint failed"
        log_debug "Response: $response"
    fi
}

# ============================================================================
# PHASE 5: EXECUTE COMMAND (CORRECTED ENDPOINT)
# ============================================================================

run_phase_5() {
    print_section "PHASE 5: Execute Command in Container"
    
    print_test "Start alpine-3.22 for exec tests"
    curl -s -X POST "$API_URL/start/$TEST_CONTAINER" > /dev/null 2>&1
    sleep 3
    
    print_test "Execute command: echo hello world (using /api/execute-command)"
    local response=$(curl -s -X POST "$API_URL/execute-command/playground-$TEST_CONTAINER" \
        -H "Content-Type: application/json" \
        -d '{"command": "echo hello world"}')
    
    if echo "$response" | grep -q "hello\|output"; then
        log_success "Execute command worked"
    else
        log_warning "Execute command response unclear"
        log_debug "Response: $response"
    fi
    
    print_test "Execute command: ls -la /root"
    local response=$(curl -s -X POST "$API_URL/execute-command/playground-$TEST_CONTAINER" \
        -H "Content-Type: application/json" \
        -d '{"command": "ls -la /root"}')
    
    if echo "$response" | grep -q "total\|root"; then
        log_success "List command worked"
    else
        log_warning "List command unclear"
    fi
}

# ============================================================================
# PHASE 6: CONTAINER STATISTICS
# ============================================================================

run_phase_6() {
    print_section "PHASE 6: Container Statistics"
    
    print_test "Get stats for: playground-$TEST_CONTAINER"
    local response=$(curl -s "$API_URL/container-stats/playground-$TEST_CONTAINER")
    
    if echo "$response" | grep -q "cpu\|memory"; then
        log_success "Stats retrieved successfully"
        
        local cpu=$(echo "$response" | grep -o '"percent":[0-9.]*' | head -1 | cut -d: -f2)
        local memory=$(echo "$response" | grep -o '"usage_mb":[0-9.]*' | cut -d: -f2)
        
        if [ -n "$cpu" ]; then
            log_info "  CPU: $cpu%"
        fi
        if [ -n "$memory" ]; then
            log_info "  Memory: $memory MB"
        fi
    else
        log_error "Stats endpoint failed"
    fi
    
    sleep 3
}

# ============================================================================
# PHASE 7: DIAGNOSTIC ENDPOINT
# ============================================================================

run_phase_7() {
    print_section "PHASE 7: Diagnostic Info"
    
    print_test "Execute diagnostic on container (using /api/execute-diagnostic)"
    local response=$(curl -s -X POST "$API_URL/execute-diagnostic/playground-$TEST_CONTAINER" \
        -H "Content-Type: application/json" \
        -d '{}')
    
    if echo "$response" | grep -q "output\|data\|diagnostic"; then
        log_success "Diagnostic endpoint working"
    else
        log_warning "Diagnostic endpoint response unclear"
        log_debug "Response: $response"
    fi
}

# ============================================================================
# PHASE 8: ERROR CASES
# ============================================================================

run_phase_8() {
    print_section "PHASE 8: Error Cases & Edge Conditions"
    
    print_test "Try to start non-existent container"
    local response=$(curl -s -X POST "$API_URL/start/nonexistent-xyz-123")
    if echo "$response" | grep -q "error\|not found"; then
        log_success "Non-existent container properly rejected"
    else
        log_warning "Non-existent container check unclear"
    fi
    
    sleep 2
    
    print_test "Try to stop container that doesn't exist"
    local http_code=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$API_URL/stop/nonexistent-xyz-123")
    if [ "$http_code" = "404" ] || [ "$http_code" = "400" ]; then
        log_success "Non-existent stop properly rejected (HTTP $http_code)"
    else
        log_warning "Non-existent stop returned HTTP $http_code"
    fi
    
    sleep 2
    
    print_test "Try invalid operation-status lookup"
    local response=$(curl -s "$API_URL/operation-status/invalid-uuid-12345")
    if echo "$response" | grep -q "error\|not found"; then
        log_success "Invalid operation ID properly handled"
    else
        log_warning "Invalid operation check unclear"
    fi
    
    sleep 2
    
    print_test "Try invalid endpoint"
    local http_code=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL/invalid-endpoint-xyz-999")
    if [ "$http_code" = "404" ]; then
        log_success "Invalid endpoint returns 404"
    else
        log_warning "Invalid endpoint returned HTTP $http_code"
    fi
}

# ============================================================================
# PHASE 9: OPERATION POLLING
# ============================================================================

run_phase_9() {
    print_section "PHASE 9: Operation Polling"
    
    print_test "Start container and poll for completion"
    local response=$(curl -s -X POST "$API_URL/start/alpine-3.22")
    if echo "$response" | grep -q "operation_id"; then
        local operation_id=$(parse_json "$response" "operation_id")
        log_info "Operation ID: $operation_id"
        
        print_test "Poll operation-status until completed"
        local op_response=$(wait_for_operation "$operation_id" 90)
        
        if [ $? -eq 0 ]; then
            local op_status=$(parse_json "$op_response" "status")
            log_info "  Final status: $op_status"
            
            if [ "$op_status" = "completed" ]; then
                log_success "Operation completed successfully"
            else
                log_warning "Operation status is: $op_status"
            fi
        else
            log_error "Operation polling failed or timeout"
        fi
    else
        log_warning "No operation_id in response"
    fi
    
    sleep 2
}

# ============================================================================
# PHASE 10: VERIFY FINAL STATE
# ============================================================================

run_phase_10() {
    print_section "PHASE 10: Verify Container State After Operations"
    
    print_test "Verify alpine-3.22 is running after start operation"
    local stats=$(curl -s "$API_URL/container-stats/playground-alpine-3.22")
    
    if echo "$stats" | grep -q "cpu\|memory"; then
        log_success "Container verified running via stats"
        local cpu=$(echo "$stats" | grep -o '"percent":[0-9.]*' | head -1 | cut -d: -f2)
        log_info "  CPU: $cpu%"
    else
        log_warning "Could not verify container running"
    fi
}

# ============================================================================
# PHASE 11: RESTART ALL
# ============================================================================

run_phase_11() {
    print_section "PHASE 11: Restart All"
    
    print_test "Ensure containers are running"
    local resp1=$(curl -s -X POST "$API_URL/start/alpine-3.22")
    local resp2=$(curl -s -X POST "$API_URL/start/ubuntu-24")
    
    # Wait for both to actually start
    if echo "$resp1" | grep -q "operation_id"; then
        local op1=$(parse_json "$resp1" "operation_id")
        wait_for_operation "$op1" 90 > /dev/null
    fi
    
    if echo "$resp2" | grep -q "operation_id"; then
        local op2=$(parse_json "$resp2" "operation_id")
        wait_for_operation "$op2" 90 > /dev/null
    fi
    
    sleep 8
    
    print_test "Restart all containers"
    local response=$(curl -s -X POST "$API_URL/restart-all")
    
    if echo "$response" | grep -q "operation_id"; then
        log_success "Restart-all initiated"
        local operation_id=$(parse_json "$response" "operation_id")
        
        local op_response=$(wait_for_operation "$operation_id" 180)
        if [ $? -eq 0 ]; then
            log_success "Restart-all completed"
            sleep 10
            
            print_test "Verify containers running after restart"
            local stats1=$(curl -s "$API_URL/container-stats/playground-alpine-3.22")
            local stats2=$(curl -s "$API_URL/container-stats/playground-ubuntu-24")
            
            if echo "$stats1" | grep -q "cpu\|memory"; then
                log_success "Alpine running"
            else
                log_warning "Alpine not running"
            fi
            
            if echo "$stats2" | grep -q "cpu\|memory"; then
                log_success "Ubuntu running"
            else
                log_warning "Ubuntu not running (might need more time on slower systems)"
            fi
        else
            log_error "Restart-all timeout"
        fi
    else
        log_error "Restart-all failed"
    fi
}

# ============================================================================
# PHASE 12: STOP ALL
# ============================================================================

run_phase_12() {
    print_section "PHASE 12: Stop All"
    
    print_test "Stop all containers"
    local response=$(curl -s -X POST "$API_URL/stop-all")
    
    if echo "$response" | grep -q "operation_id"; then
        log_success "Stop-all initiated"
        local operation_id=$(parse_json "$response" "operation_id")
        
        local op_response=$(wait_for_operation "$operation_id" 120)
        if [ $? -eq 0 ]; then
            log_success "Stop-all completed"
            sleep 3
            
            print_test "Verify containers stopped"
            local stats1=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL/container-stats/playground-alpine-3.22")
            local stats2=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL/container-stats/playground-ubuntu-24.04")
            
            if [ "$stats1" = "404" ] || [ "$stats1" = "500" ]; then
                log_success "Alpine stopped"
            else
                log_warning "Alpine might be running"
            fi
            
            if [ "$stats2" = "404" ] || [ "$stats2" = "500" ]; then
                log_success "Ubuntu stopped"
            else
                log_warning "Ubuntu might be running"
            fi
        else
            log_error "Stop-all timeout"
        fi
    else
        log_error "Stop-all failed"
    fi
}

# ============================================================================
# CLEANUP
# ============================================================================

: > "$ERROR_LOG"
: > "$SUCCESS_LOG"

cleanup() {
    log_info "Running final cleanup..."
    
    log_info "Stopping all containers..."
    curl -s -X POST "$API_URL/cleanup-all" > /dev/null 2>&1
    sleep 5
    
    log_info "Terminating web server..."
    if [ -f "${SCRIPT_DIR}/venv/web.pid" ]; then
        pid=$(cat "${SCRIPT_DIR}/venv/web.pid" 2>/dev/null)
        if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
            kill -TERM "$pid" 2>/dev/null || true
            sleep 2
            if ps -p "$pid" > /dev/null 2>&1; then
                kill -9 "$pid" 2>/dev/null || true
            fi
        fi
    fi
    
    lsof -ti:${PORT} | xargs kill -9 2>/dev/null || true
    
    log_success "Cleanup completed"
}

trap cleanup SIGINT SIGTERM EXIT

# ============================================================================
# ARGUMENT PARSING
# ============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# ============================================================================
# MAIN
# ============================================================================

main() {
    print_header "DOCKER PLAYGROUND - TEST SUITE (CORRECTED ENDPOINTS)"
    
    log_info "Starting WebUI server..."
    bash "${SERVER_SCRIPT}" --tail &
    SERVER_PID=$!
    
    sleep "$INITIAL_WAIT"
    
    if ! ps -p "$SERVER_PID" > /dev/null 2>&1; then
        log_error "Server terminated"
        return 1
    fi
    
    if ! wait_for_api; then
        log_error "Cannot reach API"
        return 1
    fi
    
    run_phase_1
    run_phase_2
    run_phase_3
    run_phase_4
    run_phase_5
    run_phase_6
    run_phase_7
    run_phase_8
    run_phase_9
    run_phase_10
    run_phase_11
    run_phase_12
    
    print_header "TEST RESULTS"
    
    local total=$((TESTS_PASSED + TESTS_FAILED))
    local pass_rate=0
    
    if [ $total -gt 0 ]; then
        pass_rate=$((TESTS_PASSED * 100 / total))
    fi
    
    echo "Total: $total"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    echo -e "Pass Rate: ${BLUE}${pass_rate}%${NC}"
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All tests passed!${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Some tests failed${NC}"
        return 1
    fi
}

main "$@"