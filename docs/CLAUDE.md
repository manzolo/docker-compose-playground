# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Docker Playground Manager is a tool for managing multiple Docker development environments with three interfaces (TUI, Web UI, CLI) plus a standalone Docker deployment. It provides 100+ pre-configured containers for Linux distributions, databases, programming languages, web servers, and development tools. All containers share a `/shared` volume and communicate via a dedicated Docker network (`playground-network`).

## Architecture

### Core Components

**Three-Tier Architecture:**
1. **CLI Layer** (`src/cli/`) - Typer-based command-line interface
2. **Web Layer** (`src/web/`) - FastAPI-based web dashboard with WebSocket support
3. **TUI Layer** (`playground.sh`) - Bash script using whiptail for terminal UI

All three interfaces share the same Docker operations logic but have separate implementations.

### Configuration System

**Hierarchical YAML Loading:**
- `config.yml` - Base settings (network name, shared volume path)
- `config.d/*.yml` - 100+ pre-configured containers (git-tracked)
- `custom.d/*.yml` - User-defined containers (git-ignored)

Configuration files are loaded in order, with later files overriding earlier ones. Each container config defines:
- `image`: Docker image name
- `category`: Grouping (linux, database, programming, etc.)
- `keep_alive_cmd`: Command to keep container running
- `shell`: Shell path (`/bin/bash` or `/bin/sh`)
- `motd`: Message of the day shown in TUI
- `ports`: Port mappings (optional)
- `environment`: Environment variables (optional)
- `volumes`: Volume mounts (named, bind, or file types)
- `scripts`: Lifecycle scripts (post_start, pre_stop)

**Groups System:**
Groups allow managing related containers as a unit. Defined in YAML configs using:
```yaml
group:
  name: dev-stack
  description: Development stack
  containers:
    - nginx-latest
    - postgres-16
    - redis-latest
```

### Docker Operations

**Key Concepts:**
- **Naming Convention**: All managed containers are prefixed with `playground-`
- **Labels**: Containers are labeled with `playground.managed=true` for filtering
- **Network**: All containers connect to `playground-network` (bridge driver)
- **Shared Volume**: `./shared-volumes` mounted as `/shared` in all containers
- **Volume Management**: Supports named volumes, bind mounts, and file mounts via `VolumeManager` class

**Docker Client Initialization:**
- CLI: `src/cli/core/docker_ops.py` - Uses `docker` Python library
- Web: `src/web/core/docker.py` - Uses `docker` Python library
- Standalone: Mounts `/var/run/docker.sock` for host Docker access

### Lifecycle Scripts

**Two-Stage Script Execution:**
1. **Default scripts** in `scripts/${CONTAINER_NAME}/playground-${CONTAINER_NAME}-${TYPE}.sh`
2. **Custom scripts** defined in YAML config (inline or external)

Script types:
- `init` (post_start): Runs after container starts
- `halt` (pre_stop): Runs before container stops (for backups/cleanup)

Both scripts execute if present, default first then custom.

### Web UI Architecture

**FastAPI Application** (`src/web/app.py`):
- Router-based API organization in `src/web/api/`
- Jinja2 templates in `src/web/templates/`
- Real-time terminal via WebSocket (`src/web/api/websocket.py`)
- State management in `src/web/core/state.py`

**Key API Endpoints:**
- `/` - Dashboard with container cards
- `/manage` - Advanced manager (bulk operations, groups)
- `/add-container` - Container creation wizard
- `/api/containers/*` - Container operations (start/stop/logs)
- `/api/groups/*` - Group management
- `/ws/{container_name}` - WebSocket terminal

### CLI Architecture

**Typer-Based Commands** (`src/cli/cli.py`):
- Command groups: `containers`, `groups`, `system`, `debug`
- Modular structure with separate command modules
- Rich library for formatted output
- Launcher script (`playground`) manages Python venv automatically

**Key Commands:**
```bash
playground list [--category] [--status] [--json]
playground start <container> [--force]
playground stop <container>
playground group start <group_name>
playground exec <container> [command]
playground ps [--all]
playground cleanup [--yes] [--images]
```

### Logging

**Location by Interface:**
- TUI: `playground.log`
- Web UI: `venv/web.log` (local) or container logs (Docker)
- CLI: `venv/cli.log`

## Development Workflow

### Testing Commands

```bash
# Test all interfaces in cascade
make test

# Test specific interface
make test-cli        # CLI tests only
make test-webui      # Web UI tests only
make test-all        # Comprehensive tests
```

### Running Interfaces

```bash
# TUI (Terminal UI)
./playground.sh

# CLI (Command Line)
./playground list
./playground start <container>

# Web UI (Local)
./start-webui.sh
# Opens on http://localhost:8000

# Docker (Standalone Container)
make docker-build
make docker-up
# Opens on http://localhost:8000
```

### Build and Deploy (Docker)

```bash
# Build image
make docker-build

# Tag with version
make docker-tag VERSION=1.2.3

# Push to registry
make docker-push VERSION=1.2.3

# View logs
make docker-logs
```

### Installation

```bash
# Install CLI globally
make install           # Creates symlink to /usr/local/bin/playground

# Uninstall
make uninstall

# Complete setup (dev environment + install + tests)
make setup
```

### Adding New Containers

Create `custom.d/my-container.yml`:
```yaml
images:
  my-app:
    image: "nginx:latest"
    category: "webserver"
    description: "My custom nginx"
    shell: "/bin/bash"
    keep_alive_cmd: "nginx -g 'daemon off;'"
    ports:
      - "8080:80"

    # Optional: Lifecycle scripts
    scripts:
      post_start:
        inline: |
          #!/bin/bash
          docker exec "playground-$1" apt-get update -qq

      pre_stop:
        inline: |
          #!/bin/bash
          mkdir -p "${SHARED_DIR}/data/backups"
```

Container appears immediately in all interfaces without restart.

## Code Organization

```
docker-compose-playground/
├── src/
│   ├── cli/                    # CLI implementation
│   │   ├── cli.py             # Main entry point (Typer app)
│   │   ├── commands/          # Command modules (containers, groups, system)
│   │   ├── core/              # Core logic (config, docker_ops, volumes, scripts)
│   │   └── utils/             # Utilities (display, scripts)
│   └── web/                   # Web UI implementation
│       ├── app.py             # FastAPI application
│       ├── api/               # API routers (containers, groups, websocket)
│       ├── core/              # Core logic (config, docker, state)
│       ├── templates/         # Jinja2 HTML templates
│       └── utils/             # Utilities (helpers, motd_processor)
├── config.d/                  # Pre-configured containers (100+ files)
├── custom.d/                  # User-defined containers (git-ignored)
├── scripts/                   # Container lifecycle scripts
├── shared-volumes/           # Shared volume mounted in containers
├── venv/                     # Python virtual environments
├── playground                # CLI launcher (manages venv)
├── playground.sh             # TUI script (whiptail)
├── start-webui.sh           # Web UI launcher
├── Dockerfile               # Docker image build
├── docker-compose-standalone.yml  # Standalone deployment
├── Makefile                 # Build/test commands
└── config.yml               # Base configuration
```

## Key Files to Modify

### Adding CLI Commands
- Edit `src/cli/commands/<module>.py` to add new command functions
- Register in `src/cli/cli.py` using `app.command(name="...")(function)`

### Adding Web API Endpoints
- Create router in `src/web/api/<module>.py`
- Register in `src/web/app.py` using `app.include_router(router)`

### Modifying Docker Operations
- CLI: `src/cli/core/docker_ops.py`
- Web: `src/web/core/docker.py`
- Both use the `docker` Python library

### Configuration Loading
- CLI: `src/cli/core/config.py`
- Web: `src/web/core/config.py`
- Both implement hierarchical YAML loading (config.yml → config.d → custom.d)

## Important Constraints

1. **Container Naming**: All managed containers MUST start with `playground-` prefix
2. **Network**: Containers MUST connect to `playground-network`
3. **Labels**: Containers MUST have label `playground.managed=true`
4. **Shared Volume**: Always mount `./shared-volumes` as `/shared`
5. **Configuration Priority**: custom.d > config.d > config.yml
6. **Script Execution Order**: Default scripts execute before custom scripts

## Troubleshooting Notes

### Docker Socket Access
When running in Docker, the container mounts `/var/run/docker.sock` for host Docker access. Ensure:
- Docker daemon is running on host
- Socket permissions allow container access
- Docker CLI is installed in container (see Dockerfile)

### Virtual Environment Issues
CLI and Web UI auto-create venvs. If corrupted:
```bash
make clean          # Remove all venvs
./playground list   # CLI auto-recreates
./start-webui.sh    # Web UI auto-recreates
```

### Port Conflicts
Default port 8000 may conflict. Check with:
```bash
sudo lsof -i :8000
```
Change port in `start-webui.sh` or `docker-compose-standalone.yml`.

## Dependencies

**Python Packages:**
- `typer>=0.12.5` - CLI framework
- `docker>=7.1.0` - Docker API client
- `pyyaml>=6.0.2` - YAML parsing
- `rich>=13.7.0` - CLI formatting
- `fastapi` - Web framework (Web UI only)
- `uvicorn` - ASGI server (Web UI only)
- `websockets` - WebSocket support (Web UI only)

**System Dependencies:**
- Docker (required)
- Python 3.8+ with `python3-venv`
- `yq` - YAML processor (auto-installed by TUI)
- `whiptail` - Terminal dialogs (TUI only)
