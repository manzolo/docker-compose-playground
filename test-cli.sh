#!/bin/bash
#############################################
# Docker Playground CLI Test Suite
# Tests for CLI functionality including groups
#############################################

#set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

CLI="./playground"
TEST_CONTAINER="alpine-3.22"  # Should exist in config
TEST_GROUP="MySQL-Stack"      # Should exist in config

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

log_test() {
    echo -e "${BLUE}[TEST $((TOTAL_TESTS + 1))]${NC} $*"
    ((TOTAL_TESTS++))
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
    ((PASSED_TESTS++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $*"
    ((FAILED_TESTS++))
}

log_skip() {
    echo -e "${YELLOW}[⊘]${NC} $*"
}

run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_pattern="$3"
    
    log_test "$test_name"
    
    if OUTPUT=$(eval "$test_command" 2>&1); then
        if [ -n "$expected_pattern" ]; then
            if echo "$OUTPUT" | grep -q "$expected_pattern"; then
                log_success "$test_name passed"
                return 0
            else
                log_error "$test_name failed - pattern not found"
                return 1
            fi
        else
            log_success "$test_name passed"
            return 0
        fi
    else
        log_error "$test_name failed - command error"
        return 1
    fi
}

# Banner
cat << 'EOF'
╔══════════════════════════════════════════╗
║   🐳  Docker Playground CLI              ║
║   Test Suite v2.0                        ║
╚══════════════════════════════════════════╝

EOF

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI="${SCRIPT_DIR}/playground"

# Verifica che CLI sia eseguibile
if [ ! -x "$CLI" ]; then
    if [ -f "$CLI" ]; then
        echo -e "${YELLOW}⚠ Making CLI executable...${NC}"
        chmod +x "$CLI"
    else
        echo -e "${RED}❌ CLI not found at $CLI${NC}"
        exit 1
    fi
fi

echo -e "${CYAN}Running CLI tests...${NC}\n"

# ========================================
# BASIC COMMANDS TESTS
# ========================================
echo -e "${MAGENTA}━━━ Basic Commands ━━━${NC}\n"

run_test "Version command" "$CLI version" "Version"
echo ""

run_test "List command" "$CLI list" "Total:"
echo ""

run_test "List with category filter" "$CLI list --category linux" ""
echo ""

run_test "List with status filter" "$CLI list --status stopped" ""
echo ""

run_test "JSON output" "$CLI list --json" '\['
echo ""

# Test PS command - should work with or without containers
log_test "PS command"
if OUTPUT=$($CLI ps 2>&1); then
    if echo "$OUTPUT" | grep -q "Playground Containers\|No playground containers"; then
        log_success "PS command passed"
    else
        log_error "PS command failed - unexpected output"
    fi
else
    log_error "PS command failed - command error"
fi
echo ""

run_test "Categories command" "$CLI categories" "Categories"
echo ""

run_test "Help command" "$CLI --help" "playground"
echo ""

# ========================================
# GROUP COMMANDS TESTS
# ========================================
echo -e "${MAGENTA}━━━ Group Commands ━━━${NC}\n"

run_test "Group list command" "$CLI group list" "Groups"
echo ""

run_test "Group list JSON" "$CLI group list --json" '"description"'
echo ""

if $CLI group list 2>&1 | grep -q "$TEST_GROUP"; then
    run_test "Group status command" "$CLI group status $TEST_GROUP" "Summary"
    echo ""
else
    log_skip "No test group found for status test"
    echo ""
fi

# ========================================
# CONTAINER LIFECYCLE TESTS
# ========================================
echo -e "${YELLOW}━━━ Container Lifecycle Tests ━━━${NC}"
echo -e "${YELLOW}(These tests require confirmation)${NC}\n"

read -p "Run container lifecycle tests? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    
    # Check if test container exists in config
    if ! $CLI list 2>&1 | grep -q "$TEST_CONTAINER"; then
        log_error "Test container '$TEST_CONTAINER' not found in config"
        echo -e "${YELLOW}Available containers:${NC}"
        $CLI list
        exit 1
    fi
    
    # Start container
    log_test "Starting container: $TEST_CONTAINER"
    if $CLI start "$TEST_CONTAINER" 2>&1 | tee /tmp/start_output.txt | grep -q "started successfully"; then
        log_success "Container started"
        sleep 2
        
        # Info command
        run_test "Info command" "$CLI info $TEST_CONTAINER" "Status"
        echo ""
        
        # Logs command
        run_test "Logs command" "$CLI logs $TEST_CONTAINER --tail 5" ""
        echo ""
        
        # Check if running
        run_test "Container appears in ps" "$CLI ps" "$TEST_CONTAINER"
        echo ""
        
        # Restart container
        log_test "Restarting container"
        if $CLI restart "$TEST_CONTAINER" 2>&1 | grep -q "restarted"; then
            log_success "Container restarted"
        else
            log_error "Failed to restart container"
        fi
        echo ""
        sleep 1
        
        # Stop container
        log_test "Stopping container"
        if $CLI stop "$TEST_CONTAINER" 2>&1 | grep -q "stopped"; then
            log_success "Container stopped"
        else
            log_error "Failed to stop container"
        fi
        echo ""
        
    else
        log_error "Failed to start container"
        cat /tmp/start_output.txt
        echo ""
    fi
fi

# ========================================
# GROUP LIFECYCLE TESTS
# ========================================
echo -e "${YELLOW}━━━ Group Lifecycle Tests ━━━${NC}"
echo -e "${YELLOW}(These tests start/stop multiple containers)${NC}\n"

read -p "Run group lifecycle tests? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    
    # Check if test group exists
    if ! $CLI group list 2>&1 | grep -q "$TEST_GROUP"; then
        log_error "Test group '$TEST_GROUP' not found"
        echo -e "${YELLOW}Available groups:${NC}"
        $CLI group list
    else
        # Get group status before
        echo -e "${CYAN}Initial group status:${NC}"
        $CLI group status "$TEST_GROUP"
        echo ""
        
        # Start group
        log_test "Starting group: $TEST_GROUP"
        if $CLI group start "$TEST_GROUP" 2>&1 | tee /tmp/group_start.txt | grep -q "Successfully completed"; then
            log_success "Group started"
            sleep 2
            
            # Check group status
            echo -e "\n${CYAN}Group status after start:${NC}"
            $CLI group status "$TEST_GROUP"
            echo ""
            
            run_test "All containers running" "$CLI group status $TEST_GROUP" "All containers are running"
            echo ""
            
            # Stop group
            log_test "Stopping group: $TEST_GROUP"
            if $CLI group stop "$TEST_GROUP" 2>&1 | grep -q "Successfully completed"; then
                log_success "Group stopped"
            else
                log_error "Failed to stop group"
                cat /tmp/group_stop.txt 2>/dev/null
            fi
            echo ""
            
        else
            log_error "Failed to start group"
            cat /tmp/group_start.txt
            echo ""
        fi
    fi
fi

# ========================================
# SYSTEM COMMANDS TESTS
# ========================================
echo -e "${MAGENTA}━━━ System Commands ━━━${NC}\n"

run_test "Stop-all without containers" "$CLI stop-all --yes" ""
echo ""

run_test "Cleanup without containers" "$CLI cleanup --yes" ""
echo ""

# ========================================
# SUMMARY
# ========================================
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Test Results:${NC}"
echo -e "  Total tests:  ${BLUE}$TOTAL_TESTS${NC}"
echo -e "  Passed:       ${GREEN}$PASSED_TESTS${NC}"
echo -e "  Failed:       ${RED}$FAILED_TESTS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   All tests passed! ✓                   ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}CLI is working correctly!${NC}"
else
    echo -e "${RED}╔══════════════════════════════════════════╗${NC}"
    echo -e "${RED}║   Some tests failed! ✗                  ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════╝${NC}"
    echo ""
    exit 1
fi

echo ""
echo -e "${CYAN}Try these commands:${NC}"
echo -e "  ${YELLOW}$CLI list${NC}                    - List all containers"
echo -e "  ${YELLOW}$CLI ps${NC}                      - Show running containers"
echo -e "  ${YELLOW}$CLI start <container>${NC}      - Start a container"
echo -e "  ${YELLOW}$CLI group list${NC}              - List all groups"
echo -e "  ${YELLOW}$CLI group start <group>${NC}    - Start a group"
echo -e "  ${YELLOW}$CLI group status <group>${NC}   - Check group status"
echo ""