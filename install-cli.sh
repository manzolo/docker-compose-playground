#!/bin/bash
#############################################
# Docker Playground CLI Installer
# Installs CLI as global command
#############################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_LAUNCHER="${PROJECT_DIR}/playground"
INSTALL_DIR="/usr/local/bin"
SYMLINK_NAME="playground"

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

# Verifica se playground script esiste
if [ ! -f "$CLI_LAUNCHER" ]; then
    log_error "CLI launcher not found at $CLI_LAUNCHER"
fi

# Banner
cat << 'EOF'
╔══════════════════════════════════════════╗
║   🐳  Docker Playground CLI              ║
║   Global Installation                    ║
╚══════════════════════════════════════════╝

EOF

# Verifica permessi
if [ "$EUID" -eq 0 ]; then
    log_error "Do not run as root. Use: ./install-cli.sh"
fi

# Chiedi conferma
echo -e "${YELLOW}This will install 'playground' command globally${NC}"
echo -e "Installation path: ${CYAN}${INSTALL_DIR}/${SYMLINK_NAME}${NC}"
echo ""
read -p "Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "Installation cancelled"
    exit 0
fi

# Rendi executable lo script
log_info "Making CLI launcher executable..."
chmod +x "$CLI_LAUNCHER"

# Crea symlink (richiede sudo)
log_info "Creating global command (requires sudo)..."

if sudo ln -sf "$CLI_LAUNCHER" "${INSTALL_DIR}/${SYMLINK_NAME}"; then
    log_success "Installation complete!"
    echo ""
    echo -e "${GREEN}You can now use:${NC}"
    echo -e "  ${CYAN}playground --help${NC}"
    echo -e "  ${CYAN}playground list${NC}"
    echo -e "  ${CYAN}playground start <container>${NC}"
    echo ""
    echo -e "${YELLOW}Note:${NC} First run will setup Python venv (takes ~30s)"
else
    log_error "Failed to create symlink. Check permissions."
fi