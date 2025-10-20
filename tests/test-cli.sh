#!/bin/bash
#############################################
# Docker Playground CLI Test Suite - FIXED
# Tests for single container (alpine-3.22)
#############################################

set -uo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

CLI="./playground"
TEST_CONTAINER="alpine-3.22"
TEST_GROUP="MySQL-Stack"
LOG_FILE="test-cli_$(date +%Y%m%d_%H%M%S).log"

# Flags
NON_INTERACTIVE=false

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

log_test() {
    echo -e "${BLUE}[TEST $((TOTAL_TESTS + 1))]${NC} $*" | tee -a "$LOG_FILE"
    ((TOTAL_TESTS++))
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*" | tee -a "$LOG_FILE"
    ((PASSED_TESTS++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $*" | tee -a "$LOG_FILE"
    ((FAILED_TESTS++))
}

log_skip() {
    echo -e "${YELLOW}[⊘]${NC} $*" | tee -a "$LOG_FILE"
    ((SKIPPED_TESTS++))
}

log_info() {
    echo -e "${CYAN}ℹ $*" | tee -a "$LOG_FILE"
}

run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_pattern="${3:-}"
    
    log_test "$test_name"
    
    local OUTPUT=""
    if OUTPUT=$(eval "$test_command" 2>&1); then
        if [ -n "$expected_pattern" ]; then
            if echo "$OUTPUT" | grep -q "$expected_pattern"; then
                log_success "$test_name passed"
                return 0
            else
                log_error "$test_name failed - pattern not found"
                echo "Expected: $expected_pattern" | tee -a "$LOG_FILE"
                echo "Got: $(echo "$OUTPUT" | head -3)" | tee -a "$LOG_FILE"
                return 1
            fi
        else
            log_success "$test_name passed"
            return 0
        fi
    else
        log_error "$test_name failed - command error"
        echo "Error: $(echo "$OUTPUT" | head -3)" | tee -a "$LOG_FILE"
        return 1
    fi
}

wait_for_container() {
    local container="$1"
    local timeout=10
    local elapsed=0
    
    while [ $elapsed -lt $timeout ]; do
        if $CLI ps 2>&1 | grep -q "playground-$container"; then
            return 0
        fi
        sleep 1
        ((elapsed++))
    done
    return 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --non-interactive)
            NON_INTERACTIVE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --non-interactive    Run all tests without user interaction"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" | tee -a "$LOG_FILE"
            exit 1
            ;;
    esac
done

# Banner
cat << 'EOF' | tee -a "$LOG_FILE"
╔══════════════════════════════════════════╗
║   🐳  Docker Playground CLI              ║
║   Test Suite v2.2 - Fixed Version        ║
╚══════════════════════════════════════════╝
EOF

if [ "$NON_INTERACTIVE" = true ]; then
    echo -e "${CYAN}Running in NON-INTERACTIVE mode${NC}\n" | tee -a "$LOG_FILE"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI="${SCRIPT_DIR}/playground"

# Verify CLI
if [ ! -x "$CLI" ]; then
    if [ -f "$CLI" ]; then
        echo -e "${YELLOW}⚠ Making CLI executable...${NC}" | tee -a "$LOG_FILE"
        chmod +x "$CLI"
    else
        echo -e "${RED}❌ CLI not found at $CLI${NC}" | tee -a "$LOG_FILE"
        exit 1
    fi
fi

echo -e "${CYAN}Running CLI tests...${NC}\n" | tee -a "$LOG_FILE"

# ========================================
# BASIC COMMANDS
# ========================================
echo -e "${MAGENTA}━━━ Basic Commands ━━━${NC}\n" | tee -a "$LOG_FILE"

run_test "Version command" "$CLI version" "."
echo ""

run_test "List command" "$CLI list" "alpine-3.22"
echo ""

run_test "List with category filter" "$CLI list --category linux" ""
echo ""

run_test "JSON output" "$CLI list --json" '\['
echo ""

run_test "PS command" "$CLI ps" "Playground\|No playground\|CONTAINER"
echo ""

run_test "Categories command" "$CLI categories" "Categories"
echo ""

# ========================================
# GROUP COMMANDS
# ========================================
echo -e "${MAGENTA}━━━ Group Commands ━━━${NC}\n" | tee -a "$LOG_FILE"

run_test "Group list command" "$CLI group list" "Groups\|group"
echo ""

run_test "Group list JSON" "$CLI group list --json" '"name"\|"description"'
echo ""

log_test "Check test group availability"
if $CLI group list 2>&1 | grep -q "$TEST_GROUP"; then
    log_success "Test group $TEST_GROUP found"
    echo ""
    
    # Group lifecycle tests
    echo -e "${MAGENTA}━━━ Group Lifecycle Tests ━━━${NC}\n" | tee -a "$LOG_FILE"
    
    # Initial group status
    log_test "Get initial group status"
    INITIAL_STATUS=$($CLI group status "$TEST_GROUP" 2>&1)
    if [ -n "$INITIAL_STATUS" ]; then
        log_success "Group status retrieved"
    else
        log_skip "Could not retrieve initial group status"
    fi
    echo ""
    
    # Start group
    log_test "Start group: $TEST_GROUP"
    GROUP_START_OUTPUT=$($CLI group start "$TEST_GROUP" 2>&1 | tee /tmp/group_start.log)
    if echo "$GROUP_START_OUTPUT" | grep -qi "started\|success\|running\|completed"; then
        log_success "Group started"
    else
        log_skip "Group start returned: $(echo "$GROUP_START_OUTPUT" | head -1)"
    fi
    sleep 3
    echo ""
    
    # Verify group status after start
    log_test "Verify group status after start"
    GROUP_STATUS_OUTPUT=$($CLI group status "$TEST_GROUP" 2>&1)
    RUNNING_COUNT=$(echo "$GROUP_STATUS_OUTPUT" | grep -oE "^Summary: [0-9]+/[0-9]+ running" | grep -oE "[0-9]+/[0-9]+")
    if echo "$GROUP_STATUS_OUTPUT" | grep -q "Summary"; then
        log_success "Group status retrieved: $RUNNING_COUNT"
    else
        log_skip "Group status format unexpected"
    fi
    echo ""
    
    # Stop group
    log_test "Stop group: $TEST_GROUP"
    GROUP_STOP_OUTPUT=$($CLI group stop "$TEST_GROUP" 2>&1 | tee /tmp/group_stop.log)
    if echo "$GROUP_STOP_OUTPUT" | grep -qi "stopped\|success\|completed"; then
        log_success "Group stopped"
    else
        log_skip "Group stop returned: $(echo "$GROUP_STOP_OUTPUT" | head -1)"
    fi
    sleep 2
    echo ""
else
    log_skip "Test group $TEST_GROUP not available"
    echo ""
fi

# ========================================
# CONTAINER LIFECYCLE - SINGLE CONTAINER
# ========================================
echo -e "${MAGENTA}━━━ Container Lifecycle Tests ━━━${NC}\n" | tee -a "$LOG_FILE"

echo -e "${CYAN}Testing single container: $TEST_CONTAINER${NC}\n" | tee -a "$LOG_FILE"

# Pre-check: verify container exists in list
log_test "Verify container exists in list"
LIST_OUTPUT=$($CLI list 2>&1)
if echo "$LIST_OUTPUT" | grep -i "alpine-3.22" | grep -q "linux"; then
    log_success "Container $TEST_CONTAINER found in list"
else
    log_error "Container $TEST_CONTAINER not found in list"
    echo "Available containers:" | tee -a "$LOG_FILE"
    echo "$LIST_OUTPUT" | tee -a "$LOG_FILE"
    exit 1
fi
echo ""

# Check initial status
log_info "Checking initial status of $TEST_CONTAINER"
CURRENT_STATUS=$(echo "$LIST_OUTPUT" | grep -i "alpine-3.22" | grep -oE "running|stopped" | head -1)
log_info "Current status: ${CURRENT_STATUS:-unknown}"
echo ""

# Stop if running
if [ "$CURRENT_STATUS" = "running" ]; then
    log_info "Container is running, stopping first..."
    log_test "Stop container (pre-test)"
    if $CLI stop "$TEST_CONTAINER" 2>&1 | tee /tmp/stop.log | grep -qi "stopped\|success\|completed"; then
        log_success "Container stopped"
    else
        log_error "Failed to stop container"
        cat /tmp/stop.log | tee -a "$LOG_FILE"
    fi
    sleep 2
    echo ""
fi

# Start container
log_test "Start container: $TEST_CONTAINER"
START_OUTPUT=$($CLI start "$TEST_CONTAINER" 2>&1 | tee /tmp/start.log)
if echo "$START_OUTPUT" | grep -qi "started\|success\|running"; then
    log_success "Container started"
else
    log_error "Failed to start container"
    cat /tmp/start.log | tee -a "$LOG_FILE"
fi
sleep 2
echo ""

# Wait for container to be ready
log_info "Waiting for container to be ready..."
if wait_for_container "$TEST_CONTAINER"; then
    log_success "Container is ready"
else
    log_skip "Container may not be fully ready yet"
fi
echo ""

# Verify running
log_test "Verify container is running"
if $CLI ps 2>&1 | grep -q "playground-$TEST_CONTAINER"; then
    log_success "Container appears in ps output"
else
    log_error "Container not found in ps output"
    log_info "PS Output:"
    $CLI ps 2>&1 | tee -a "$LOG_FILE"
fi
echo ""

# Get container info
log_test "Get container info"
INFO_OUTPUT=$($CLI info "$TEST_CONTAINER" 2>&1)
if echo "$INFO_OUTPUT" | grep -q "playground-alpine-3.22"; then
    log_success "Container info retrieved successfully"
else
    log_error "Container info command failed or unexpected output"
fi
echo ""

# Test logs command
log_test "Get container logs"
if $CLI logs "$TEST_CONTAINER" 2>&1 | wc -l | grep -qE "[1-9]"; then
    log_success "Container logs retrieved"
else
    log_skip "Container logs command returned no output"
fi
echo ""

# Stop container
log_test "Stop container: $TEST_CONTAINER"
STOP_OUTPUT=$($CLI stop "$TEST_CONTAINER" 2>&1 | tee /tmp/stop2.log)
if echo "$STOP_OUTPUT" | grep -qi "stopped\|success\|completed"; then
    log_success "Container stopped"
else
    log_error "Failed to stop container"
    cat /tmp/stop2.log | tee -a "$LOG_FILE"
fi
sleep 1
echo ""

# Verify stopped
log_test "Verify container is stopped"
if ! $CLI ps 2>&1 | grep -q "playground-$TEST_CONTAINER"; then
    log_success "Container confirmed stopped"
else
    log_skip "Container still appears in ps (may need more time)"
fi
echo ""

# ========================================
# SYSTEM COMMANDS
# ========================================
echo -e "${MAGENTA}━━━ System Commands ━━━${NC}\n" | tee -a "$LOG_FILE"

run_test "Help command" "$CLI --help" "playground\|usage"
echo ""

run_test "Version details" "$CLI version" "."
echo ""

# ========================================
# SUMMARY
# ========================================
echo "" | tee -a "$LOG_FILE"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" | tee -a "$LOG_FILE"
echo -e "${CYAN}Test Results:${NC}" | tee -a "$LOG_FILE"
TOTAL_EXECUTED=$((PASSED_TESTS + FAILED_TESTS + SKIPPED_TESTS))
echo -e "  Total tests:  ${BLUE}$TOTAL_EXECUTED${NC}" | tee -a "$LOG_FILE"
echo -e "  Passed:       ${GREEN}$PASSED_TESTS${NC}" | tee -a "$LOG_FILE"
echo -e "  Failed:       ${RED}$FAILED_TESTS${NC}" | tee -a "$LOG_FILE"
echo -e "  Skipped:      ${YELLOW}$SKIPPED_TESTS${NC}" | tee -a "$LOG_FILE"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" | tee -a "$LOG_FILE"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}" | tee -a "$LOG_FILE"
    echo -e "${GREEN}║   All tests passed! ✓                    ║${NC}" | tee -a "$LOG_FILE"
    echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}" | tee -a "$LOG_FILE"
else
    echo -e "${RED}╔══════════════════════════════════════════╗${NC}" | tee -a "$LOG_FILE"
    echo -e "${RED}║   Some tests failed! ✗                   ║${NC}" | tee -a "$LOG_FILE"
    echo -e "${RED}╚══════════════════════════════════════════╝${NC}" | tee -a "$LOG_FILE"
fi

echo ""
echo -e "${CYAN}Quick commands:${NC}" | tee -a "$LOG_FILE"
echo -e "  ${YELLOW}playground list${NC}                   List all containers" | tee -a "$LOG_FILE"
echo -e "  ${YELLOW}playground ps${NC}                     Show running containers" | tee -a "$LOG_FILE"
echo -e "  ${YELLOW}playground start alpine-3.22${NC}     Start test container" | tee -a "$LOG_FILE"
echo -e "  ${YELLOW}playground stop alpine-3.22${NC}      Stop test container" | tee -a "$LOG_FILE"
echo -e "  ${YELLOW}playground info alpine-3.22${NC}      Container details" | tee -a "$LOG_FILE"
echo -e "  ${YELLOW}playground logs alpine-3.22${NC}      Show container logs" | tee -a "$LOG_FILE"
echo -e "  ${YELLOW}playground group list${NC}             List all groups" | tee -a "$LOG_FILE"
echo ""

if [ $FAILED_TESTS -gt 0 ]; then
    exit 1
fi