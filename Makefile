# Docker Playground - CLI Makefile
# Quick commands for CLI management

.PHONY: help install uninstall test test-cli test-webui test-all clean cli web list ps categories version dev-setup docs setup

# Colors
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
BLUE := \033[0;34m
NC := \033[0m

help:
	@echo ""
	@echo "$(CYAN)🐳 Docker Playground - CLI Management$(NC)"
	@echo ""
	@echo "$(GREEN)Setup Commands:$(NC)"
	@echo "  make install         Install CLI globally as 'playground' command"
	@echo "  make uninstall       Remove CLI and clean up"
	@echo "  make dev-setup       Setup development environment"
	@echo ""
	@echo "$(GREEN)Test Commands:$(NC)"
	@echo "  make test            Run all tests in cascade (cli → webui → all)"
	@echo "  make test-cli        Run CLI test suite only"
	@echo "  make test-webui      Run WebUI test suite only"
	@echo "  make test-all        Run comprehensive tests only"
	@echo ""
	@echo "$(GREEN)Quick Commands:$(NC)"
	@echo "  make cli             Run CLI directly (without installing)"
	@echo "  make web             Start web dashboard"
	@echo "  make clean           Clean up virtual environments"
	@echo "  make list            List all containers"
	@echo "  make ps              Show running containers"
	@echo "  make categories      Show container categories"
	@echo "  make version         Show CLI version"
	@echo ""
	@echo "$(GREEN)Usage Examples:$(NC)"
	@echo "  make cli ARGS='list'"
	@echo "  make cli ARGS='start nginx'"
	@echo "  make cli ARGS='ps'"
	@echo ""

install:
	@echo "$(CYAN)Installing CLI globally...$(NC)"
	@chmod +x playground install-cli.sh uninstall-cli.sh tests/test-cli.sh
	@./install-cli.sh
	@echo "$(GREEN)✓ Installation complete$(NC)"

uninstall:
	@echo "$(CYAN)Uninstalling CLI...$(NC)"
	@./uninstall-cli.sh
	@echo "$(GREEN)✓ Uninstallation complete$(NC)"

# Test cascade - runs all tests in sequence
test: test-cli test-webui test-all
	@echo ""
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)✓ All tests completed successfully!$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""

test-cli:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(CYAN)Running CLI tests...$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@chmod +x tests/test-cli.sh
	@./tests/test-cli.sh --non-interactive
	@echo ""

test-webui:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(CYAN)Running WebUI tests...$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@chmod +x tests/test-webui.sh
	@./tests/test-webui.sh
	@echo ""

test-all:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(CYAN)Running comprehensive tests...$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@chmod +x tests/test-all.sh playground
	@./playground list
	@./tests/test-all.sh
	@echo ""

cli:
	@chmod +x playground
	@./playground $(ARGS)

web:
	@echo "$(CYAN)Starting web dashboard...$(NC)"
	@chmod +x start-webui.sh
	@./start-webui.sh

clean:
	@echo "$(CYAN)Cleaning up virtual environments...$(NC)"
	@rm -rf venv/environments
	@rm -f venv/.cli_venv_ready
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

# Alias shortcuts
list:
	@make cli ARGS="list"

ps:
	@make cli ARGS="ps"

categories:
	@make cli ARGS="categories"

version:
	@make cli ARGS="version"

# Development helpers
dev-setup:
	@echo "$(CYAN)Setting up development environment...$(NC)"
	@chmod +x playground install-cli.sh uninstall-cli.sh tests/test-cli.sh tests/test-webui.sh tests/test-all.sh start-webui.sh
	@make clean
	@echo "$(GREEN)✓ Development environment ready$(NC)"
	@echo "$(YELLOW)Run 'make cli ARGS=\"list\"' to test$(NC)"
	@echo ""

# Documentation
docs:
	@echo ""
	@echo "$(CYAN)📚 Documentation Files:$(NC)"
	@echo "  CLI-README.md        CLI usage and examples"
	@echo "  README.md            Main project documentation"
	@echo ""
	@echo "$(CYAN)Quick Reference:$(NC)"
	@echo "  ./playground list              List all containers"
	@echo "  ./playground start <name>      Start a container"
	@echo "  ./playground stop <name>       Stop a container"
	@echo "  ./playground ps                Show running containers"
	@echo "  ./playground exec <name>       Open shell in container"
	@echo "  ./playground --help            Full help"
	@echo ""

# All-in-one setup
setup: dev-setup install test
	@echo ""
	@echo "$(GREEN)╔══════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║   Complete setup finished!               ║$(NC)"
	@echo "$(GREEN)╚══════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)You can now use:$(NC)"
	@echo "  playground --help"
	@echo "  playground list"
	@echo "  make test"
	@echo ""