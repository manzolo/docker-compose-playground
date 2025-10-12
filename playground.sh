#!/bin/bash

#############################################
# Docker Playground Manager
# Version: 3.0 - Modular Edition
#############################################

set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
export CONFIG_FILE="${SCRIPT_DIR}/config.yml"
export COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
export SHARED_DIR="${SCRIPT_DIR}/shared-volumes"
export LOG_FILE="${SCRIPT_DIR}/playground.log"
export MOTD_DIR="${SCRIPT_DIR}/motd"
export SCRIPTS_DIR="${SCRIPT_DIR}/scripts"
export NETWORK_NAME="playground-network"
export PLAYGROUND_LABEL="playground.managed=true"

# Source all library modules
source "${SCRIPT_DIR}/lib/logging.sh"
source "${SCRIPT_DIR}/lib/utils.sh"
source "${SCRIPT_DIR}/lib/config_loader.sh"  # NEW!
source "${SCRIPT_DIR}/lib/config.sh"
source "${SCRIPT_DIR}/lib/motd.sh"
source "${SCRIPT_DIR}/lib/docker.sh"
source "${SCRIPT_DIR}/lib/ui.sh"

#############################################
# Main Execution
#############################################

main() {
  log_info "Docker Playground Manager v3.0 starting..."
  
  # Check dependencies
  check_dependencies
  
  # Initialize environment
  initialize_environment
  
  # Merge configuration files from config.d/
  merge_configs || {
    log_error "Failed to merge configuration files"
    exit 1
  }
  
  # Trap to cleanup merged config on exit
  trap cleanup_merged_config EXIT
  
  # Start main menu
  main_menu
}

# Trap for clean exit
trap 'log_info "Playground manager exited"; exit 0' EXIT

# Run main
main