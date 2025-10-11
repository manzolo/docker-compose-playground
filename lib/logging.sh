#!/bin/bash

#############################################
# Logging Module
#############################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Log levels
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

log_info() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*" >> "$LOG_FILE"
}

log_error() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" >> "$LOG_FILE"
  echo -e "${RED}ERROR: $*${NC}" >&2
}

log_warn() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] $*" >> "$LOG_FILE"
  echo -e "${YELLOW}WARNING: $*${NC}" >&2
}

log_success() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SUCCESS] $*" >> "$LOG_FILE"
  echo -e "${GREEN}SUCCESS: $*${NC}"
}

export_logs() {
  local export_file="playground-logs-$(date +%Y%m%d-%H%M%S).txt"
  cp "$LOG_FILE" "$export_file"
  log_info "Logs exported to $export_file"
  whiptail --msgbox "✓ Logs exported to:\n\n$export_file" 10 60
}