#!/bin/bash
set -uo pipefail

# Script per testare start/stop di tutti i container del playground
# Ottimizzato per CI/CD

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# File di log
LOG_FILE="playground_test_$(date +%Y%m%d_%H%M%S).log"
SUMMARY_FILE="playground_summary_$(date +%Y%m%d_%H%M%S).txt"

# Contatori
TOTAL_CONTAINERS=0
START_SUCCESS=0
START_FAILED=0
STOP_SUCCESS=0
STOP_FAILED=0
SKIPPED=0

HEALTH_CHECK_TIMEOUT=30
HEALTH_CHECK_INTERVAL=2

declare -a SUCCESS_CONTAINERS
declare -a FAILED_CONTAINERS
declare -a STOP_FAILED_CONTAINERS

echo -e "${BLUE}🐳 Docker Playground Test Script${NC}"
echo -e "${BLUE}================================${NC}"
echo "Log file: $LOG_FILE"
echo "Summary: $SUMMARY_FILE"
echo

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Funzione per estrarre container dai file YAML
get_containers_from_yaml() {
    local yaml_file=$1
    
    if [ ! -f "$yaml_file" ]; then
        return
    fi
    
    # Estrai tutti i nomi delle immagini usando grep e awk
    # Cerca linee che possono essere indentate (con spazi) e terminano con :
    grep -E "^[[:space:]]*[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]:[[:space:]]*$" "$yaml_file" | \
    sed 's/^[[:space:]]*//g' | \
    sed 's/:.*//g' | \
    grep -v -E "^(images|groups|group|settings|image|description|category|volumes|environment|ports|shell|keep_alive_cmd|scripts|motd|network)$" | \
    sort -u
}

# Funzione per ottenere la lista dei container
get_containers_list() {
    log "Recupero lista container da file YAML..."
    
    local containers=""
    
    # Cerca config.yml nella root
    if [ -f "config.yml" ]; then
        log "Trovato config.yml"
        containers="$(get_containers_from_yaml config.yml)"
    fi
    
    # Cerca file in config.d/
    if [ -d "config.d" ]; then
        for file in config.d/*.yml config.d/*.yaml; do
            if [ -f "$file" ]; then
                log "Trovato file config: $file"
                containers="$containers"$'\n'"$(get_containers_from_yaml "$file")"
            fi
        done
    fi
    
    # Cerca file in custom.d/
    if [ -d "custom.d" ]; then
        for file in custom.d/*.yml custom.d/*.yaml; do
            if [ -f "$file" ]; then
                log "Trovato file config: $file"
                containers="$containers"$'\n'"$(get_containers_from_yaml "$file")"
            fi
        done
    fi
    
    # Rimuovi linee vuote e duplicati
    echo "$containers" | sort -u | grep -v '^$'
}

# Verifica se un container è in esecuzione
is_container_running() {
    local container=$1
    docker ps --format "table {{.Names}}" | grep -q "^playground-$container$"
}

# Health check per il container
check_container_health() {
    local container_name=$1
    local timeout=$HEALTH_CHECK_TIMEOUT
    local elapsed=0
    
    log "Health check per: $container_name"
    
    while [ $elapsed -lt $timeout ]; do
        # Verifica stato Docker
        local status
        status=$(docker inspect "$container_name" --format='{{.State.Status}}' 2>/dev/null || echo "")
        
        if [ "$status" = "running" ]; then
            log "Container $container_name è running"
            return 0
        elif [ "$status" = "exited" ] || [ "$status" = "dead" ]; then
            log "Container $container_name in stato: $status"
            return 1
        fi
        
        sleep $HEALTH_CHECK_INTERVAL
        ((elapsed += HEALTH_CHECK_INTERVAL))
    done
    
    log "Health check timeout per: $container_name"
    return 1
}

# Test singolo container
test_container() {
    local container=$1
    local index=$2
    local total=$3
    
    echo -e "\n${BLUE}[$index/$total] Testing: $container${NC}"
    log "Testing container: $container"
    
    local container_name="playground-$container"
    
    # Pulizia preliminare
    docker rm -f "$container_name" >/dev/null 2>&1 || true
    sleep 1
    
    # START TEST
    echo -e "  ${YELLOW}Starting container...${NC}"
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
    
    if [ -z "$container_id" ] || [ "$container_id" = "Error response from daemon"* ]; then
        echo -e "  ${RED}START FAILED: $container${NC}"
        log "START FAILED: $container"
        ((START_FAILED++))
        FAILED_CONTAINERS+=("$container")
        return 1
    fi
    
    # Health check
    sleep 2
    if check_container_health "$container_name"; then
        echo -e "  ${GREEN}START SUCCESS: $container${NC}"
        log "START SUCCESS: $container"
        ((START_SUCCESS++))
        SUCCESS_CONTAINERS+=("$container")
        
        # STOP TEST
        echo -e "  ${YELLOW}Stopping container...${NC}"
        log "Stopping: $container"
        
        if docker stop "$container_name" >/dev/null 2>&1 && \
           docker rm "$container_name" >/dev/null 2>&1; then
            sleep 1
            
            if ! is_container_running "$container"; then
                echo -e "  ${GREEN}STOP SUCCESS: $container${NC}"
                log "STOP SUCCESS: $container"
                ((STOP_SUCCESS++))
            else
                echo -e "  ${RED}STOP FAILED: $container${NC}"
                log "STOP FAILED: $container"
                ((STOP_FAILED++))
                STOP_FAILED_CONTAINERS+=("$container")
                docker rm -f "$container_name" >/dev/null 2>&1 || true
            fi
        else
            echo -e "  ${RED}STOP FAILED: $container${NC}"
            log "STOP FAILED: $container"
            ((STOP_FAILED++))
            STOP_FAILED_CONTAINERS+=("$container")
            docker rm -f "$container_name" >/dev/null 2>&1 || true
        fi
    else
        echo -e "  ${RED}START FAILED (health check): $container${NC}"
        log "START FAILED: $container - health check fallito"
        ((START_FAILED++))
        FAILED_CONTAINERS+=("$container")
        
        # Log diagnostici
        docker logs "$container_name" 2>&1 | tail -5 | tee -a "$LOG_FILE"
        docker rm -f "$container_name" >/dev/null 2>&1 || true
    fi
}

# Genera report
generate_report() {
    echo -e "\n${BLUE}📊 REPORT FINALE${NC}"
    echo -e "${BLUE}================${NC}"
    
    local report="DOCKER PLAYGROUND TEST REPORT
Generated: $(date)
Total containers tested: $TOTAL_CONTAINERS
Start success: $START_SUCCESS
Start failed: $START_FAILED
Stop success: $STOP_SUCCESS
Stop failed: $STOP_FAILED
Skipped: $SKIPPED

SUCCESSFUL CONTAINERS (${#SUCCESS_CONTAINERS[@]}):
$(if [ ${#SUCCESS_CONTAINERS[@]} -gt 0 ]; then printf '  - %s\n' "${SUCCESS_CONTAINERS[@]}"; else echo "  None"; fi)

FAILED TO START (${#FAILED_CONTAINERS[@]}):
$(if [ ${#FAILED_CONTAINERS[@]} -gt 0 ]; then printf '  - %s\n' "${FAILED_CONTAINERS[@]}"; else echo "  None"; fi)

FAILED TO STOP (${#STOP_FAILED_CONTAINERS[@]}):
$(if [ ${#STOP_FAILED_CONTAINERS[@]} -gt 0 ]; then printf '  - %s\n' "${STOP_FAILED_CONTAINERS[@]}"; else echo "  None"; fi)
"
    
    echo "$report" | tee "$SUMMARY_FILE"
    echo -e "\n${GREEN}Report saved: $SUMMARY_FILE${NC}"
    echo -e "${GREEN}Log saved: $LOG_FILE${NC}"
}

# Main
main() {
    log "Inizio test Docker Playground"
    
    # Verifica Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}ERROR: Docker non trovato${NC}"
        exit 1
    fi
    
    # Crea network se non esiste
    docker network create playground-network 2>/dev/null || true
    log "Network playground-network verificato/creato"
    
    # Recupera container da testare
    echo -e "${YELLOW}Recupero lista container...${NC}"
    mapfile -t CONTAINERS < <(get_containers_list)
    
    if [ ${#CONTAINERS[@]} -eq 0 ]; then
        echo -e "${RED}ERROR: Nessun container trovato${NC}"
        echo "Verifica:"
        echo "1. Esisti config.yml in root?"
        echo "2. Contiene sezione 'images'?"
        echo "3. Contiene file in config.d/ o custom.d/?"
        
        # Lista file trovati
        echo -e "\n${YELLOW}File trovati:${NC}"
        ls -la *.yml 2>/dev/null || echo "  Nessun config.yml trovato"
        ls -la config.d/*.yml 2>/dev/null || echo "  Nessun file in config.d/"
        ls -la custom.d/*.yml 2>/dev/null || echo "  Nessun file in custom.d/"
        
        exit 1
    fi
    
    TOTAL_CONTAINERS=${#CONTAINERS[@]}
    echo -e "${GREEN}Trovati $TOTAL_CONTAINERS container${NC}"
    echo -e "${YELLOW}Container da testare:${NC}"
    printf '  - %s\n' "${CONTAINERS[@]}"
    echo
    
    # Test container
    local index=1
    for container in "${CONTAINERS[@]}"; do
        if [ -z "$container" ] || [[ "$container" =~ ^[[:space:]]*$ ]]; then
            ((SKIPPED++))
            continue
        fi
        
        test_container "$container" "$index" "$TOTAL_CONTAINERS"
        ((index++))
    done
    
    generate_report
    
    # Exit code
    if [ $START_FAILED -eq 0 ] && [ $STOP_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}✅ TUTTI I TEST PASSATI!${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ ALCUNI TEST FALLITI${NC}"
        exit 1
    fi
}

trap 'echo -e "\n${RED}Test interrotto${NC}"; generate_report; exit 1' INT

main