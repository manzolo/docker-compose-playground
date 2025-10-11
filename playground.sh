#!/bin/bash

#############################################
# Docker Playground Manager
# A professional tool for managing Docker development environments
# Version: 2.0
#############################################

set -euo pipefail

# Configuration
CONFIG_FILE="config.yml"
COMPOSE_FILE="docker-compose.yml"
SHARED_DIR="$(pwd)/shared-volumes"
LOG_FILE="$(pwd)/playground.log"
NETWORK_NAME="playground-network"

# Colors for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

#############################################
# Utility Functions
#############################################

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

print_header() {
  clear
  echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
  echo -e "${BLUE}║       Docker Playground Manager v2.0          ║${NC}"
  echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
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

# Create necessary directories and files
initialize_environment() {
  mkdir -p "$SHARED_DIR"
  touch "$LOG_FILE"
  
  # Create a welcome file in shared volume
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
  
  log "Environment initialized"
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
    img="${img//\"/}"  # Remove quotes
    
    # Get image configuration - FIXED: usando valori di default corretti
    image_name=$(yq ".images.\"$img\".image" "$CONFIG_FILE")
    keep_alive_cmd=$(yq ".images.\"$img\".keep_alive_cmd // \"sleep infinity\"" "$CONFIG_FILE")
    shell_cmd=$(yq ".images.\"$img\".shell // \"/bin/bash\"" "$CONFIG_FILE")
    privileged=$(yq ".images.\"$img\".privileged // false" "$CONFIG_FILE")
    
    # Start service definition
    cat <<EOF >> "$COMPOSE_FILE"
  $img:
    image: $image_name
    container_name: playground-$img
    hostname: $img
    networks:
      - $NETWORK_NAME
    volumes:
      - $SHARED_DIR:/shared
    command: $shell_cmd -c "$keep_alive_cmd"
    stdin_open: true
    tty: true
    restart: unless-stopped
EOF

    # Add privileged mode if needed
    if [ "$privileged" = "true" ]; then
      echo "    privileged: true" >> "$COMPOSE_FILE"
    fi
    
    # Add environment variables if defined
    env_keys=$(yq ".images.\"$img\".environment // {} | keys | .[]" "$CONFIG_FILE" 2>/dev/null || echo "")
    if [ -n "$env_keys" ]; then
      echo "    environment:" >> "$COMPOSE_FILE"
      while IFS= read -r key; do
        value=$(yq ".images.\"$img\".environment.\"$key\"" "$CONFIG_FILE")
        echo "      $key: $value" >> "$COMPOSE_FILE"
      done <<< "$env_keys"
    fi
    
    # Add port mappings if defined
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
  local selected=()
  local options=()
  
  mapfile -t images < <(yq '.images | keys | .[]' "$CONFIG_FILE")
  
  for img in "${images[@]}"; do
    # FIXED: rimosse le stringhe con apici singoli
    description=$(yq ".images.\"$img\".description // \"No description\"" "$CONFIG_FILE")
    category=$(yq ".images.\"$img\".category // \"other\"" "$CONFIG_FILE")
    options+=("$img" "[$category] $description" off)
  done
  
  selected=$(whiptail --title "Select Container Instances" \
    --checklist "Choose one or more containers to manage:\n(Use SPACE to select, ENTER to confirm)" \
    20 80 12 "${options[@]}" 3>&1 1>&2 2>&3)
  
  echo "$selected"
}

select_single_instance() {
  local title="$1"
  local message="$2"
  
  if [ ! -f "$COMPOSE_FILE" ]; then
    echo ""
    return
  fi
  
  services=$(yq '.services | keys | .[]' "$COMPOSE_FILE" 2>/dev/null || echo "")
  
  if [ -z "$services" ]; then
    echo ""
    return
  fi
  
  local options=()
  while IFS= read -r service; do
    description=$(yq ".images.\"$service\".description // \"N/A\"" "$CONFIG_FILE")
    options+=("$service" "$description")
  done <<< "$services"
  
  selected=$(whiptail --title "$title" --menu "$message" 20 70 12 "${options[@]}" 3>&1 1>&2 2>&3)
  echo "$selected"
}

#############################################
# Container Management Functions
#############################################

start_containers() {
  selected=$(select_instances)
  
  if [ -z "$selected" ]; then
    whiptail --msgbox "No instances selected." 8 40
    return
  fi
  
  read -r -a selected_array <<< "$selected"
  generate_compose "${selected_array[@]}"
  
  if docker compose -f "$COMPOSE_FILE" up -d; then
    log "Started containers: ${selected_array[*]}"
    whiptail --msgbox "✓ Successfully started:\n\n${selected_array[*]}\n\nUse 'Enter container' to interact." 12 60
  else
    log "ERROR: Failed to start containers"
    whiptail --msgbox "✗ Failed to start containers. Check docker logs." 8 60
  fi
}

stop_containers() {
  selected=$(select_instances)
  
  if [ -z "$selected" ]; then
    whiptail --msgbox "No instances selected." 8 40
    return
  fi
  
  read -r -a selected_array <<< "$selected"
  generate_compose "${selected_array[@]}"
  
  if docker compose -f "$COMPOSE_FILE" down; then
    log "Stopped containers: ${selected_array[*]}"
    whiptail --msgbox "✓ Successfully stopped:\n\n${selected_array[*]}" 10 60
  else
    log "ERROR: Failed to stop containers"
    whiptail --msgbox "✗ Failed to stop containers." 8 60
  fi
}

list_containers() {
  # FIXED: output più semplice con solo le informazioni essenziali
  output=$(docker ps --filter "name=playground-" \
    --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" 2>/dev/null || echo "")
  
  if [ -z "$output" ] || [ "$(echo "$output" | wc -l)" -eq 1 ]; then
    whiptail --msgbox "No active containers found." 8 40
  else
    whiptail --title "Active Playground Containers" --msgbox "$output" 20 78 --scrolltext
  fi
}

enter_container() {
  service=$(select_single_instance "Enter Container" "Choose a container to enter:")
  
  if [ -z "$service" ]; then
    whiptail --msgbox "No container selected or no active containers." 8 50
    return
  fi
  
  shell_cmd=$(yq ".images.\"$service\".shell // \"/bin/bash\"" "$CONFIG_FILE")
  
  clear
  echo -e "${GREEN}Entering container: playground-$service${NC}"
  echo -e "${YELLOW}Type 'exit' to return to the menu${NC}"
  echo ""
  
  docker compose -f "$COMPOSE_FILE" exec "$service" "$shell_cmd" || {
    whiptail --msgbox "Failed to enter $service.\nEnsure the container is running." 10 60
  }
  
  log "Entered container: $service"
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
  
  # Trap Ctrl+C to return to menu instead of exiting
  trap 'echo -e "\n${GREEN}Returning to menu...${NC}"; sleep 1; return' INT
  
  docker compose -f "$COMPOSE_FILE" logs -f "$service"
  
  # Reset trap
  trap - INT
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
    whiptail --msgbox "✗ Failed to restart $service." 8 50
  fi
}

container_stats() {
  clear
  echo -e "${GREEN}Container Statistics${NC}"
  echo -e "${YELLOW}Press Ctrl+C to return to menu${NC}"
  echo ""
  
  # Trap Ctrl+C to return to menu instead of exiting
  trap 'echo -e "\n${GREEN}Returning to menu...${NC}"; sleep 1; return' INT
  
  docker stats $(docker ps --filter "name=playground-" -q)
  
  # Reset trap
  trap - INT
}

#############################################
# Utility Functions
#############################################

browse_catalog() {
  local categories=("linux" "programming" "database" "webserver" "devops" "utility")
  local catalog_text="Docker Playground - Image Catalog\n\n"
  
  for category in "${categories[@]}"; do
    images=$(yq ".images | to_entries[] | select(.value.category == \"$category\") | .key" "$CONFIG_FILE" 2>/dev/null || echo "")
    
    if [ -n "$images" ]; then
      catalog_text+="═══ $(echo "$category" | tr '[:lower:]' '[:upper:]') ═══\n"
      
      while IFS= read -r img; do
        desc=$(yq ".images.\"$img\".description" "$CONFIG_FILE")
        image_name=$(yq ".images.\"$img\".image" "$CONFIG_FILE")
        catalog_text+="  • $img\n    $desc\n    Image: $image_name\n\n"
      done <<< "$images"
    fi
  done
  
  whiptail --title "Image Catalog" --msgbox "$catalog_text" 30 80 --scrolltext
}

cleanup_all() {
  if whiptail --yesno "⚠ WARNING ⚠\n\nThis will:\n• Stop all playground containers\n• Remove all containers\n• Delete shared volume data\n\nAre you absolutely sure?" 14 60; then
    
    # Stop and remove containers
    docker ps -q --filter "name=playground-" | xargs -r docker stop 2>/dev/null
    docker ps -aq --filter "name=playground-" | xargs -r docker rm 2>/dev/null
    
    # Remove network
    docker network rm "$NETWORK_NAME" 2>/dev/null || true
    
    # Clean up shared volume
    rm -rf "$SHARED_DIR"
    mkdir -p "$SHARED_DIR"
    
    # Remove compose file
    rm -f "$COMPOSE_FILE"
    
    log "Full cleanup performed"
    whiptail --msgbox "✓ Cleanup completed successfully.\n\nAll playground containers and data removed." 10 60
  fi
}

export_logs() {
  export_file="playground-logs-$(date +%Y%m%d-%H%M%S).txt"
  cp "$LOG_FILE" "$export_file"
  whiptail --msgbox "Logs exported to:\n$export_file" 10 60
}

show_info() {
  local info_text="Docker Playground Manager v2.0\n\n"
  info_text+="Configuration: $CONFIG_FILE\n"
  info_text+="Shared Volume: $SHARED_DIR\n"
  info_text+="Log File: $LOG_FILE\n"
  info_text+="Network: $NETWORK_NAME\n\n"
  
  # Count available images
  total_images=$(yq '.images | length' "$CONFIG_FILE")
  info_text+="Available Images: $total_images\n\n"
  
  # Count running containers
  running=$(docker ps --filter "name=playground-" -q | wc -l)
  info_text+="Running Containers: $running\n"
  
  whiptail --title "System Information" --msgbox "$info_text" 18 70
}

#############################################
# Main Menu
#############################################

main_menu() {
  while true; do
    print_header
    
    choice=$(whiptail --title "Docker Playground Manager" \
      --menu "Choose an action:" 22 70 14 \
      "1" "▶ Start containers" \
      "2" "■ Stop containers" \
      "3" "📋 List active containers" \
      "4" "💻 Enter a container" \
      "5" "📊 View container logs" \
      "6" "🔄 Restart container" \
      "7" "📈 Container statistics" \
      "8" "📚 Browse image catalog" \
      "9" "ℹ System information" \
      "10" "📤 Export logs" \
      "11" "🧹 Cleanup (remove all)" \
      "12" "❌ Exit" 3>&1 1>&2 2>&3)
    
    case $choice in
      1) start_containers ;;
      2) stop_containers ;;
      3) list_containers ;;
      4) enter_container ;;
      5) container_logs ;;
      6) restart_container ;;
      7) container_stats ;;
      8) browse_catalog ;;
      9) show_info ;;
      10) export_logs ;;
      11) cleanup_all ;;
      12)
        log "Playground manager exited"
        clear
        echo -e "${GREEN}Thank you for using Docker Playground!${NC}"
        exit 0
        ;;
      *)
        exit 0
        ;;
    esac
  done
}

#############################################
# Main Execution
#############################################

# Check dependencies
check_dependencies

# Initialize environment
initialize_environment

# Start main menu
main_menu