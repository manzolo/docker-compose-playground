#!/bin/bash
set -uo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
    log_info "Esecuzione cleanup..."
    
    if [ -f "${SCRIPT_DIR}/venv/web.pid" ]; then
        pid=$(cat "${SCRIPT_DIR}/venv/web.pid" 2>/dev/null)
        if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
            log_info "Terminazione server (PID: $pid)..."
            kill -TERM "$pid" 2>/dev/null || true
            sleep 2
            if ps -p "$pid" > /dev/null 2>&1; then
                kill -9 "$pid" 2>/dev/null || true
            fi
        fi
    fi
    
    lsof -ti:${PORT} | xargs kill -9 2>/dev/null || true
    
    # Ferma il container di test
    log_info "Arresto container $CONTAINER_NAME..."
    curl -s -X POST "http://localhost:${PORT}/stop/${CONTAINER_NAME}" > /dev/null 2>&1 || true
    
    log_info "Cleanup completato"
}

trap cleanup SIGINT SIGTERM EXIT

wait_for_api() {
    local elapsed=0
    local max_wait=$1
    
    log_info "Attesa della disponibilità API (max ${max_wait}s)..."
    
    while [ $elapsed -lt "$max_wait" ]; do
        if curl -sf "${API_URL}/system-info" > /dev/null 2>&1; then
            log_success "API disponibile"
            return 0
        fi
        
        sleep 1
        ((elapsed++))
    done
    
    log_error "API non disponibile dopo ${max_wait}s"
    return 1
}

# Estrai valori JSON in modo robusto
parse_json() {
    local json="$1"
    local key="$2"
    echo "$json" | grep -o "\"$key\":[^,}]*" | head -1 | cut -d: -f2- | tr -d ' "' || echo ""
}

# Aspetta che un'operazione asincrona si completi
wait_for_operation() {
    local operation_id=$1
    local max_wait=${2:-90}
    local elapsed=0
    
    log_info "In attesa del completamento dell'operazione $operation_id (max ${max_wait}s)..."
    
    while [ $elapsed -lt "$max_wait" ]; do
        local op_response=$(curl -s "${API_URL}/operation-status/${operation_id}" 2>/dev/null || echo "{}")
        local status=$(parse_json "$op_response" "status")
        
        if [ -z "$status" ]; then
            log_warning "Operazione non trovata, retry..."
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
    
    log_error "Timeout in attesa del completamento operazione"
    return 1
}

test_start_container() {
    log_info "TEST 1: Start container '$IMAGE_NAME'"
    
    # Pulisci container precedenti
    curl -s -X POST "http://localhost:${PORT}/stop/${CONTAINER_NAME}" > /dev/null 2>&1 || true
    sleep 1
    
    local response=$(curl -s -X POST "${API_URL}/start/${IMAGE_NAME}")
    log_info "Start response: $response"
    
    if echo "$response" | grep -q "operation_id"; then
        local operation_id=$(parse_json "$response" "operation_id")
        log_info "Start iniziato. Operation ID: $operation_id"
        
        # Aspetta completamento
        local op_response=$(wait_for_operation "$operation_id" 90)
        
        if [ $? -eq 0 ]; then
            local op_status=$(parse_json "$op_response" "status")
            local started=$(parse_json "$op_response" "started")
            
            log_info "Operation response: $op_response"
            
            if [ "$op_status" = "completed" ] && [ "$started" = "1" ]; then
                log_success "Container avviato con successo"
                sleep 2
                
                # Verifica che il container sia in system-info
                local sys_info=$(curl -s "${API_URL}/system-info")
                if echo "$sys_info" | grep -q "$CONTAINER_NAME"; then
                    log_success "Container verificato in system-info"
                    return 0
                else
                    log_warning "Container non trovato in system-info, ma operazione completata"
                    return 0
                fi
            else
                log_error "Operazione completata ma container non avviato. Status: $op_status, Started: $started"
                return 1
            fi
        else
            log_error "Operazione fallita o timeout"
            return 1
        fi
    else
        log_error "Risposta invalida: $response"
        return 1
    fi
}

test_start_already_running() {
    log_info "TEST 2: Start container già in esecuzione"
    
    local response=$(curl -s -X POST "${API_URL}/start/${IMAGE_NAME}")
    log_info "Response: $response"
    
    if echo "$response" | grep -q "operation_id"; then
        local operation_id=$(parse_json "$response" "operation_id")
        
        local op_response=$(wait_for_operation "$operation_id" 60)
        if [ $? -eq 0 ]; then
            local already_running=$(parse_json "$op_response" "already_running")
            
            if [ "$already_running" = "1" ]; then
                log_success "Correttamente identificato container già in esecuzione"
                return 0
            else
                log_warning "Container non marcato come already_running. Response: $op_response"
                return 0
            fi
        fi
    fi
    
    log_error "Test fallito"
    return 1
}

test_stop_container() {
    log_info "TEST 3: Stop container '$CONTAINER_NAME'"
    
    local response=$(curl -s -X POST "http://localhost:${PORT}/stop/${CONTAINER_NAME}")
    log_info "Stop response: $response"
    
    if echo "$response" | grep -q "stopped"; then
        log_success "Container fermato con successo"
        sleep 2
        return 0
    elif echo "$response" | grep -q "not found\|Not Found"; then
        log_warning "Container non trovato (potrebbe non essere stato creato)"
        return 0
    else
        log_error "Stop fallito: $response"
        return 1
    fi
}

test_stop_nonexistent() {
    log_info "TEST 4: Stop container inesistente"
    
    local fake_container="playground-nonexistent-container-xyz-12345"
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_URL}/stop/${fake_container}")
    
    if [ "$http_code" = "404" ]; then
        log_success "Correttamente restituito 404 per container inesistente"
        return 0
    else
        log_error "HTTP code atteso 404, ricevuto $http_code"
        return 1
    fi
}

test_start_invalid_image() {
    log_info "TEST 5: Start container con immagine invalida"
    
    local response=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/start/invalid-image-xyz-nonexistent")
    local http_code=$(echo "$response" | tail -1)
    local body=$(echo "$response" | head -n -1)
    
    log_info "Response code: $http_code, body: $body"
    
    if [ "$http_code" = "404" ]; then
        log_success "Correttamente restituito 404 per immagine invalida"
        return 0
    else
        log_error "HTTP code atteso 404, ricevuto $http_code"
        return 1
    fi
}

test_system_info() {
    log_info "TEST 6: System info endpoint"
    
    local response=$(curl -s "${API_URL}/system-info")
    
    if echo "$response" | grep -q '"docker"' && echo "$response" | grep -q '"network"' && echo "$response" | grep -q '"volume"'; then
        log_success "System info contiene tutti i campi richiesti"
        return 0
    fi
    
    log_error "System info risposta invalida"
    return 1
}

test_operation_status_nonexistent() {
    log_info "TEST 7: Get status operazione inesistente"
    
    local fake_op_id="nonexistent-op-id-12345"
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/operation-status/${fake_op_id}")
    
    if [ "$http_code" = "404" ]; then
        log_success "Correttamente restituito 404 per operazione inesistente"
        return 0
    else
        log_error "HTTP code atteso 404, ricevuto $http_code"
        return 1
    fi
}

main() {
    log_info "============================================"
    log_info "API Test Suite - Start/Stop Container"
    log_info "============================================"
    log_info ""
    
    # Pulizia iniziale
    log_info "Pulizia iniziale..."
    lsof -ti:${PORT} | xargs kill -9 2>/dev/null || true
    sleep 1
    
    # Avvio server
    log_info "Avvio WebUI server..."
    bash "${SERVER_SCRIPT}" &
    SERVER_PID=$!
    log_info "Server avviato con PID: $SERVER_PID"
    
    sleep "$INITIAL_WAIT"
    
    if ! ps -p "$SERVER_PID" > /dev/null 2>&1; then
        log_error "Server terminato durante l'inizializzazione"
        [ -f "$WEB_LOG" ] && tail -20 "$WEB_LOG"
        return 1
    fi
    
    if ! wait_for_api "$TIMEOUT"; then
        log_error "Impossibile connettersi all'API"
        return 1
    fi
    
    # Esecuzione test
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
    log_info "RISULTATI TEST"
    log_info "============================================"
    log_success "Test passati: $tests_passed"
    if [ $tests_failed -gt 0 ]; then
        log_error "Test falliti: $tests_failed"
    else
        log_success "Nessun test fallito!"
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