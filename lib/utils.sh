#!/bin/bash

#############################################
# Utility Functions Module
#############################################

print_header() {
  clear
  echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
  echo -e "${BLUE}║       🐳 Docker Playground Manager v3.0           ║${NC}"
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
  
  log_info "All dependencies check passed"
}

initialize_environment() {
  mkdir -p "$SHARED_DIR" "$MOTD_DIR" "$SCRIPTS_DIR"
  
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
Mounted at: /shared (inside containers)
Host path: $SHARED_DIR
EOF
  fi
  
  if [ -d "$SHARED_DIR" ] && [ -w "$SHARED_DIR" ]; then
    echo "Test" > "$SHARED_DIR/test-write.txt" && rm "$SHARED_DIR/test-write.txt"
    log_info "Environment initialized successfully"
  else
    log_error "Shared directory $SHARED_DIR is not writable"
    whiptail --msgbox "ERROR: Shared directory $SHARED_DIR is not writable." 10 60
    exit 1
  fi
}

cleanup_dead_containers() {
  docker ps -a --filter "label=playground.managed=true" --filter "status=exited" -q | xargs -r docker rm 2>/dev/null || true
  docker ps -a --filter "label=playground.managed=true" --filter "status=dead" -q | xargs -r docker rm 2>/dev/null || true
  log_info "Dead containers cleaned up"
}