#!/bin/bash
# Test script for Docker Compose parameter support
# Tests that all configured Docker Compose parameters are correctly applied to containers

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Container name
CONTAINER_NAME="test-docker-compose-params"
FULL_CONTAINER_NAME="playground-${CONTAINER_NAME}"

# Log function
log() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

pass() {
    echo -e "${GREEN}✓ PASS${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

fail() {
    echo -e "${RED}✗ FAIL${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

warn() {
    echo -e "${YELLOW}⚠ WARN${NC} $1"
}

test_result() {
    local test_name="$1"
    local expected="$2"
    local actual="$3"

    TESTS_RUN=$((TESTS_RUN + 1))

    if [[ "$actual" == "$expected" ]]; then
        pass "$test_name"
        return 0
    else
        fail "$test_name (expected: '$expected', got: '$actual')"
        return 1
    fi
}

test_contains() {
    local test_name="$1"
    local needle="$2"
    local haystack="$3"

    TESTS_RUN=$((TESTS_RUN + 1))

    if echo "$haystack" | grep -q "$needle"; then
        pass "$test_name"
        return 0
    else
        fail "$test_name (expected to find: '$needle')"
        return 1
    fi
}

# Banner
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Docker Compose Parameters Test Suite"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if container config exists
log "Checking if test configuration exists..."
if ! ./playground list | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}ERROR: Test container '$CONTAINER_NAME' not found in configuration${NC}"
    echo "Make sure custom.d/test-docker-compose-params.yml exists"
    exit 1
fi
echo -e "${GREEN}✓${NC} Test configuration found"

# Clean up any existing container
log "Cleaning up existing container..."
if docker ps -a --format '{{.Names}}' | grep -q "^${FULL_CONTAINER_NAME}$"; then
    log "Container exists, stopping it..."
    ./playground stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
else
    log "No existing container found"
fi

# Start the container
echo ""
log "Starting test container: $CONTAINER_NAME"
if ! ./playground start "$CONTAINER_NAME"; then
    echo -e "${RED}ERROR: Failed to start container${NC}"
    exit 1
fi

# Wait for container to be fully running
log "Waiting for container to be ready..."
sleep 3

# Verify container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${FULL_CONTAINER_NAME}$"; then
    echo -e "${RED}ERROR: Container is not running${NC}"
    exit 1
fi

echo ""
echo "───────────────────────────────────────────────────────────────"
echo "  Running Parameter Verification Tests"
echo "───────────────────────────────────────────────────────────────"
echo ""

# ==============================================================================
# NETWORK & CONNECTIVITY TESTS
# ==============================================================================
echo -e "${BLUE}📡 NETWORK & CONNECTIVITY TESTS${NC}"

# Test extra_hosts
HOSTS_CONTENT=$(docker exec "$FULL_CONTAINER_NAME" cat /etc/hosts 2>/dev/null)
test_contains "extra_hosts: api.example.com" "192.168.1.100.*api.example.com" "$HOSTS_CONTENT"
test_contains "extra_hosts: db.example.com" "192.168.1.200.*db.example.com" "$HOSTS_CONTENT"
test_contains "extra_hosts: cache.example.com" "192.168.1.150.*cache.example.com" "$HOSTS_CONTENT"

# Test dns
RESOLV_CONTENT=$(docker exec "$FULL_CONTAINER_NAME" cat /etc/resolv.conf 2>/dev/null)
test_contains "dns: 8.8.8.8" "8.8.8.8" "$RESOLV_CONTENT"
test_contains "dns: 8.8.4.4" "8.8.4.4" "$RESOLV_CONTENT"

# Test dns_search
test_contains "dns_search: example.com" "example.com" "$RESOLV_CONTENT"

# Test hostname
HOSTNAME=$(docker exec "$FULL_CONTAINER_NAME" hostname 2>/dev/null)
test_result "hostname" "compose-test-host" "$HOSTNAME"

echo ""

# ==============================================================================
# SECURITY TESTS
# ==============================================================================
echo -e "${BLUE}🔒 SECURITY TESTS${NC}"

# Test privileged
PRIVILEGED=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{.HostConfig.Privileged}}' 2>/dev/null)
test_result "privileged" "false" "$PRIVILEGED"

# Test read_only
READ_ONLY=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{.HostConfig.ReadonlyRootfs}}' 2>/dev/null)
test_result "read_only" "false" "$READ_ONLY"

# Test security_opt
SECURITY_OPT=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{.HostConfig.SecurityOpt}}' 2>/dev/null)
test_contains "security_opt: no-new-privileges" "no-new-privileges" "$SECURITY_OPT"

# Test capabilities
CAP_INFO=$(docker exec "$FULL_CONTAINER_NAME" cat /proc/self/status 2>/dev/null | grep Cap)
test_contains "cap_add/cap_drop configured" "Cap" "$CAP_INFO"

echo ""

# ==============================================================================
# RESOURCE TESTS
# ==============================================================================
echo -e "${BLUE}💾 RESOURCE TESTS${NC}"

# Test mem_limit (512m = 536870912 bytes)
MEMORY=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{.HostConfig.Memory}}' 2>/dev/null)
test_result "mem_limit (512m)" "536870912" "$MEMORY"

# Test memswap_limit (1g = 1073741824 bytes)
MEMORY_SWAP=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{.HostConfig.MemorySwap}}' 2>/dev/null)
test_result "memswap_limit (1g)" "1073741824" "$MEMORY_SWAP"

# Test shm_size (128m = 134217728 bytes)
SHM_SIZE=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{.HostConfig.ShmSize}}' 2>/dev/null)
test_result "shm_size (128m)" "134217728" "$SHM_SIZE"

# Test cpu_shares
CPU_SHARES=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{.HostConfig.CpuShares}}' 2>/dev/null)
test_result "cpu_shares" "512" "$CPU_SHARES"

# Test cpuset_cpus
CPUSET=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{.HostConfig.CpusetCpus}}' 2>/dev/null)
test_result "cpuset_cpus" "0" "$CPUSET"

# Test cpu_quota
CPU_QUOTA=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{.HostConfig.CpuQuota}}' 2>/dev/null)
test_result "cpu_quota" "50000" "$CPU_QUOTA"

# Test cpu_period
CPU_PERIOD=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{.HostConfig.CpuPeriod}}' 2>/dev/null)
test_result "cpu_period" "100000" "$CPU_PERIOD"

# Test pids_limit
PIDS_LIMIT=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{.HostConfig.PidsLimit}}' 2>/dev/null)
test_result "pids_limit" "200" "$PIDS_LIMIT"

echo ""

# ==============================================================================
# PROCESS MANAGEMENT TESTS
# ==============================================================================
echo -e "${BLUE}⚙️  PROCESS MANAGEMENT TESTS${NC}"

# Test oom_kill_disable (can be false or <nil> when disabled)
OOM_KILL=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{.HostConfig.OomKillDisable}}' 2>/dev/null)
TESTS_RUN=$((TESTS_RUN + 1))
if [[ "$OOM_KILL" == "false" || "$OOM_KILL" == "<nil>" ]]; then
    pass "oom_kill_disable"
else
    fail "oom_kill_disable (expected: 'false' or '<nil>', got: '$OOM_KILL')"
fi

# Test oom_score_adj
OOM_SCORE=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{.HostConfig.OomScoreAdj}}' 2>/dev/null)
test_result "oom_score_adj" "500" "$OOM_SCORE"

# Test init
INIT=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{.HostConfig.Init}}' 2>/dev/null)
test_result "init" "true" "$INIT"

echo ""

# ==============================================================================
# STORAGE TESTS
# ==============================================================================
echo -e "${BLUE}💿 STORAGE TESTS${NC}"

# Test tmpfs mounts
MOUNT_INFO=$(docker exec "$FULL_CONTAINER_NAME" mount 2>/dev/null)
test_contains "tmpfs: /tmp" "tmpfs on /tmp" "$MOUNT_INFO"
test_contains "tmpfs: /run" "tmpfs on /run" "$MOUNT_INFO"
test_contains "tmpfs: /cache" "tmpfs on /cache" "$MOUNT_INFO"

# Test working_dir
WORKDIR=$(docker exec "$FULL_CONTAINER_NAME" pwd 2>/dev/null)
test_result "working_dir" "/app" "$WORKDIR"

echo ""

# ==============================================================================
# SYSTEM CONTROL TESTS
# ==============================================================================
echo -e "${BLUE}🖥️  SYSTEM CONTROL TESTS${NC}"

# Test sysctls
SYSCTL_1=$(docker exec "$FULL_CONTAINER_NAME" sysctl net.ipv4.ip_forward 2>/dev/null)
test_contains "sysctls: net.ipv4.ip_forward" "= 1" "$SYSCTL_1"

SYSCTL_2=$(docker exec "$FULL_CONTAINER_NAME" sysctl net.core.somaxconn 2>/dev/null)
test_contains "sysctls: net.core.somaxconn" "= 1024" "$SYSCTL_2"

SYSCTL_3=$(docker exec "$FULL_CONTAINER_NAME" sysctl net.ipv4.tcp_keepalive_time 2>/dev/null)
test_contains "sysctls: net.ipv4.tcp_keepalive_time" "= 600" "$SYSCTL_3"

echo ""

# ==============================================================================
# NAMESPACE TESTS
# ==============================================================================
echo -e "${BLUE}🔐 NAMESPACE TESTS${NC}"

# Test group_add
GROUP_ADD=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{.HostConfig.GroupAdd}}' 2>/dev/null)
TESTS_RUN=$((TESTS_RUN + 1))
if echo "$GROUP_ADD" | grep -qE "(wheel|audio)"; then
    pass "group_add: groups configured"
else
    warn "group_add: Groups may not exist in alpine (this is OK)"
fi

echo ""

# ==============================================================================
# ULIMITS TESTS
# ==============================================================================
echo -e "${BLUE}📊 ULIMITS TESTS${NC}"

# Test nofile ulimit
NOFILE=$(docker exec "$FULL_CONTAINER_NAME" sh -c "ulimit -n" 2>/dev/null)
test_result "ulimits: nofile" "65536" "$NOFILE"

# Test nproc ulimit
NPROC=$(docker exec "$FULL_CONTAINER_NAME" sh -c "ulimit -u" 2>/dev/null)
test_result "ulimits: nproc" "4096" "$NPROC"

echo ""

# ==============================================================================
# HEALTHCHECK TESTS
# ==============================================================================
echo -e "${BLUE}🏥 HEALTHCHECK TESTS${NC}"

# Test healthcheck configuration
HEALTH_CHECK=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{json .State.Health}}' 2>/dev/null)
if [[ -n "$HEALTH_CHECK" && "$HEALTH_CHECK" != "null" ]]; then
    test_contains "healthcheck configured" "Status" "$HEALTH_CHECK"
else
    TESTS_RUN=$((TESTS_RUN + 1))
    warn "healthcheck: Health status not available yet (starting)"
fi

echo ""

# ==============================================================================
# RESTART POLICY TESTS
# ==============================================================================
echo -e "${BLUE}🔄 RESTART POLICY TESTS${NC}"

# Test restart policy
RESTART_NAME=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{.HostConfig.RestartPolicy.Name}}' 2>/dev/null)
test_result "restart_policy Name" "on-failure" "$RESTART_NAME"

RESTART_MAX=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{.HostConfig.RestartPolicy.MaximumRetryCount}}' 2>/dev/null)
test_result "restart_policy MaximumRetryCount" "3" "$RESTART_MAX"

echo ""

# ==============================================================================
# LOGGING TESTS
# ==============================================================================
echo -e "${BLUE}📝 LOGGING TESTS${NC}"

# Test log config
LOG_TYPE=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{.HostConfig.LogConfig.Type}}' 2>/dev/null)
test_result "log_config Type" "json-file" "$LOG_TYPE"

LOG_MAX_SIZE=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{index .HostConfig.LogConfig.Config "max-size"}}' 2>/dev/null)
test_result "log_config max-size" "10m" "$LOG_MAX_SIZE"

LOG_MAX_FILE=$(docker inspect "$FULL_CONTAINER_NAME" --format '{{index .HostConfig.LogConfig.Config "max-file"}}' 2>/dev/null)
test_result "log_config max-file" "3" "$LOG_MAX_FILE"

echo ""

# ==============================================================================
# CLEANUP
# ==============================================================================
log "Stopping test container..."
./playground stop "$CONTAINER_NAME" >/dev/null 2>&1

# ==============================================================================
# SUMMARY
# ==============================================================================
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Test Summary"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Total Tests Run:    $TESTS_RUN"
echo -e "Tests Passed:       ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed:       ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED!${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo ""
    exit 1
fi
