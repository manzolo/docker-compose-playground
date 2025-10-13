#!/bin/bash
#############################################
# Docker Playground CLI Uninstaller
# Removes global command and cleans up
#############################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_BASE_DIR="${PROJECT_DIR}/venv/environments"
INSTALL_DIR="/usr/local/bin"
SYMLINK_NAME="playground"
CACHE_FILE="${PROJECT_DIR}/venv/.cli_venv_ready"

log_info() {
    echo -e "${CYAN}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
}

log_error() {
    echo -e "${RED}[✗]${NC} $*" >&2
    exit 1
}

# Banner
cat << 'EOF'
╔══════════════════════════════════════════╗
║   🐳  Docker Playground CLI              ║
║   Uninstallation                         ║
╚══════════════════════════════════════════╝

EOF

# Chiedi conferma
echo -e "${YELLOW}This will remove 'playground' command and clean up virtual environment${NC}"
echo ""
read -p "Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "Uninstallation cancelled"
    exit 0
fi

# Rimuovi symlink
if [ -L "${INSTALL_DIR}/${SYMLINK_NAME}" ]; then
    log_info "Removing global command (requires sudo)..."
    sudo rm -f "${INSTALL_DIR}/${SYMLINK_NAME}"
    log_success "Global command removed"
else
    log_info "Global command not found (already removed?)"
fi

# Rimuovi virtual environment
if [ -d "$VENV_BASE_DIR" ]; then
    log_info "Removing virtual environment..."
    rm -rf "$VENV_BASE_DIR"
    log_success "Virtual environment removed"
fi

# Rimuovi cache file
if [ -f "$CACHE_FILE" ]; then
    rm -f "$CACHE_FILE"
fi

log_success "Uninstallation complete!"
echo ""
echo -e "${CYAN}Note:${NC} Configuration files and containers were preserved"
echo -e "To remove containers, run: ${CYAN}docker ps -a --filter label=playground.managed=true${NC}"