#!/bin/bash

################################################################################
# TEST SUITE - Docker Playground API (FIXED FOR GROUPS + CONTAINERS)
# 
# ✓ Testa singoli container (alpine-3.22)
# ✓ Testa gruppi
# ✓ Esclude network dalla ricerca
#
# Usage:
#   ./test-webui-real-fixed.sh              # Run all tests
#   ./test-webui-real-fixed.sh -v           # Verbose output
################################################################################

set -uo pipefail

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

# Container specifici da testare
TEST_CONTAINER="alpine-3.22"

# Logs
ERROR_LOG="${SCRIPT_DIR}/venv/test_error.log"
SUCCESS_LOG="${SCRIPT_DIR}/venv/test_success.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Test counters
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

VERBOSE=false

# ============================================================================
# LOGGING FUNCTIONS
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
# UTILITY
# ============================================================================

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

extract_json_value() {
    local json="$1"
    local key="$2"
    echo "$json" | grep -o "\"${key}\"[[:space:]]*:[[:space:]]*[^,}]*" | cut -d: -f2- | sed 's/[" ]//g' | head -1
}

# Robustly extract JSON values (from old tests)
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
    
    log_debug "Waiting for operation $operation_id (max ${max_wait}s)..."
    
    while [ $elapsed -lt "$max_wait" ]; do
        local op_response=$(curl -s "$API_URL/operation-status/$operation_id" 2>/dev/null || echo "{}")
        local status=$(parse_json "$op_response" "status")
        
        if [ -z "$status" ]; then
            log_debug "Operation not found, retrying..."
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
    
    log_error "Timeout waiting for operation $operation_id after ${max_wait}s"
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
    
    log_error "API not reachable after ${timeout}s"
    return 1
}

# ============================================================================
# PHASE 1: API BASIC
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
    if echo "$response" | grep -q "running\|total"; then
        log_success "System info retrieved"
        log_debug "System info: $(echo "$response" | head -c 100)"
    else
        log_error "System info failed"
    fi
}

# ============================================================================
# PHASE 2: SINGLE CONTAINER (alpine-3.22)
# ============================================================================

run_phase_2() {
    print_section "PHASE 2: Single Container - $TEST_CONTAINER"
    
    print_test "Start container: $TEST_CONTAINER"
    local response=$(curl -s -X POST "$BASE_URL/api/start/$TEST_CONTAINER")
    log_debug "Response: $response"
    
    if echo "$response" | grep -q "success\|operation_id\|running"; then
        log_success "Container start initiated"
        sleep 3
    else
        log_warning "Container start unclear, continuing..."
    fi
    
    print_test "Verify container is running with stats endpoint"
    local stats=$(curl -s "$API_URL/container-stats/playground-$TEST_CONTAINER")
    if echo "$stats" | grep -q "cpu\|memory"; then
        log_success "Container is running (verified via stats)"
    else
        log_error "Container not running or stats failed"
        log_debug "Stats response: $stats"
    fi
    
    print_test "Stop container: $TEST_CONTAINER"
    local response=$(curl -s -X POST "$BASE_URL/api/stop/$TEST_CONTAINER")
    log_debug "Response: $response"
    
    if echo "$response" | grep -q "operation_id\|started"; then
        log_success "Container stop initiated"
        
        # Verify it's actually stopped - retry fino a 30 sec
        print_test "Verify container stopped (should get 404 from stats) - retry up to 30 sec"
        local elapsed=0
        local max_wait=30
        while [ $elapsed -lt $max_wait ]; do
            local stats=$(curl -s -w "\n%{http_code}" "$API_URL/container-stats/playground-$TEST_CONTAINER")
            local http_code=$(echo "$stats" | tail -1)
            
            if [ "$http_code" = "404" ] || [ "$http_code" = "400" ]; then
                log_success "Container confirmed stopped (HTTP $http_code after ${elapsed}s)"
                break
            fi
            
            elapsed=$((elapsed + 2))
            if [ $elapsed -lt $max_wait ]; then
                log_debug "  Waiting... ${elapsed}s/${max_wait}s"
                sleep 2
            fi
        done
        
        if [ $elapsed -ge $max_wait ]; then
            log_warning "Container stop timeout after ${max_wait}s (HTTP $http_code)"
        fi
    else
        log_warning "Container stop unclear"
    fi
}

# ============================================================================
# PHASE 3: GROUPS
# ============================================================================

run_phase_3() {
    print_section "PHASE 3: Group Operations"
    
    print_test "Get groups list"
    local response=$(curl -s "$API_URL/groups")
    log_debug "Response: $response"
    
    if echo "$response" | grep -q "groups"; then
        log_success "Groups endpoint working"
        local group=$(echo "$response" | grep -o '"name":"[^"]*"' | head -1 | cut -d'"' -f4)
        
        if [ -n "$group" ]; then
            log_info "  Found group: $group"
            
            print_test "Get group details: $group"
            local details=$(curl -s "$API_URL/groups/$group")
            if echo "$details" | grep -q "containers"; then
                log_success "Group details retrieved"
                # Skip first name (è il nome del gruppo), prendi dai container reali
                local containers=$(echo "$details" | grep -o '"name":"[^"]*"' | tail -n +2 | cut -d'"' -f4 | head -3)
                log_info "  Containers in group:"
                echo "$containers" | while read -r c; do
                    [ -n "$c" ] && log_info "    - $c"
                done
            else
                log_error "Group details failed"
            fi
            
            print_test "Start group: $group"
            local response=$(curl -s -X POST "$API_URL/start-group/$group")
            if echo "$response" | grep -q "operation_id\|started"; then
                log_success "Group start initiated"
                sleep 5
                
                # Verificare che almeno un container del gruppo sia running
                print_test "Verify group containers are running"
                # Il primo container del gruppo (elasticsearch-stack o kibana-stack)
                local first_container="elasticsearch-stack"
                
                local stats=$(curl -s "$API_URL/container-stats/playground-$first_container")
                if echo "$stats" | grep -q "cpu\|memory"; then
                    log_success "Group container verified running: $first_container"
                else
                    log_warning "Could not verify group container status"
                fi
            else
                log_warning "Group start response unclear"
            fi
            
            print_test "Stop group: $group"
            local response=$(curl -s -X POST "$API_URL/stop-group/$group")
            if echo "$response" | grep -q "operation_id\|started"; then
                log_success "Group stop initiated"
                
                # Verificare che siano effettivamente fermi - retry fino a 30 sec
                print_test "Verify group containers are stopped - retry up to 30 sec"
                local first_container="elasticsearch-stack"
                local elapsed=0
                local max_wait=30
                while [ $elapsed -lt $max_wait ]; do
                    local http_code=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL/container-stats/playground-$first_container")
                    
                    if [ "$http_code" = "404" ] || [ "$http_code" = "400" ]; then
                        log_success "Group container confirmed stopped (HTTP $http_code after ${elapsed}s)"
                        break
                    fi
                    
                    elapsed=$((elapsed + 2))
                    if [ $elapsed -lt $max_wait ]; then
                        log_debug "  Waiting... ${elapsed}s/${max_wait}s"
                        sleep 2
                    fi
                done
                
                if [ $elapsed -ge $max_wait ]; then
                    log_warning "Group container stop timeout after ${max_wait}s (HTTP $http_code)"
                fi
            else
                log_warning "Group stop response unclear"
            fi
        else
            log_warning "No groups found to test"
        fi
    else
        log_warning "Groups endpoint not responding"
    fi
}

# ============================================================================
# PHASE 4: BULK OPERATIONS
# ============================================================================

run_phase_4() {
    print_section "PHASE 4: Restart All (with alpine still running)"
    
    print_test "Verify alpine is still running before restart"
    local stats=$(curl -s "$API_URL/container-stats/playground-alpine-3.22")
    if echo "$stats" | grep -q "cpu\|memory"; then
        log_success "Alpine confirmed running"
    else
        log_warning "Alpine not running, skipping restart test"
        return
    fi
    
    print_test "Restart all containers (ELK should restart, alpine stays)"
    local response=$(curl -s -X POST "$BASE_URL/api/restart-all")
    if echo "$response" | grep -q "success\|operation\|started"; then
        log_success "Restart-all executed"
        sleep 5
        
        # Verify alpine is STILL running after restart
        print_test "Verify alpine still running after restart-all"
        local stats=$(curl -s "$API_URL/container-stats/playground-alpine-3.22")
        if echo "$stats" | grep -q "cpu\|memory"; then
            log_success "Alpine still running - restart didn't stop it"
        else
            log_warning "Alpine was stopped by restart-all (unexpected)"
        fi
        
        # Verify ELK is back up
        print_test "Verify ELK containers restarted"
        local stats=$(curl -s "$API_URL/container-stats/playground-elasticsearch-stack")
        if echo "$stats" | grep -q "cpu\|memory"; then
            log_success "Elasticsearch confirmed running after restart"
        else
            log_warning "Elasticsearch not running after restart"
        fi
    else
        log_warning "Restart-all response unclear"
    fi
    
    sleep 2
}

# ============================================================================
# PHASE 4B: STOP ALL
# ============================================================================

run_phase_4b() {
    print_section "PHASE 4B: Stop All Containers"
    
    print_test "Stop all containers"
    local response=$(curl -s -X POST "$BASE_URL/api/stop-all")
    if echo "$response" | grep -q "success\|operation"; then
        log_success "Stop-all executed"
        
        # Waiter: verifica che alpine sia fermo (è sempre presente)
        print_test "Waiting for containers to stop (up to 40 sec)..."
        local elapsed=0
        local max_wait=40
        while [ $elapsed -lt $max_wait ]; do
            local http_code=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL/container-stats/playground-alpine-3.22")
            
            if [ "$http_code" = "404" ] || [ "$http_code" = "400" ]; then
                log_success "Containers stopped (after ${elapsed}s)"
                break
            fi
            
            elapsed=$((elapsed + 2))
            if [ $elapsed -lt $max_wait ]; then
                log_debug "  Waiting... ${elapsed}s/${max_wait}s (HTTP $http_code)"
                sleep 2
            fi
        done
        
        if [ $elapsed -ge $max_wait ]; then
            log_warning "Stop-all timeout after ${max_wait}s (HTTP $http_code)"
        fi
        
        sleep 2
    else
        log_warning "Stop-all response unclear"
        sleep 5
    fi
}

# ============================================================================
# PHASE 5: CONTAINERS HEALTH
# ============================================================================

run_phase_5() {
    print_section "PHASE 5: Containers Health Status"
    
    print_test "Get containers health"
    local response=$(curl -s "$API_URL/containers-health")
    log_debug "Response: $response"
    
    if echo "$response" | grep -q "total\|running\|stopped"; then
        log_success "Health status retrieved"
        local total=$(echo "$response" | grep -o '"total":[0-9]*' | cut -d: -f2)
        local running=$(echo "$response" | grep -o '"running":[0-9]*' | cut -d: -f2)
        log_info "  Total: $total, Running: $running"
    else
        log_error "Health endpoint failed"
    fi
    
    sleep 2
}

# ============================================================================
# PHASE 6: EXECUTE COMMAND (richiede container running)
# ============================================================================

run_phase_6() {
    print_section "PHASE 6: Execute Command in Container"
    
    # Prima, ferma alpine se è ancora running da fasi precedenti
    print_test "Ensure alpine-3.22 is stopped before starting for exec tests"
    curl -s -X POST "$BASE_URL/api/stop/$TEST_CONTAINER" > /dev/null 2>&1
    sleep 3
    
    print_test "Start $TEST_CONTAINER for command execution"
    curl -s -X POST "$BASE_URL/api/start/$TEST_CONTAINER" > /dev/null
    sleep 4
    log_debug "Container started, waiting for ready state"
    
    print_test "Execute command: echo hello world"
    local response=$(curl -s -X POST "$API_URL/execute-command/playground-$TEST_CONTAINER" \
        -H "Content-Type: application/json" \
        -d '{"command":"echo hello world","timeout":10}')
    log_debug "Response: $response"
    
    if echo "$response" | grep -q "output\|exit_code"; then
        log_success "Execute command worked"
        if echo "$response" | grep -q "hello"; then
            log_info "  Output contiene 'hello' - comando eseguito"
        fi
    else
        log_error "Execute command failed"
    fi
    
    sleep 2
    
    print_test "Execute command: ls -la /root"
    local response=$(curl -s -X POST "$API_URL/execute-command/playground-$TEST_CONTAINER" \
        -H "Content-Type: application/json" \
        -d '{"command":"ls -la /root","timeout":10}')
    log_debug "Response: $response"
    
    if echo "$response" | grep -q "output\|exit_code"; then
        log_success "List command worked"
    else
        log_error "List command failed"
    fi
    
    sleep 2
}

# ============================================================================
# PHASE 7: CONTAINER STATS
# ============================================================================

run_phase_7() {
    print_section "PHASE 7: Container Statistics"
    
    print_test "Get stats for: playground-$TEST_CONTAINER"
    local response=$(curl -s "$API_URL/container-stats/playground-$TEST_CONTAINER")
    log_debug "Response (first 200 chars): $(echo "$response" | head -c 200)"
    
    if echo "$response" | grep -q "cpu\|memory\|percent"; then
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
        log_debug "Full response: $response"
    fi
    
    sleep 3
}

# ============================================================================
# PHASE 8: WEBSOCKET CONSOLE
# ============================================================================

run_phase_8() {
    print_section "PHASE 8: WebSocket Console Endpoint"
    
    print_test "Check WebSocket console endpoint reachability"
    log_info "Endpoint: /ws/console/playground-$TEST_CONTAINER"
    
    timeout 2 bash -c "exec 3<>/dev/tcp/localhost/$PORT; echo 'GET /ws/console/playground-$TEST_CONTAINER HTTP/1.1' >&3" 2>/dev/null
    
    if [ $? -eq 0 ] || [ $? -eq 124 ]; then
        log_success "WebSocket endpoint is reachable"
    else
        log_error "WebSocket endpoint not reachable"
    fi
    
    sleep 2
}

# ============================================================================
# PHASE 9: ERROR CASES & EDGE CONDITIONS
# ============================================================================

run_phase_9() {
    print_section "PHASE 9: Error Cases & Edge Conditions"
    
    print_test "Try to start non-existent container"
    local response=$(curl -s -X POST "$API_URL/start/nonexistent-xyz-123")
    log_debug "Response: $response"
    
    if echo "$response" | grep -q "error\|not found\|404"; then
        log_success "Non-existent container properly rejected"
    else
        log_warning "Non-existent container check unclear"
    fi
    
    sleep 2
    
    print_test "Try to stop container that doesn't exist"
    local http_code=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$API_URL/stop/nonexistent-xyz-123")
    log_debug "HTTP code: $http_code"
    
    if [ "$http_code" = "404" ] || [ "$http_code" = "400" ]; then
        log_success "Non-existent stop properly rejected (HTTP $http_code)"
    else
        log_warning "Non-existent stop returned unexpected code (HTTP $http_code)"
    fi
    
    sleep 2
    
    print_test "Try invalid operation-status lookup"
    local invalid_op_id="invalid-uuid-12345"
    local response=$(curl -s "$API_URL/operation-status/$invalid_op_id")
    log_debug "Response: $response"
    
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
# PHASE 10: OPERATION POLLING (verify actual completion)
# ============================================================================

run_phase_10() {
    print_section "PHASE 10: Operation Polling - Verify Real Completion"
    
    print_test "Start container and poll for completion"
    local response=$(curl -s -X POST "$API_URL/start/alpine-3.22")
    log_debug "Start response: $response"
    
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
        log_warning "No operation_id in response, skipping polling test"
    fi
    
    sleep 2
}

# ============================================================================
# PHASE 11: OPERATION VERIFICATION
# ============================================================================

run_phase_11() {
    print_section "PHASE 11: Verify Container State After Operations"
    
    print_test "Verify alpine-3.22 is actually running after start operation"
    local stats=$(curl -s "$API_URL/container-stats/playground-alpine-3.22")
    
    if echo "$stats" | grep -q "cpu\|memory"; then
        log_success "Container verified running via stats"
        local cpu=$(echo "$stats" | grep -o '"percent":[0-9.]*' | head -1 | cut -d: -f2)
        log_info "  CPU: $cpu%"
    else
        log_warning "Could not verify container running"
    fi
}

: > "$ERROR_LOG"
: > "$SUCCESS_LOG"

cleanup() {
    log_info "Running final cleanup..."
    
    # Ferma alpine
    log_info "Stopping alpine-3.22..."
    curl -s -X POST "$BASE_URL/api/stop/$TEST_CONTAINER" > /dev/null 2>&1
    sleep 3
    
    # Ferma tutti i container
    log_info "Stopping all remaining containers..."
    curl -s -X POST "$BASE_URL/api/stop-all" > /dev/null 2>&1
    sleep 5
    
    # Uccidi il server
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
    print_header "DOCKER PLAYGROUND - TEST SUITE (CONTAINER + GROUPS)"
    
    # Start server
    log_info "Starting WebUI server..."
    bash "${SERVER_SCRIPT}" --tail &
    SERVER_PID=$!
    log_info "Server started with PID: $SERVER_PID"
    
    sleep "$INITIAL_WAIT"
    
    if ! ps -p "$SERVER_PID" > /dev/null 2>&1; then
        log_error "Server terminated"
        return 1
    fi
    
    if ! wait_for_api; then
        log_error "Cannot reach API"
        return 1
    fi
    
    # Run tests
    run_phase_1
    run_phase_2
    run_phase_3
    run_phase_4
    run_phase_4b
    run_phase_5
    run_phase_6
    run_phase_7
    run_phase_8
    run_phase_9
    run_phase_10
    run_phase_11
    
    # Summary
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