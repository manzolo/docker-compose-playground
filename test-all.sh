#!/bin/bash

# Script per testare start/stop di tutti i container del playground
# Generated on: $(date)

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Timing configuration
HEALTH_CHECK_TIMEOUT=30  # Timeout massimo per health check
HEALTH_CHECK_INTERVAL=2  # Intervallo tra i check

# Array per tenere traccia dei risultati
declare -a SUCCESS_CONTAINERS
declare -a FAILED_CONTAINERS
declare -a STOP_FAILED_CONTAINERS

echo -e "${BLUE}🐳 Docker Playground Test Script${NC}"
echo -e "${BLUE}================================${NC}"
echo "Log file: $LOG_FILE"
echo "Summary: $SUMMARY_FILE"
echo

# Funzione per loggare
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Funzione per verificare se un container è healthy
check_container_health() {
    local container_name="playground-$1"
    local timeout=$HEALTH_CHECK_TIMEOUT
    local elapsed=0
    
    log "Health check per container: $container_name"
    
    while [ $elapsed -lt $timeout ]; do
        # Metodo 1: Controlla stato Docker direttamente
        local container_status
        container_status=$(docker inspect "$container_name" --format='{{.State.Status}}' 2>/dev/null)
        
        if [ "$container_status" != "running" ]; then
            log "Container non in running state: $container_status"
            return 1
        fi
        
        # Metodo 2: Controlla health status se definito
        local health_status
        health_status=$(docker inspect "$container_name" --format='{{.State.Health.Status}}' 2>/dev/null)
        
        if [ "$health_status" == "healthy" ]; then
            log "Container healthy: $container_name"
            return 0
        elif [ "$health_status" == "unhealthy" ]; then
            log "Container unhealthy: $container_name"
            return 1
        fi
        
        # Metodo 3: Controlla se il processo principale è attivo
        local pid
        pid=$(docker inspect "$container_name" --format='{{.State.Pid}}' 2>/dev/null)
        
        if [ -n "$pid" ] && [ "$pid" -gt 0 ]; then
            # Metodo 4: Prova a connettersi ai porti esposti (se presenti)
            local ports
            ports=$(docker inspect "$container_name" --format='{{range $p, $conf := .NetworkSettings.Ports}}{{$p}} {{end}}' 2>/dev/null)
            
            if [ -n "$ports" ]; then
                local host_port
                host_port=$(docker port "$container_name" 2>/dev/null | head -1 | cut -d':' -f2)
                
                if [ -n "$host_port" ]; then
                    # Prova connessione TCP basic
                    if timeout 1 bash -c "echo > /dev/tcp/localhost/$host_port" 2>/dev/null; then
                        log "Porta responsive: $host_port"
                        return 0
                    fi
                fi
            else
                # Se non ci sono porte, considera running come sufficiente
                log "Container running senza porte esposte: $container_name"
                return 0
            fi
        fi
        
        echo -ne "  ${YELLOW}⏳ Health check... $(($timeout - $elapsed))s${NC}\r"
        sleep $HEALTH_CHECK_INTERVAL
        elapsed=$((elapsed + HEALTH_CHECK_INTERVAL))
    done
    
    echo -ne "                                   \r"
    log "Health check timeout per: $container_name"
    return 1
}

# Funzione per verificare se il container risponde
check_container_response() {
    local container=$1
    local container_name="playground-$container"
    
    log "Verifica risposta container: $container_name"
    
    # Metodo alternativo: usa docker exec per comandi basic
    if docker exec "$container_name" echo "test" >/dev/null 2>&1; then
        log "Container responsive via docker exec: $container_name"
        return 0
    fi
    
    # Metodo fallback: controlla logs per errori evidenti
    local logs
    logs=$(docker logs "$container_name" 2>&1 | tail -5)
    
    if echo "$logs" | grep -q -i "error\|failed\|exception\|panic"; then
        log "Errori nei logs container: $container_name"
        return 1
    fi
    
    # Ultima risorsa: container running da almeno 5 secondi
    local start_time
    start_time=$(docker inspect "$container_name" --format='{{.State.StartedAt}}' 2>/dev/null)
    
    if [ -n "$start_time" ]; then
        local start_epoch
        start_epoch=$(date -d "$start_time" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "${start_time:0:19}" +%s 2>/dev/null)
        local current_epoch
        current_epoch=$(date +%s)
        
        if [ -n "$start_epoch" ] && [ $((current_epoch - start_epoch)) -ge 5 ]; then
            log "Container running stabilmente: $container_name"
            return 0
        fi
    fi
    
    return 1
}

# Funzione per ottenere la lista dei container dal config
get_containers_list() {
    log "Recupero lista container dal config..."
    
    # Metodo 1: usa playground list --json se disponibile
    if command -v python3 >/dev/null 2>&1 && ./playground list --json >/dev/null 2>&1; then
        ./playground list --json 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    for container in data:
        if isinstance(container, dict) and 'name' in container:
            print(container['name'])
except Exception as e:
    pass
" 2>/dev/null
        return
    fi
    
    # Metodo 2: usa playground list normale
    if ./playground list >/dev/null 2>&1; then
        ./playground list 2>/dev/null | awk -F '[│┃]' '
        {
            name = $2
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", name)
            if (name ~ /^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]$/ && name != "Name") {
                print name
            }
        }
        ' | sort -u | head -n 138
        return
    fi
    
    # Metodo 3: cerca direttamente nei file YAML
    local config_files=("config.yml")
    if [ -d "config.d" ]; then
        config_files+=($(find config.d -name "*.yml" -type f 2>/dev/null))
    fi
    if [ -d "custom.d" ]; then
        config_files+=($(find custom.d -name "*.yml" -type f 2>/dev/null))
    fi
    
    for config_file in "${config_files[@]}"; do
        if [ -f "$config_file" ]; then
            awk '
                /^[[:space:]]*[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]:[[:space:]]*$/ {
                    container_name = $1
                    sub(/:$/, "", container_name)
                    if (container_name != "images" && container_name != "group") {
                        print container_name
                    }
                }
            ' "$config_file" 2>/dev/null
        fi
    done | sort -u
}

# Funzione per verificare se un container esiste nella configurazione
container_exists() {
    local container=$1
    log "Verifica esistenza container $container:"
    ./playground list 2>/dev/null | awk -F '[│┃]' '
    {
        name = $2
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", name)
        if (name == "'"$container"'") {
            found=1
            exit 0
        }
    }
    END {
        if (found) exit 0
        else exit 1
    }
    '
}

# Funzione per verificare se un container è in esecuzione (basic)
is_container_running() {
    local container=$1
    docker ps --filter "name=playground-$container" --format "table {{.Names}}" | grep -q "playground-$container"
}

# Funzione per testare un container
test_container() {
    local container=$1
    local index=$2
    local total=$3
    
    echo -e "\n${BLUE}[$index/$total] Test container: $container${NC}"
    log "Testing container: $container"
    
    # Verifica se il container esiste nella configurazione
    if ! container_exists "$container"; then
        echo -e "${YELLOW}⚠  Container non trovato nella configurazione, skipping${NC}"
        log "Container $container non trovato nella configurazione"
        ((SKIPPED++))
        return 1
    fi
    
    # Pulizia preliminare: ferma container se già in esecuzione
    if is_container_running "$container"; then
        echo -e "${YELLOW}  🔄 Container già in esecuzione, fermo preliminare...${NC}"
        ./playground stop "$container" >/dev/null 2>&1 || true
        sleep 3
    fi
    
    # Cleanup eventuali container zombie
    docker rm -f "playground-$container" >/dev/null 2>&1 || true
    
    # START TEST
    echo -e "  ${YELLOW}▶  Avvio container...${NC}"
    log "Starting container: $container"
    
    local start_output
    start_output=$(./playground start "$container" 2>&1)
    local start_exit_code=$?
    
    echo "$start_output" | tee -a "$LOG_FILE"
    
    # Verifica avanzata se lo start è riuscito
    if [ $start_exit_code -eq 0 ]; then
        echo -e "  ${YELLOW}🔍 Verifica stato container...${NC}"
        
        # Attendi breve inizializzazione
        sleep 2
        
        # Test avanzato con health check
        if check_container_health "$container" && check_container_response "$container"; then
            echo -e "  ${GREEN}✅ START SUCCESS: $container (health check passato)${NC}"
            log "START SUCCESS: $container - health check passato"
            ((START_SUCCESS++))
            SUCCESS_CONTAINERS+=("$container")
            
            # STOP TEST
            echo -e "  ${YELLOW}⏹  Arresto container...${NC}"
            log "Stopping container: $container"
            
            local stop_output
            stop_output=$(./playground stop "$container" 2>&1)
            local stop_exit_code=$?
            
            echo "$stop_output" | tee -a "$LOG_FILE"
            
            # Verifica stop
            sleep 2
            if [ $stop_exit_code -eq 0 ] && ! is_container_running "$container"; then
                echo -e "  ${GREEN}✅ STOP SUCCESS: $container${NC}"
                log "STOP SUCCESS: $container"
                ((STOP_SUCCESS++))
            else
                echo -e "  ${RED}❌ STOP FAILED: $container${NC}"
                log "STOP FAILED: $container - exit code: $stop_exit_code"
                ((STOP_FAILED++))
                STOP_FAILED_CONTAINERS+=("$container")
                
                # Force cleanup
                docker rm -f "playground-$container" >/dev/null 2>&1 || true
            fi
            
        else
            echo -e "  ${RED}❌ START FAILED: $container (health check fallito)${NC}"
            log "START FAILED: $container - health check fallito"
            ((START_FAILED++))
            FAILED_CONTAINERS+=("$container")
            
            # Log diagnostici
            echo -e "  ${YELLOW}📋 Logs container:${NC}"
            docker logs "playground-$container" 2>&1 | tail -10 | tee -a "$LOG_FILE"
        fi
    else
        echo -e "  ${RED}❌ START FAILED: $container (comando fallito)${NC}"
        log "START FAILED: $container - exit code: $start_exit_code"
        ((START_FAILED++))
        FAILED_CONTAINERS+=("$container")
    fi
    
    # Pulizia finale
    docker rm -f "playground-$container" >/dev/null 2>&1 || true
}

# Funzione per generare report
generate_report() {
    echo -e "\n${BLUE}📊 REPORT FINALE${NC}"
    echo -e "${BLUE}================${NC}"
    
    local report="DOCKER PLAYGROUND TEST REPORT
Generated: $(date)
Total containers processed: $TOTAL_CONTAINERS
Start success: $START_SUCCESS
Start failed: $START_FAILED
Stop success: $STOP_SUCCESS
Stop failed: $STOP_FAILED
Skipped: $SKIPPED

HEALTH CHECK CONFIG:
Timeout: ${HEALTH_CHECK_TIMEOUT}s
Interval: ${HEALTH_CHECK_INTERVAL}s

SUCCESSFUL CONTAINERS (${#SUCCESS_CONTAINERS[@]}):
$(if [ ${#SUCCESS_CONTAINERS[@]} -gt 0 ]; then printf '  - %s\n' "${SUCCESS_CONTAINERS[@]}"; else echo "  None"; fi)

FAILED TO START (${#FAILED_CONTAINERS[@]}):
$(if [ ${#FAILED_CONTAINERS[@]} -gt 0 ]; then printf '  - %s\n' "${FAILED_CONTAINERS[@]}"; else echo "  None"; fi)

FAILED TO STOP (${#STOP_FAILED_CONTAINERS[@]}):
$(if [ ${#STOP_FAILED_CONTAINERS[@]} -gt 0 ]; then printf '  - %s\n' "${STOP_FAILED_CONTAINERS[@]}"; else echo "  None"; fi)
"
    
    echo "$report" | tee "$SUMMARY_FILE"
    echo -e "\n${GREEN}📄 Report salvato in: $SUMMARY_FILE${NC}"
    echo -e "${GREEN}📋 Log completo in: $LOG_FILE${NC}"
}

# Main execution
main() {
    log "Inizio test Docker Playground"
    
    if [ ! -f "./playground" ] && [ ! -f "./playground.py" ]; then
        echo -e "${RED}❌ Errore: file playground non trovato${NC}"
        echo "Assicurati di eseguire lo script dalla directory corretta"
        exit 1
    fi
    
    if [ -f "./playground" ] && [ ! -x "./playground" ]; then
        chmod +x ./playground
    fi
    
    echo -e "${YELLOW}Recupero lista container...${NC}"
    mapfile -t CONTAINERS < <(get_containers_list)
    
    if [ ${#CONTAINERS[@]} -eq 0 ]; then
        echo -e "${RED}❌ Nessun container trovato nella configurazione${NC}"
        echo "Verifica che:"
        echo "1. Il file config.yml esista"
        echo "2. Il comando './playground list' funzioni"
        exit 1
    fi
    
    TOTAL_CONTAINERS=${#CONTAINERS[@]}
    echo -e "${GREEN}Trovati $TOTAL_CONTAINERS container${NC}"
    echo -e "${YELLOW}Container da testare:${NC}"
    printf '  - %s\n' "${CONTAINERS[@]}"
    echo
    
    local index=1
    for container in "${CONTAINERS[@]}"; do
        if [[ -z "$container" || "$container" =~ ^[[:space:]]+$ || "$container" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2} ]]; then
            log "Saltato container non valido: $container"
            ((SKIPPED++))
            continue
        fi
        
        test_container "$container" "$index" "$TOTAL_CONTAINERS"
        ((index++))
    done
    
    generate_report
    
    if [ $START_FAILED -eq 0 ] && [ $STOP_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}🎉 TUTTI I TEST PASSATI!${NC}"
        exit 0
    else
        echo -e "\n${YELLOW}⚠  ALCUNI TEST FALLITI${NC}"
        exit 1
    fi
}

# Gestione Ctrl+C
trap 'echo -e "\n${RED}⏹  Test interrotto dall utente${NC}"; generate_report; exit 1' INT

# Esegui main
main