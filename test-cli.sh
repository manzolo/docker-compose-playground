#!/bin/bash
#############################################
# Docker Playground CLI Test Suite
# Quick tests for CLI functionality
#############################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

CLI="./playground"
TEST_CONTAINER="alpine-3.22"  # Should exist in config

log_test() {
    echo -e "${BLUE}[TEST]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
}

log_error() {
    echo -e "${RED}[✗]${NC} $*"
    exit 1
}

# Banner
cat << 'EOF'
╔══════════════════════════════════════════╗
║   🐳  Docker Playground CLI              ║
║   Test Suite                             ║
╚══════════════════════════════════════════╝

EOF

# Verifica che CLI esista
if [ ! -f "$CLI" ]; then
    log_error "CLI not found at $CLI"
fi

echo -e "${CYAN}Running CLI tests...${NC}\n"

# Test 1: Version
log_test "Testing version command..."
$CLI version > /dev/null 2>&1
log_success "Version command works"
echo ""

# Test 2: List
log_test "Testing list command..."
$CLI list > /dev/null 2>&1
log_success "List command works"
echo ""

# Test 3: List with filters
log_test "Testing list with category filter..."
$CLI list --category linux > /dev/null 2>&1
log_success "Category filter works"
echo ""

# Test 4: List JSON output
log_test "Testing JSON output..."
OUTPUT=$($CLI list --json 2>&1)
if echo "$OUTPUT" | grep -q '\['; then
    log_success "JSON output works"
else
    log_error "JSON output failed"
fi
echo ""

# Test 5: PS command
log_test "Testing ps command..."
$CLI ps > /dev/null 2>&1
log_success "PS command works"
echo ""

# Test 6: Categories
log_test "Testing categories command..."
$CLI categories > /dev/null 2>&1
log_success "Categories command works"
echo ""

# Test 7: Help
log_test "Testing help command..."
$CLI --help > /dev/null 2>&1
log_success "Help command works"
echo ""

# Interactive tests (optional)
echo -e "${YELLOW}Interactive tests (requires confirmation):${NC}\n"

read -p "Test container start/stop? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Test 8: Start container
    log_test "Starting test container: $TEST_CONTAINER..."
    if $CLI start "$TEST_CONTAINER" 2>&1 | grep -q "started successfully"; then
        log_success "Container started"
        sleep 2
        
        # Test 9: Info command
        log_test "Testing info command..."
        $CLI info "$TEST_CONTAINER" > /dev/null 2>&1
        log_success "Info command works"
        
        # Test 10: Logs command
        log_test "Testing logs command..."
        $CLI logs "$TEST_CONTAINER" --tail 5 > /dev/null 2>&1
        log_success "Logs command works"
        
        # Test 11: Stop container
        log_test "Stopping test container..."
        if $CLI stop "$TEST_CONTAINER" 2>&1 | grep -q "stopped"; then
            log_success "Container stopped"
        else
            log_error "Failed to stop container"
        fi
    else
        log_error "Failed to start container"
    fi
    echo ""
fi

# Summary
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   All tests passed! ✓                   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}CLI is working correctly!${NC}"
echo ""
echo -e "Try these commands:"
echo -e "  ${YELLOW}$CLI list${NC}"
echo -e "  ${YELLOW}$CLI ps${NC}"
echo -e "  ${YELLOW}$CLI start <container>${NC}"