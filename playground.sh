#!/bin/bash

#############################################
# Docker Playground Manager
# A professional tool for managing Docker development environments
# Version: 2.4
#############################################

set -euo pipefail

# Configuration
CONFIG_FILE="config.yml"
COMPOSE_FILE="docker-compose.yml"
SHARED_DIR="$(pwd)/shared-volumes"
LOG_FILE="$(pwd)/playground.log"
NETWORK_NAME="playground-network"
PLAYGROUND_LABEL="playground.managed=true"
MOTD_DIR="$(pwd)/motd"

# Colors for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# ---------------------------------------------
# GLOBAL TRAP FIX:
# Ignore Ctrl+C globally to prevent exiting the script unless explicitly allowed.
# We set a placeholder function that will be executed when INT is received.
# 'break' will only work inside a while loop, so we use a dummy function
# which we will manually override in functions that need to catch it.
# We define the actual action in main_menu's while loop.
# ---------------------------------------------
dummy_trap_handler() {
    # This prevents the script from exiting when Ctrl+C is pressed outside of a read/whiptail/sleep loop.
    :
}
trap 'dummy_trap_handler' INT

#############################################
# Utility Functions
#############################################

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

print_header() {
  clear
  echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
  echo -e "${BLUE}║       🐳 Docker Playground Manager v2.4            ║${NC}"
  echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
  echo ""
}

check_dependencies() {
  local missing_deps=()
  
  if ! command -v docker &>/dev/null; then
    missing_deps+=("docker")
  fi
  
  if ! command -v docker compose &>/dev/null && ! command -v docker-compose &>/dev/null; then
    missing_deps+=("docker-compose")
  fi
  
  if ! command -v yq &>/dev/null; then
    if whiptail --yesno "yq is not installed. Install it via snap?" 10 60; then
      sudo snap install yq || {
        whiptail --msgbox "Failed to install yq. Please install it manually." 10 60
        exit 1
      }
    else
      missing_deps+=("yq")
    fi
  fi
  
  if [ ${#missing_deps[@]} -gt 0 ]; then
    whiptail --msgbox "Missing dependencies: ${missing_deps[*]}\nPlease install them and try again." 12 60
    exit 1
  fi
}

initialize_environment() {
  mkdir -p "$SHARED_DIR" "$MOTD_DIR"
  
  # Set permissions only if directory is empty or just created
  if [ ! -f "$SHARED_DIR/.initialized" ]; then
    chmod 777 "$SHARED_DIR" 2>/dev/null || true
    touch "$SHARED_DIR/.initialized"
  fi
  
  touch "$LOG_FILE"
  
  if [ ! -f "$SHARED_DIR/README.txt" ]; then
    cat > "$SHARED_DIR/README.txt" <<EOF
Docker Playground - Shared Volume
==================================

This directory is shared across all playground containers.
You can use it to:
- Exchange files between containers
- Test scripts across different environments
- Share configuration files

Mounted at: /shared (inside containers)
Host path: $SHARED_DIR
EOF
  fi
  
  if [ -d "$SHARED_DIR" ] && [ -w "$SHARED_DIR" ]; then
    echo "Test" > "$SHARED_DIR/test-write.txt" && rm "$SHARED_DIR/test-write.txt"
    log "Environment initialized successfully"
  else
    log "ERROR: Shared directory $SHARED_DIR is not writable"
    whiptail --msgbox "ERROR: Shared directory $SHARED_DIR is not writable. Check permissions." 10 60
    exit 1
  fi
}

show_motd() {
  local service="$1"
  local motd_file=""
  
  # Map service to MOTD file
  case "$service" in
    mysql*) motd_file="$MOTD_DIR/mysql.txt" ;;
    postgres*) motd_file="$MOTD_DIR/postgres.txt" ;;
    mongodb*) motd_file="$MOTD_DIR/mongodb.txt" ;;
    redis*) motd_file="$MOTD_DIR/redis.txt" ;;
    docker-dind) motd_file="$MOTD_DIR/docker.txt" ;;
    python*) motd_file="$MOTD_DIR/python.txt" ;;
    node*) motd_file="$MOTD_DIR/node.txt" ;;
    golang*) motd_file="$MOTD_DIR/golang.txt" ;;
    nginx*) motd_file="$MOTD_DIR/nginx.txt" ;;
    rust*) motd_file="$MOTD_DIR/rust.txt" ;;
    elasticsearch) motd_file="$MOTD_DIR/elasticsearch.txt" ;;
  esac
  
  if [ -n "$motd_file" ] && [ -f "$motd_file" ]; then
    clear
    cat "$motd_file"
    read -r -p ""
  fi
}

#############################################
# Docker Compose Generation
#############################################

generate_compose() {
  local selected=("$@")
  
  cat <<EOF > "$COMPOSE_FILE"
networks:
  $NETWORK_NAME:
    driver: bridge

services:
EOF

  for img in "${selected[@]}"; do
    img="${img//\"/}"
    image_name=$(yq ".images.\"$img\".image" "$CONFIG_FILE")
    keep_alive_cmd=$(yq ".images.\"$img\".keep_alive_cmd // \"sleep infinity\"" "$CONFIG_FILE")
    shell_cmd=$(yq ".images.\"$img\".shell // \"/bin/bash\"" "$CONFIG_FILE")
    privileged=$(yq ".images.\"$img\".privileged // false" "$CONFIG_FILE")
    
    cat <<EOF >> "$COMPOSE_FILE"
  $img:
    image: $image_name
    container_name: playground-$img
    hostname: $img
    networks:
      - $NETWORK_NAME
    volumes:
      - $SHARED_DIR:/shared
    command: $keep_alive_cmd
    stdin_open: true
    tty: true
    restart: unless-stopped
    labels:
      - "playground.managed=true"
      - "playground.image=$img"
EOF

    if [ "$privileged" = "true" ]; then
      echo "    privileged: true" >> "$COMPOSE_FILE"
    fi
    
    env_keys=$(yq ".images.\"$img\".environment // {} | keys | .[]" "$CONFIG_FILE" 2>/dev/null || echo "")
    if [ -n "$env_keys" ]; then
      echo "    environment:" >> "$COMPOSE_FILE"
      while IFS= read -r key; do
        value=$(yq ".images.\"$img\".environment.\"$key\"" "$CONFIG_FILE")
        echo "      $key: $value" >> "$COMPOSE_FILE"
      done <<< "$env_keys"
    fi
    
    port_count=$(yq ".images.\"$img\".ports | length" "$CONFIG_FILE" 2>/dev/null || echo "0")
    if [ "$port_count" -gt 0 ]; then
      echo "    ports:" >> "$COMPOSE_FILE"
      for ((i=0; i<port_count; i++)); do
        port=$(yq ".images.\"$img\".ports[$i]" "$CONFIG_FILE")
        echo "      - \"$port\"" >> "$COMPOSE_FILE"
      done
    fi
    
    echo "" >> "$COMPOSE_FILE"
  done
  
  log "Generated docker-compose.yml with services: ${selected[*]}"
}

#############################################
# Selection Functions
#############################################

select_instances() {
  local action="$1"
  local category_filter="${2:-}"
  local selected=()
  local options=()
  
  mapfile -t images < <(yq '.images | keys | .[]' "$CONFIG_FILE")
  
  local running=()
  if [ "$action" = "stop" ]; then
    mapfile -t running < <(docker ps --filter "label=playground.managed=true" --format "{{.Labels}}" | grep -oP 'playground.image=\K[^,]+' | sort -u 2>/dev/null || echo "")
  fi
  
  for img in "${images[@]}"; do
    description=$(yq ".images.\"$img\".description // \"No description\"" "$CONFIG_FILE")
    category=$(yq ".images.\"$img\".category // \"other\"" "$CONFIG_FILE")
    
    # Apply category filter if specified
    if [ -n "$category_filter" ] && [ "$category" != "$category_filter" ]; then
      continue
    fi
    
    # Check if running
    is_running=$(docker ps -q --filter "name=playground-$img" --filter "label=playground.managed=true" 2>/dev/null)
    
    if [ "$action" = "start" ] && [ -n "$is_running" ]; then
      continue  # Skip already running containers for start
    fi
    
    if [ "$action" = "stop" ] && [[ " ${running[*]} " =~ " $img " ]]; then
      options+=("$img" "[$category] $description" on)
    else
      options+=("$img" "[$category] $description" off)
    fi
  done
  
  if [ ${#options[@]} -eq 0 ]; then
    echo ""
    return
  fi
  
  local title="Select Container Instances"
  if [ -n "$category_filter" ]; then
    title="Select Containers - Category: $category_filter"
  fi
  
  selected=$(whiptail --title "$title" \
    --checklist "Choose one or more containers to $action:\n(Use SPACE to select, ENTER to confirm)" \
    22 85 14 "${options[@]}" 3>&1 1>&2 2>&3)
  
  echo "$selected"
}

select_single_instance() {
  local title="$1"
  local message="$2"
  
  # Get ONLY running containers - direct approach
  local running_containers=$(docker ps --filter "label=playground.managed=true" --filter "status=running" --format "{{.Names}}" 2>/dev/null | sed 's/playground-//' | sort -u)
  
  if [ -z "$running_containers" ]; then
    echo ""
    return
  fi
  
  local options=()
  while IFS= read -r service; do
    # Skip empty lines
    [ -z "$service" ] && continue
    
    # Verify the service exists in config
    if yq ".images.\"$service\"" "$CONFIG_FILE" &>/dev/null; then
      description=$(yq ".images.\"$service\".description // \"No description\"" "$CONFIG_FILE" 2>/dev/null)
      category=$(yq ".images.\"$service\".category // \"other\"" "$CONFIG_FILE" 2>/dev/null)
      options+=("$service" "[$category] $description")
    fi
  done <<< "$running_containers"
  
  # Check if we have any valid options
  if [ ${#options[@]} -eq 0 ]; then
    echo ""
    return
  fi
  
  selected=$(whiptail --title "$title" --menu "$message" 22 75 14 "${options[@]}" 3>&1 1>&2 2>&3)
  echo "$selected"
}

cleanup_dead_containers() {
  # Remove any stopped/dead containers with playground label
  docker ps -a --filter "label=playground.managed=true" --filter "status=exited" -q | xargs -r docker rm 2>/dev/null || true
  docker ps -a --filter "label=playground.managed=true" --filter "status=dead" -q | xargs -r docker rm 2>/dev/null || true
}

select_category() {
  local categories=("linux" "programming" "database" "messaging" "webserver" "devops" "monitoring" "ml" "utility")
  local options=()
  
  for cat in "${categories[@]}"; do
    count=$(yq ".images | to_entries[] | select(.value.category == \"$cat\") | .key" "$CONFIG_FILE" 2>/dev/null | wc -l)
    if [ "$count" -gt 0 ]; then
      options+=("$cat" "$count images")
    fi
  done
  
  selected=$(whiptail --title "Select Category" --menu "Choose a category:" 20 60 12 "${options[@]}" 3>&1 1>&2 2>&3)
  echo "$selected"
}

#############################################
# Container Management Functions
#############################################

start_containers() {
  selected=$(select_instances "start")
  
  if [ -z "$selected" ]; then
    whiptail --msgbox "No instances selected or all are already running." 10 55
    return
  fi
  
  read -r -a selected_array <<< "$selected"
  generate_compose "${selected_array[@]}"
  
  if docker compose -f "$COMPOSE_FILE" up -d; then
    log "Started containers: ${selected_array[*]}"
    whiptail --msgbox "✓ Successfully started:\n\n${selected_array[*]}\n\nUse 'Enter container' to interact." 14 65
  else
    log "ERROR: Failed to start containers"
    whiptail --msgbox "✗ Failed to start containers. Check docker logs." 10 60
  fi
}

start_by_category() {
  category=$(select_category)
  
  if [ -z "$category" ]; then
    return
  fi
  
  selected=$(select_instances "start" "$category")
  
  if [ -z "$selected" ]; then
    whiptail --msgbox "No instances selected." 10 50
    return
  fi
  
  read -r -a selected_array <<< "$selected"
  generate_compose "${selected_array[@]}"
  
  if docker compose -f "$COMPOSE_FILE" up -d; then
    log "Started containers from category $category: ${selected_array[*]}"
    whiptail --msgbox "✓ Successfully started from category '$category':\n\n${selected_array[*]}" 14 65
  else
    log "ERROR: Failed to start containers"
    whiptail --msgbox "✗ Failed to start containers." 10 60
  fi
}

stop_containers() {
  selected=$(select_instances "stop")
  
  if [ -z "$selected" ]; then
    whiptail --msgbox "No running instances to stop." 8 40
    return
  fi
  
  read -r -a selected_array <<< "$selected"
  generate_compose "${selected_array[@]}"
  
  if docker compose -f "$COMPOSE_FILE" down; then
    log "Stopped containers: ${selected_array[*]}"
    whiptail --msgbox "✓ Successfully stopped:\n\n${selected_array[*]}" 12 65
  else
    log "ERROR: Failed to stop containers"
    whiptail --msgbox "✗ Failed to stop containers." 10 60
  fi
}

list_containers() {
  # Show ONLY running containers
  output=$(docker ps --filter "label=playground.managed=true" --filter "status=running" \
    --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" 2>/dev/null || echo "")
  
  if [ -z "$output" ] || [ "$(echo "$output" | wc -l)" -eq 1 ]; then
    whiptail --msgbox "No active containers found." 8 40
  else
    whiptail --title "Active Playground Containers" --msgbox "$output" 22 80 --scrolltext
  fi
}

enter_container() {
  # Clean up any dead containers first
  cleanup_dead_containers
  
  service=$(select_single_instance "Enter Container" "Choose a container to enter:")
  
  if [ -z "$service" ]; then
    whiptail --msgbox "No running containers available." 8 50
    return
  fi
  
  # Double check container is actually running
  is_running=$(docker ps -q --filter "name=playground-$service" --filter "status=running" 2>/dev/null)
  
  if [ -z "$is_running" ]; then
    whiptail --msgbox "Container $service is not running.\n\nPlease start it first." 10 50
    return
  fi
  
  # Show MOTD if available
  show_motd "$service"
  
  shell_cmd=$(yq ".images.\"$service\".shell // \"/bin/bash\"" "$CONFIG_FILE")
  
  clear
  echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║  Entering container: playground-$service"
  echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
  echo -e "${YELLOW}Type 'exit' to return to the menu${NC}"
  echo ""
  log "Entering container: $service"
  
  # Generate compose for this specific container if needed
  if [ ! -f "$COMPOSE_FILE" ]; then
    generate_compose "$service"
  fi
  
  docker compose -f "$COMPOSE_FILE" exec -it "$service" "$shell_cmd" || {
    log "ERROR: Failed to enter $service"
    whiptail --msgbox "Failed to enter $service.\n\nThe container may have stopped." 10 60
  }
  
  log "Exited container: $service"
}

container_logs() {
  service=$(select_single_instance "View Container Logs" "Choose a container:")
  
  if [ -z "$service" ]; then
    whiptail --msgbox "No container selected." 8 40
    return
  fi
  
  clear
  echo -e "${GREEN}Logs for: playground-$service${NC}"
  echo -e "${YELLOW}Press Ctrl+C to return to menu${NC}"
  echo ""
  
  # Create a subshell that handles the logs
  (
    # This subshell will be killed on Ctrl+C
    docker compose -f "$COMPOSE_FILE" logs -f "$service" 2>&1
  ) &
  
  local log_pid=$!
  
  # Wait for Ctrl+C in the parent shell
  trap "kill $log_pid 2>/dev/null; trap - INT; echo -e '\n${GREEN}Returning to menu...${NC}'; sleep 1; return 0" INT
  
  # Wait for the background process
  wait $log_pid 2>/dev/null
  
  # Clean up trap
  trap - INT
  
  echo -e "\n${GREEN}Returning to menu...${NC}"
  sleep 1
}

restart_container() {
  service=$(select_single_instance "Restart Container" "Choose a container to restart:")
  
  if [ -z "$service" ]; then
    whiptail --msgbox "No container selected." 8 40
    return
  fi
  
  if docker compose -f "$COMPOSE_FILE" restart "$service"; then
    log "Restarted container: $service"
    whiptail --msgbox "✓ Container $service restarted successfully." 8 50
  else
    log "ERROR: Failed to restart $service"
    whiptail --msgbox "✗ Failed to restart $service." 8 50
  fi
}

#############################################
# Container Statistics (Manuale Refresh)
#############################################
container_stats() {
  local GREEN='\033[0;32m'
  local YELLOW='\033[1;33m'
  local RED='\033[0;31m'
  local NC='\033[0m'
  local CYAN='\033[0;36m'

  # 1. Salva la trap INT dello script principale
  local old_trap
  old_trap=$(trap -p INT | sed "s/trap -- '//; s/' INT//")
  
  # 2. Imposta la trap INT: esegue la pulizia e poi termina la funzione con 'return'.
  # Il 'return' esce dalla funzione e riporta il controllo al main_menu.
  trap 'echo -e "\n${GREEN}Ritorno al menu...${NC}"; sleep 1; return' INT
  
  while true; do
    clear 
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              Container Statistics                          ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo -e "${YELLOW}Premi INVIO per aggiornare, Ctrl+C per tornare al menu.${NC}"
    echo ""

    containers_ids=$(docker ps --filter "label=playground.managed=true" --filter "status=running" -q)
    
    if [ -z "$containers_ids" ]; then
      echo -e "${RED}Attenzione: Nessun contenitore in esecuzione trovato.${NC}"
      read -r -p "Premi Invio per continuare..." || true
      # Rimuove il "return" qui, in modo che il controllo segua il flusso normale
      break
    fi

    echo -e "${CYAN}NAME\t\t\tCPU %\tMEM USAGE / LIMIT\tMEM %\tNET I/O\t\tBLOCK I/O${NC}"
    echo -e "──────────────────────────────────────────────────────────────────────────────────────"
    
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}" $containers_ids | tail -n +2
    
    # 3. Blocco di input (read)
    # read -r -p "" input
    # Usiamo 'read -r -s -n 1' senza un loop interno, in modo che la trap sia l'unico modo per uscire.
    # Quando l'utente preme INVIO, la read termina.
    # Quando l'utente preme Ctrl+C, la trap viene attivata e ritorna al menu.
    
    # Il problema era che Ctrl+C interrompeva la read, ma non forniva una nuova riga,
    # lasciando il terminale confuso. Aggiungiamo un semplice sleep per resettare il segnale.
    
    echo -n "" # Assicura una riga pulita per la read successiva

    # Usiamo read -r -s per un'esperienza migliore, se Invio è la tua unica opzione.
    read -r -p "" input
    
    # Questo punto viene raggiunto solo se l'utente preme Invio.
  done
  
  # 4. Ripristina la trap INT originale.
  trap "$old_trap" INT 
}

#############################################
# Dashboard & Information
#############################################

show_dashboard() {
  clear
  print_header
  
  running=$(docker ps --filter "label=playground.managed=true" -q | wc -l)
  total=$(yq '.images | length' "$CONFIG_FILE")
  
  echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${CYAN}║                    PLAYGROUND DASHBOARD                    ║${NC}"
  echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
  echo ""
  
  echo -e "${BLUE}📊 Statistics:${NC}"
  echo -e "   Active Containers: ${GREEN}$running${NC} / ${YELLOW}$total${NC} available"
  echo ""
  
  if [ $running -gt 0 ]; then
    echo -e "${BLUE}🔥 Running Containers:${NC}"
    docker ps --filter "label=playground.managed=true" --format "{{.Names}} {{.Image}}" 2>/dev/null | while read -r name image; do
      echo -e "   ${GREEN}•${NC} $name ${CYAN}($image)${NC}"
    done
    echo ""
  fi
  
  # Category breakdown
  echo -e "${BLUE}📦 Images by Category:${NC}"
  categories=("linux" "programming" "database" "messaging" "webserver" "devops" "monitoring" "ml" "utility")
  for cat in "${categories[@]}"; do
    count=$(yq ".images | to_entries[] | select(.value.category == \"$cat\") | .key" "$CONFIG_FILE" 2>/dev/null | wc -l)
    if [ "$count" -gt 0 ]; then
      printf "   ${YELLOW}%-15s${NC}: %2d images\n" "$cat" "$count"
    fi
  done
  
  echo ""
  echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  read -p "Press Enter to continue..." -r
}

quick_search() {
  search_term=$(whiptail --inputbox "Search images by name or description:" 10 60 3>&1 1>&2 2>&3) || return 0
  
  # Check if empty
  if [ -z "$search_term" ]; then
    return 0
  fi
  
  # Search in both keys and descriptions
  results=""
  
  # Search by key name
  while IFS= read -r img; do
    if echo "$img" | grep -qi "$search_term"; then
      desc=$(yq ".images.\"$img\".description" "$CONFIG_FILE" 2>/dev/null || echo "No description")
      results+="$img - $desc"$'\n'
    fi
  done < <(yq '.images | keys | .[]' "$CONFIG_FILE" 2>/dev/null || true)
  
  # Search by description
  while IFS= read -r img; do
    desc=$(yq ".images.\"$img\".description" "$CONFIG_FILE" 2>/dev/null || echo "")
    if [ -n "$desc" ] && echo "$desc" | grep -qi "$search_term"; then
      if ! echo "$results" | grep -q "^$img -"; then
        results+="$img - $desc"$'\n'
      fi
    fi
  done < <(yq '.images | keys | .[]' "$CONFIG_FILE" 2>/dev/null || true)
  
  # Remove empty lines and sort
  all_results=$(echo "$results" | grep -v '^$' | sort -u || true)
  
  if [ -z "$all_results" ]; then
    whiptail --msgbox "No images found matching: $search_term" 8 50 || true
  else
    whiptail --title "Search Results for: $search_term" --msgbox "$all_results" 22 90 --scrolltext || true
  fi
  
  return 0
}

#############################################
# Utility Functions
#############################################

browse_catalog() {
  local categories=("linux" "programming" "database" "messaging" "webserver" "devops" "monitoring" "ml" "utility")
  local catalog_text="╔══════════════════════════════════════════════════════════════╗\n"
  catalog_text+="║          Docker Playground - Complete Image Catalog          ║\n"
  catalog_text+="╚══════════════════════════════════════════════════════════════╝\n\n"
  
  for category in "${categories[@]}"; do
    images=$(yq ".images | to_entries[] | select(.value.category == \"$category\") | .key" "$CONFIG_FILE" 2>/dev/null || echo "")
    
    if [ -n "$images" ]; then
      catalog_text+="$(echo "$category" | tr '[:lower:]' '[:upper:]')\n"
      catalog_text+="══════════════════════════════════════════════════════════════\n"
      
      while IFS= read -r img; do
        desc=$(yq ".images.\"$img\".description" "$CONFIG_FILE")
        image_name=$(yq ".images.\"$img\".image" "$CONFIG_FILE")
        catalog_text+="  • $img\n"
        catalog_text+="    $desc\n"
        catalog_text+="    Image: $image_name\n\n"
      done <<< "$images"
    fi
  done
  
  whiptail --title "Image Catalog (${total} total)" --msgbox "$catalog_text" 30 85 --scrolltext
}

cleanup_all() {
  if whiptail --yesno "⚠️  WARNING ⚠️\n\nThis will:\n• Stop all playground containers\n• Remove all containers\n• Delete shared volume data\n• Remove docker-compose.yml\n\nAre you absolutely sure?" 16 65; then
    
    docker ps -q --filter "label=playground.managed=true" | xargs -r docker stop 2>/dev/null
    docker ps -aq --filter "label=playground.managed=true" | xargs -r docker rm 2>/dev/null
    
    docker network rm "$NETWORK_NAME" 2>/dev/null || true
    
    rm -rf "$SHARED_DIR"
    mkdir -p "$SHARED_DIR"
    
    rm -f "$COMPOSE_FILE"
    
    log "Full cleanup performed"
    whiptail --msgbox "✓ Cleanup completed successfully.\n\nAll playground containers and data removed." 10 60
  fi
}

export_logs() {
  export_file="playground-logs-$(date +%Y%m%d-%H%M%S).txt"
  cp "$LOG_FILE" "$export_file"
  log "Logs exported to $export_file"
  whiptail --msgbox "✓ Logs exported to:\n\n$export_file" 10 60
}

show_info() {
  local info_text="╔══════════════════════════════════════════════════════════════╗\n"
  info_text+="║          Docker Playground Manager v2.4 - Info              ║\n"
  info_text+="╚══════════════════════════════════════════════════════════════╝\n\n"
  
  info_text+="📁 Configuration:\n"
  info_text+="   Config File: $CONFIG_FILE\n"
  info_text+="   Shared Volume: $SHARED_DIR\n"
  info_text+="   Log File: $LOG_FILE\n"
  info_text+="   MOTD Directory: $MOTD_DIR\n"
  info_text+="   Network: $NETWORK_NAME\n\n"
  
  total_images=$(yq '.images | length' "$CONFIG_FILE")
  info_text+="📦 Images:\n"
  info_text+="   Total Available: $total_images\n\n"
  
  running=$(docker ps --filter "label=playground.managed=true" -q | wc -l)
  info_text+="🚀 Containers:\n"
  info_text+="   Currently Running: $running\n\n"
  
  if [ $running -gt 0 ]; then
    info_text+="Active Containers:\n"
    while IFS= read -r container; do
      info_text+="   • $container\n"
    done < <(docker ps --filter "label=playground.managed=true" --format "{{.Names}}")
  fi
  
  whiptail --title "System Information" --msgbox "$info_text" 24 75 --scrolltext
}

show_help() {
  local help_text="╔══════════════════════════════════════════════════════════════╗\n"
  help_text+="║              Docker Playground Manager - Help                ║\n"
  help_text+="╚══════════════════════════════════════════════════════════════╝\n\n"
  
  help_text+="🚀 Quick Start:\n"
  help_text+="   1. Select 'Start containers' or 'Start by category'\n"
  help_text+="   2. Choose your desired images\n"
  help_text+="   3. Use 'Enter container' to access them\n\n"
  
  help_text+="📁 Shared Volume:\n"
  help_text+="   Files in $SHARED_DIR are accessible\n"
  help_text+="   from all containers at /shared\n\n"
  
  help_text+="💡 Tips:\n"
  help_text+="   • Some containers show helpful guides (MOTD) on entry\n"
  help_text+="   • Use 'Search images' to quickly find what you need\n"
  help_text+="   • 'Dashboard' shows an overview of your environment\n"
  help_text+="   • Containers persist between script restarts\n"
  help_text+="   • Use 'Cleanup' to remove everything and start fresh\n\n"
  
  help_text+="🔧 Container Management:\n"
  help_text+="   • Start: Launch new containers\n"
  help_text+="   • Stop: Shutdown and remove containers\n"
  help_text+="   • Enter: Get an interactive shell\n"
  help_text+="   • Logs: View container output\n"
  help_text+="   • Stats: Monitor resource usage\n\n"
  
  help_text+="📝 Categories:\n"
  help_text+="   linux, programming, database, messaging,\n"
  help_text+="   webserver, devops, monitoring, ml, utility\n"
  
  whiptail --title "Help & Documentation" --msgbox "$help_text" 30 70 --scrolltext
}

#############################################
# Main Menu
#############################################
#############################################
# Main Menu
#############################################
main_menu() {
  while true; do
    print_header
    
    # --- Gestione del segnale INT (Ctrl+C) per il menu ---
    # Se Ctrl+C viene premuto mentre whiptail è attivo, vogliamo tornare
    # al menu principale e ridisegnarlo.
    trap 'clear; echo -e "\n${YELLOW}Action interrupted. Returning to menu...${NC}"; continue' INT
    # --------------------------------------------------------

    # Show quick stats
    running=$(docker ps --filter "label=playground.managed=true" -q | wc -l)
    total=$(yq '.images | length' "$CONFIG_FILE")
    echo -e "${CYAN}Status:${NC} ${GREEN}$running${NC} running / ${YELLOW}$total${NC} available\n"
    
    # Esecuzione del menu whiptail
    choice=$(whiptail --title "Docker Playground Manager v2.4" \
      --menu "Choose an action:" 24 75 16 \
      "1" "▶️  Start containers              [Container]" \
      "2" "🎯 Start by category             [Container]" \
      "3" "⏹️  Stop containers               [Container]" \
      "4" "💻 Enter a container             [Container]" \
      "5" "📋 List active containers        [Monitor]" \
      "6" "📊 View container logs           [Monitor]" \
      "7" "🔄 Restart container             [Monitor]" \
      "8" "📈 Container statistics          [Monitor]" \
      "9" "📺 Dashboard                     [Monitor]" \
      "10" "🔍 Search images                 [Tools]" \
      "11" "📚 Browse catalog                [Tools]" \
      "12" "⚙  System information            [Tools]" \
      "13" "❓ Help                          [Tools]" \
      "14" "📤 Export logs                   [Maintenance]" \
      "15" "🧹 Cleanup (remove all)          [Maintenance]" \
      "16" "❌ Exit                           " 3>&1 1>&2 2>&3)
    
    # Check the exit status of whiptail. Status 1 usually means ESC/CANCEL/Ctrl+C.
    if [ $? -ne 0 ]; then
        continue # Redraw the menu
    fi
    
    # --- Ripristina la trap di default (dummy) ---
    # PRIMA di chiamare qualsiasi altra funzione (come container_stats), ripristiniamo la
    # trap alla 'dummy_trap_handler'. Questo è ESSENZIALE per permettere alle funzioni
    # chiamate (come container_stats) di impostare e gestire le loro proprie trap in modo sicuro.
    trap 'dummy_trap_handler' INT
    # ---------------------------------------------
    
    case $choice in
      1) start_containers ;;
      2) start_by_category ;;
      3) stop_containers ;;
      4) enter_container ;;
      5) list_containers ;;
      6) container_logs ;;
      7) restart_container ;;
      8) container_stats ;; # La funzione stats ora ha il controllo sicuro del Ctrl+C
      9) show_dashboard ;;
      10) quick_search ;;
      11) browse_catalog ;;
      12) show_info ;;
      13) show_help ;;
      14) export_logs ;;
      15) cleanup_all ;;
      16)
        log "Playground manager exited"
        # Ripristina la trap di sistema prima di uscire completamente
        trap - INT
        clear
        echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  Thank you for using Docker Playground! 🐳     ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
        echo ""
        exit 0
        ;;
      *)
        # Se whiptail fallisce o viene selezionata un'opzione non prevista
        # Ripristina la trap di sistema prima di uscire
        trap - INT
        exit 0
        ;;
    esac
  done
}

#############################################
# Main Execution
#############################################

check_dependencies
initialize_environment
main_menu