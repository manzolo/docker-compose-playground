#!/bin/bash
set -uo pipefail

# Script to test start/stop of all playground containers
# Optimized for CI/CD

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Log files
LOG_FILE="playground_test_$(date +%Y%m%d_%H%M%S).log"
SUMMARY_FILE="playground_summary_$(date +%Y%m%d_%H%M%S).txt"

# Container counters
TOTAL_CONTAINERS=0
START_SUCCESS=0
START_FAILED=0
STOP_SUCCESS=0
STOP_FAILED=0
SKIPPED=0

# Group counters
TOTAL_GROUPS=0
GROUP_START_SUCCESS=0
GROUP_START_FAILED=0
GROUP_STOP_SUCCESS=0
GROUP_STOP_FAILED=0

HEALTH_CHECK_TIMEOUT=30
HEALTH_CHECK_INTERVAL=2

# Initialize arrays explicitly
declare -a SUCCESS_CONTAINERS=()
declare -a FAILED_CONTAINERS=()
declare -a STOP_FAILED_CONTAINERS=()
declare -a SUCCESS_GROUPS=()
declare -a FAILED_GROUPS=()
declare -a STOP_FAILED_GROUPS=()

# Start time for duration calculation
START_TIME=$(date +%s)

# Banner
cat << 'EOF'
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║        🐳  DOCKER PLAYGROUND COMPREHENSIVE TEST SUITE        ║
║                                                               ║
║        Testing all containers and groups from config         ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF

echo -e "\n${CYAN}📋 Test Configuration${NC}"
echo -e "   Log file:     ${YELLOW}$LOG_FILE${NC}"
echo -e "   Summary:      ${YELLOW}$SUMMARY_FILE${NC}"
echo -e "   Started:      ${YELLOW}$(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to extract containers from YAML files
get_containers_from_yaml() {
    local yaml_file=$1

    if [ ! -f "$yaml_file" ]; then
        return
    fi

    # Extract all image names using grep and awk
    grep -E "^[[:space:]]*[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]:[[:space:]]*$" "$yaml_file" | \
    sed 's/^[[:space:]]*//g' | \
    sed 's/:.*//g' | \
    grep -v -E "^(images|groups|group|settings|image|description|category|volumes|environment|ports|shell|keep_alive_cmd|scripts|motd|network)$" | \
    sort -u
}

# Function to get container list
get_containers_list() {
    log "Retrieving container list from YAML files..."

    local containers=""

    if [ -f "config.yml" ]; then
        log "Found config.yml"
        containers="$(get_containers_from_yaml config.yml)"
    fi

    if [ -d "config.d" ]; then
        for file in config.d/*.yml config.d/*.yaml; do
            if [ -f "$file" ]; then
                log "Found config file: $file"
                containers="$containers"$'\n'"$(get_containers_from_yaml "$file")"
            fi
        done
    fi

    if [ -d "custom.d" ]; then
        for file in custom.d/*.yml custom.d/*.yaml; do
            if [ -f "$file" ]; then
                log "Found config file: $file"
                containers="$containers"$'\n'"$(get_containers_from_yaml "$file")"
            fi
        done
    fi

    echo "$containers" | sort -u | grep -v '^$'
}

# Function to extract groups from YAML files
get_groups_from_yaml() {
    local yaml_file=$1

    if [ ! -f "$yaml_file" ]; then
        return
    fi

    # Extract group name using sed for more reliable parsing
    # Look for "name:" field within "group:" section
    local group_name
    group_name=$(sed -n '/^group:/,/^[a-z]/ {
        s/^[[:space:]]*name:[[:space:]]*"\{0,1\}\([^"]*\)"\{0,1\}.*/\1/p
    }' "$yaml_file" | head -1)

    if [ -n "$group_name" ]; then
        echo "$group_name"
    fi
}

# Function to get the list of containers in a group
get_group_containers() {
    local group_name=$1
    local containers=""

    # Search YAML files for the group and its containers
    for file in config.yml config.d/*.yml config.d/*.yaml custom.d/*.yml custom.d/*.yaml; do
        if [ -f "$file" ]; then
            local file_group
            file_group=$(get_groups_from_yaml "$file")

            if [ "$file_group" = "$group_name" ]; then
                # Extract group containers
                containers=$(awk '/^group:/,/^images:/' "$file" | grep -E "^[[:space:]]*-[[:space:]]+" | sed 's/^[[:space:]]*-[[:space:]]*//g' | tr -d '"')
                break
            fi
        fi
    done

    echo "$containers"
}

# Function to get group list
get_groups_list() {
    log "Retrieving group list from YAML files..."

    local groups=""

    if [ -f "config.yml" ]; then
        log "Found config.yml"
        groups="$(get_groups_from_yaml config.yml)"
    fi

    if [ -d "config.d" ]; then
        for file in config.d/*.yml config.d/*.yaml; do
            if [ -f "$file" ]; then
                local file_groups
                file_groups=$(get_groups_from_yaml "$file")
                if [ -n "$file_groups" ]; then
                    log "Found group in: $file - $file_groups"
                    groups="$groups"$'\n'"$file_groups"
                fi
            fi
        done
    fi

    if [ -d "custom.d" ]; then
        for file in custom.d/*.yml custom.d/*.yaml; do
            if [ -f "$file" ]; then
                local file_groups
                file_groups=$(get_groups_from_yaml "$file")
                if [ -n "$file_groups" ]; then
                    log "Found group in: $file - $file_groups"
                    groups="$groups"$'\n'"$file_groups"
                fi
            fi
        done
    fi

    echo "$groups" | sort -u | grep -v '^$'
}

# Check if a container is running
is_container_running() {
    local container=$1
    docker ps --format "table {{.Names}}" | grep -q "^playground-$container$"
}

# Container health check
check_container_health() {
    local container_name=$1
    local timeout=$HEALTH_CHECK_TIMEOUT
    local elapsed=0

    log "Health check for: $container_name"
    
    while [ $elapsed -lt $timeout ]; do
        local status
        status=$(docker inspect "$container_name" --format='{{.State.Status}}' 2>/dev/null || echo "")
        
        if [ "$status" = "running" ]; then
            log "Container $container_name is running"
            return 0
        elif [ "$status" = "exited" ] || [ "$status" = "dead" ]; then
            log "Container $container_name in status: $status"
            return 1
        fi

        sleep $HEALTH_CHECK_INTERVAL
        ((elapsed += HEALTH_CHECK_INTERVAL))
    done

    log "Health check timeout for: $container_name"
    return 1
}

# Test single container
test_container() {
    local container=$1
    local index=$2
    local total=$3

    echo -e "\n${CYAN}┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│${NC} ${BLUE}[$index/$total]${NC} Testing: ${MAGENTA}$container${NC}"
    echo -e "${CYAN}└─────────────────────────────────────────────────────────┘${NC}"
    log "Testing container: $container"

    local container_name="playground-$container"

    docker rm -f "$container_name" >/dev/null 2>&1 || true
    sleep 1

    echo -e "  ⏳ ${YELLOW}Starting container...${NC}"
    log "Starting: $container"
    
    local start_output
    start_output=$(docker run \
        -d \
        --name "$container_name" \
        --label "playground.managed=true" \
        --network playground-network \
        alpine:3.22 \
        tail -f /dev/null 2>&1) || true
    
    local container_id=$start_output
    echo "$start_output" | tee -a "$LOG_FILE"
    
    if [ -z "$container_id" ] || [[ "$start_output" == "Error response from daemon"* ]]; then
        echo -e "  ❌ ${RED}START FAILED${NC}"
        log "START FAILED: $container"
        ((START_FAILED++))
        FAILED_CONTAINERS+=("$container")
        return 1
    fi

    sleep 2
    if check_container_health "$container_name"; then
        echo -e "  ✅ ${GREEN}START SUCCESS${NC}"
        log "START SUCCESS: $container"
        ((START_SUCCESS++))
        SUCCESS_CONTAINERS+=("$container")

        echo -e "  ⏹️  ${YELLOW}Stopping container...${NC}"
        log "Stopping: $container"
        
        if docker stop "$container_name" >/dev/null 2>&1 && \
           docker rm "$container_name" >/dev/null 2>&1; then
            sleep 1

            if ! is_container_running "$container"; then
                echo -e "  ✅ ${GREEN}STOP SUCCESS${NC}"
                log "STOP SUCCESS: $container"
                ((STOP_SUCCESS++))
            else
                echo -e "  ❌ ${RED}STOP FAILED${NC}"
                log "STOP FAILED: $container"
                ((STOP_FAILED++))
                STOP_FAILED_CONTAINERS+=("$container")
                docker rm -f "$container_name" >/dev/null 2>&1 || true
            fi
        else
            echo -e "  ❌ ${RED}STOP FAILED${NC}"
            log "STOP FAILED: $container"
            ((STOP_FAILED++))
            STOP_FAILED_CONTAINERS+=("$container")
            docker rm -f "$container_name" >/dev/null 2>&1 || true
        fi
    else
        echo -e "  ❌ ${RED}START FAILED (health check timeout)${NC}"
        log "START FAILED: $container - health check failed"
        ((START_FAILED++))
        FAILED_CONTAINERS+=("$container")
        
        docker logs "$container_name" 2>&1 | tail -5 | tee -a "$LOG_FILE"
        docker rm -f "$container_name" >/dev/null 2>&1 || true
    fi
}

# Test complete group
test_group() {
    local group_name=$1
    local index=$2
    local total=$3

    echo -e "\n${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BLUE}[$index/$total]${NC} Testing Group: ${MAGENTA}$group_name${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    log "Testing group: $group_name"

    # Get group containers
    local containers
    containers=$(get_group_containers "$group_name")

    if [ -z "$containers" ]; then
        echo -e "  ⚠️  ${YELLOW}SKIPPED: No containers found in group${NC}"
        log "SKIPPED: No containers in group $group_name"
        return 0
    fi

    local container_array
    mapfile -t container_array <<< "$containers"
    local container_count=${#container_array[@]}

    echo -e "  📦 ${CYAN}Group contains $container_count containers:${NC}"
    for cont in "${container_array[@]}"; do
        echo -e "     • ${YELLOW}$cont${NC}"
    done
    log "Group $group_name has $container_count containers: ${container_array[*]}"

    # Cleanup: remove any existing containers
    for container in "${container_array[@]}"; do
        docker rm -f "playground-$container" >/dev/null 2>&1 || true
    done
    sleep 1

    # Start group using playground CLI
    echo -e "\n  🚀 ${YELLOW}Starting group...${NC}"
    log "Starting group: $group_name"

    local start_success=true
    if ! ./playground group start "$group_name" >> "$LOG_FILE" 2>&1; then
        echo -e "  ❌ ${RED}GROUP START FAILED${NC}"
        log "GROUP START FAILED: $group_name"
        ((GROUP_START_FAILED++))
        FAILED_GROUPS+=("$group_name")

        # Cleanup
        for container in "${container_array[@]}"; do
            docker rm -f "playground-$container" >/dev/null 2>&1 || true
        done
        return 1
    fi

    # Verify all containers are running
    echo -e "  🔍 ${CYAN}Verifying containers...${NC}"
    sleep 3
    local all_running=true
    local verified=0

    for container in "${container_array[@]}"; do
        local container_name="playground-$container"
        if check_container_health "$container_name"; then
            ((verified++))
            echo -e "     ✓ ${GREEN}$container${NC}"
        else
            echo -e "     ✗ ${RED}$container (not running)${NC}"
            log "Container $container in group $group_name not running"
            all_running=false
        fi
    done

    if $all_running && [ $verified -eq $container_count ]; then
        echo -e "\n  ✅ ${GREEN}GROUP START SUCCESS${NC} (${verified}/${container_count} containers)"
        log "GROUP START SUCCESS: $group_name - all $container_count containers running"
        ((GROUP_START_SUCCESS++))
        SUCCESS_GROUPS+=("$group_name")

        # Stop group
        echo -e "\n  ⏹️  ${YELLOW}Stopping group...${NC}"
        log "Stopping group: $group_name"

        if ./playground group stop "$group_name" >> "$LOG_FILE" 2>&1; then
            sleep 2

            # Verify all containers are stopped
            local all_stopped=true
            for container in "${container_array[@]}"; do
                if is_container_running "$container"; then
                    echo -e "     ✗ ${RED}$container (still running)${NC}"
                    log "Container $container in group $group_name still running"
                    all_stopped=false
                else
                    echo -e "     ✓ ${GREEN}$container (stopped)${NC}"
                fi
            done

            if $all_stopped; then
                echo -e "\n  ✅ ${GREEN}GROUP STOP SUCCESS${NC}"
                log "GROUP STOP SUCCESS: $group_name"
                ((GROUP_STOP_SUCCESS++))
            else
                echo -e "\n  ❌ ${RED}GROUP STOP FAILED (some containers still running)${NC}"
                log "GROUP STOP FAILED: $group_name"
                ((GROUP_STOP_FAILED++))
                STOP_FAILED_GROUPS+=("$group_name")

                # Force cleanup
                for container in "${container_array[@]}"; do
                    docker rm -f "playground-$container" >/dev/null 2>&1 || true
                done
            fi
        else
            echo -e "\n  ❌ ${RED}GROUP STOP FAILED${NC}"
            log "GROUP STOP FAILED: $group_name"
            ((GROUP_STOP_FAILED++))
            STOP_FAILED_GROUPS+=("$group_name")

            # Force cleanup
            for container in "${container_array[@]}"; do
                docker rm -f "playground-$container" >/dev/null 2>&1 || true
            done
        fi
    else
        echo -e "\n  ❌ ${RED}GROUP START FAILED${NC} (${verified}/${container_count} containers verified)"
        log "GROUP START FAILED: $group_name - only $verified/$container_count containers running"
        ((GROUP_START_FAILED++))
        FAILED_GROUPS+=("$group_name")

        # Cleanup
        for container in "${container_array[@]}"; do
            docker rm -f "playground-$container" >/dev/null 2>&1 || true
        done
    fi
}

# Generate report
generate_report() {
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))

    echo -e "\n${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                                                               ║${NC}"
    echo -e "${CYAN}║                    📊  FINAL TEST REPORT                     ║${NC}"
    echo -e "${CYAN}║                                                               ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"

    local report="
╔═══════════════════════════════════════════════════════════════╗
║               DOCKER PLAYGROUND TEST REPORT                   ║
╚═══════════════════════════════════════════════════════════════╝

📅 Generated: $(date '+%Y-%m-%d %H:%M:%S')
⏱️  Duration: ${minutes}m ${seconds}s


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 CONTAINER TEST RESULTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Tested:     $TOTAL_CONTAINERS
  ✅ Start Success:  $START_SUCCESS
  ❌ Start Failed:   $START_FAILED
  ✅ Stop Success:   $STOP_SUCCESS
  ❌ Stop Failed:    $STOP_FAILED
  ⚠️  Skipped:       $SKIPPED

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 GROUP TEST RESULTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Tested:     $TOTAL_GROUPS
  ✅ Start Success:  $GROUP_START_SUCCESS
  ❌ Start Failed:   $GROUP_START_FAILED
  ✅ Stop Success:   $GROUP_STOP_SUCCESS
  ❌ Stop Failed:    $GROUP_STOP_FAILED

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 DETAILED RESULTS - CONTAINERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ SUCCESSFUL CONTAINERS (${#SUCCESS_CONTAINERS[@]}):
$(if [ ${#SUCCESS_CONTAINERS[@]} -gt 0 ]; then printf '   • %s\n' "${SUCCESS_CONTAINERS[@]}" | head -20; [ ${#SUCCESS_CONTAINERS[@]} -gt 20 ] && echo "   ... and $((${#SUCCESS_CONTAINERS[@]} - 20)) more"; else echo "   None"; fi)

❌ FAILED TO START (${#FAILED_CONTAINERS[@]}):
$(if [ ${#FAILED_CONTAINERS[@]} -gt 0 ]; then printf '   • %s\n' "${FAILED_CONTAINERS[@]}"; else echo "   None"; fi)

❌ FAILED TO STOP (${#STOP_FAILED_CONTAINERS[@]}):
$(if [ ${#STOP_FAILED_CONTAINERS[@]} -gt 0 ]; then printf '   • %s\n' "${STOP_FAILED_CONTAINERS[@]}"; else echo "   None"; fi)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 DETAILED RESULTS - GROUPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ SUCCESSFUL GROUPS (${#SUCCESS_GROUPS[@]}):
$(if [ ${#SUCCESS_GROUPS[@]} -gt 0 ]; then printf '   • %s\n' "${SUCCESS_GROUPS[@]}"; else echo "   None"; fi)

❌ FAILED TO START (${#FAILED_GROUPS[@]}):
$(if [ ${#FAILED_GROUPS[@]} -gt 0 ]; then printf '   • %s\n' "${FAILED_GROUPS[@]}"; else echo "   None"; fi)

❌ FAILED TO STOP (${#STOP_FAILED_GROUPS[@]}):
$(if [ ${#STOP_FAILED_GROUPS[@]} -gt 0 ]; then printf '   • %s\n' "${STOP_FAILED_GROUPS[@]}"; else echo "   None"; fi)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"

    echo "$report" | tee "$SUMMARY_FILE"
    echo -e "\n${GREEN}Report saved: $SUMMARY_FILE${NC}"
    echo -e "${GREEN}Log saved: $LOG_FILE${NC}"
}

# Main
main() {
    log "Starting Docker Playground tests"

    if ! command -v docker &> /dev/null; then
        echo -e "${RED}ERROR: Docker not found${NC}"
        exit 1
    fi

    docker network create playground-network 2>/dev/null || true
    log "Network playground-network verified/created"

    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}📦 PHASE 1: CONTAINER DISCOVERY${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    echo -e "${YELLOW}⏳ Scanning configuration files...${NC}"
    mapfile -t CONTAINERS < <(get_containers_list)

    if [ ${#CONTAINERS[@]} -eq 0 ]; then
        echo -e "${RED}❌ ERROR: No containers found${NC}"
        echo -e "${YELLOW}Please verify:${NC}"
        echo "   1. Does config.yml exist in root?"
        echo "   2. Does it contain 'images' section?"
        echo "   3. Are there files in config.d/ or custom.d/?"

        echo -e "\n${YELLOW}Files found:${NC}"
        ls -la *.yml 2>/dev/null || echo "  ❌ No config.yml found"
        ls -la config.d/*.yml 2>/dev/null || echo "  ❌ No files in config.d/"
        ls -la custom.d/*.yml 2>/dev/null || echo "  ❌ No files in custom.d/"

        exit 1
    fi

    TOTAL_CONTAINERS=${#CONTAINERS[@]}
    echo -e "${GREEN}✅ Found $TOTAL_CONTAINERS containers${NC}\n"

    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}🔬 PHASE 2: CONTAINER TESTING${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    local index=1
    for container in "${CONTAINERS[@]}"; do
        if [ -z "$container" ] || [[ "$container" =~ ^[[:space:]]*$ ]]; then
            ((SKIPPED++))
            continue
        fi

        test_container "$container" "$index" "$TOTAL_CONTAINERS"
        ((index++))
    done

    # Test groups
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}🎯 PHASE 3: GROUP TESTING${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    echo -e "${YELLOW}⏳ Scanning for groups...${NC}"
    mapfile -t GROUPS < <(get_groups_list)

    TOTAL_GROUPS=${#GROUPS[@]}

    if [ ${#GROUPS[@]} -eq 0 ]; then
        echo -e "${YELLOW}⚠️  No groups found${NC}\n"
    else
        echo -e "${GREEN}✅ Found $TOTAL_GROUPS groups:${NC}"
        for grp in "${GROUPS[@]}"; do
            echo -e "   • ${MAGENTA}$grp${NC}"
        done
        echo

        local group_index=1
        for group in "${GROUPS[@]}"; do
            if [ -z "$group" ] || [[ "$group" =~ ^[[:space:]]*$ ]]; then
                continue
            fi

            test_group "$group" "$group_index" "$TOTAL_GROUPS"
            ((group_index++))
        done
    fi

    generate_report

    # Calculate success rate
    local total_tests=$((TOTAL_CONTAINERS + TOTAL_GROUPS))
    local total_success=$((START_SUCCESS + STOP_SUCCESS + GROUP_START_SUCCESS + GROUP_STOP_SUCCESS))
    local total_failed=$((START_FAILED + STOP_FAILED + GROUP_START_FAILED + GROUP_STOP_FAILED))

    # Check both containers and groups
    if [ $START_FAILED -eq 0 ] && [ $STOP_FAILED -eq 0 ] && [ $GROUP_START_FAILED -eq 0 ] && [ $GROUP_STOP_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║                                                               ║${NC}"
        echo -e "${GREEN}║                  ✅  ALL TESTS PASSED!  ✅                   ║${NC}"
        echo -e "${GREEN}║                                                               ║${NC}"
        echo -e "${GREEN}║           $TOTAL_CONTAINERS containers + $TOTAL_GROUPS groups tested successfully           ║${NC}"
        echo -e "${GREEN}║                                                               ║${NC}"
        echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}\n"
        exit 0
    else
        echo -e "\n${RED}╔═══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║                                                               ║${NC}"
        echo -e "${RED}║                 ❌  SOME TESTS FAILED  ❌                    ║${NC}"
        echo -e "${RED}║                                                               ║${NC}"
        echo -e "${RED}║              Failed: $total_failed | Passed: $total_success                     ║${NC}"
        echo -e "${RED}║                                                               ║${NC}"
        echo -e "${RED}╚═══════════════════════════════════════════════════════════════╝${NC}\n"

        echo -e "${YELLOW}💡 Check the detailed report above or review:${NC}"
        echo -e "   📄 Log file: ${CYAN}$LOG_FILE${NC}"
        echo -e "   📊 Summary:  ${CYAN}$SUMMARY_FILE${NC}\n"
        exit 1
    fi
}

trap 'echo -e "\n${RED}Test interrupted${NC}"; generate_report; exit 1' INT

main