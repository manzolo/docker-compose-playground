# Docker Playground - CLI Makefile
# Quick commands for CLI management

.PHONY: help install uninstall test clean cli web

# Colors
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

help:
	@echo ""
	@echo "$(CYAN)🐳 Docker Playground - CLI Management$(NC)"
	@echo ""
	@echo "$(GREEN)Setup Commands:$(NC)"
	@echo "  make install      Install CLI globally as 'playground' command"
	@echo "  make uninstall    Remove CLI and clean up"
	@echo "  make test         Run CLI test suite"
	@echo ""
	@echo "$(GREEN)Quick Commands:$(NC)"
	@echo "  make cli          Run CLI directly (without installing)"
	@echo "  make web          Start web dashboard"
	@echo "  make clean        Clean up virtual environments"
	@echo ""
	@echo "$(GREEN)Usage Examples:$(NC)"
	@echo "  make cli ARGS='list'"
	@echo "  make cli ARGS='start nginx'"
	@echo "  make cli ARGS='ps'"
	@echo ""

install:
	@echo "$(CYAN)Installing CLI globally...$(NC)"
	@chmod +x playground install-cli.sh uninstall-cli.sh test-cli.sh
	@./install-cli.sh

uninstall:
	@echo "$(CYAN)Uninstalling CLI...$(NC)"
	@./uninstall-cli.sh

test:
	@echo "$(CYAN)Running CLI tests...$(NC)"
	@chmod +x test-cli.sh
	@./test-cli.sh

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
	@chmod +x playground install-cli.sh uninstall-cli.sh test-cli.sh start-web.sh
	@make clean
	@echo "$(GREEN)✓ Development environment ready$(NC)"
	@echo "$(YELLOW)Run 'make cli ARGS=\"list\"' to test$(NC)"

# Documentation
docs:
	@echo ""
	@echo "$(CYAN)📚 Documentation Files:$(NC)"
	@echo "  CLI-README.md     CLI usage and examples"
	@echo "  README.md         Main project documentation"
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
	@echo "$(GREEN)✓ Complete setup finished!$(NC)"
	@echo "$(YELLOW)You can now use: playground --help$(NC)"
	@echo ""