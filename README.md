# 🐳 Docker Playground Manager

A professional tool for managing multiple Docker development environments. Choose between TUI (Terminal), Web UI (Browser), or CLI (Command Line) interfaces.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Docker](https://img.shields.io/badge/docker-required-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)

<a href="https://www.buymeacoffee.com/manzolo">
  <img src=".github/blue-button.png" alt="Buy Me A Coffee" width="200">
</a>

## ✨ Features

- 🎯 **Three Interfaces** - TUI (whiptail), Web UI (browser), CLI (terminal)
- 📦 **100+ Pre-configured Images** - Linux, databases, programming languages, and more
- 📁 **Shared Volumes** - `/shared` directory mounted in all containers
- 🌐 **Network Isolation** - Dedicated Docker network for inter-container communication
- 📝 **MOTD System** - Helpful guides when entering containers
- 🔧 **Pre/Post Scripts** - Automatic initialization and backup scripts
- 🔍 **Smart Filtering** - Filter by name, category, or status
- 📊 **Real-time Console** - WebSocket-based terminal access (Web UI)
- ➕ **Add Containers** - Visual form to create new configurations (Web UI)
- 🧹 **Bulk Operations** - Stop all, cleanup, category management
- 🚀 **Container Groups** - Organize and manage related containers together (e.g., start/stop entire groups like a development stack)

## 📋 Requirements

- **Docker** - [Install Docker](https://docs.docker.com/engine/install/ubuntu/)
- **Python 3.8+** - With `python3-venv` for Web UI and CLI
- **yq** - YAML processor (auto-installed by TUI if missing)
- **whiptail** - For TUI (usually pre-installed)

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-venv
```

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/manzolo/docker-compose-playground.git
cd docker-compose-playground

# Choose your interface:

# 1. TUI (Terminal Interface)
chmod +x playground.sh
./playground.sh

# 2. Web UI (Browser Interface)
chmod +x start-webui.sh
./start-webui.sh
# Open http://localhost:8000

# 3. CLI (Command Line)
chmod +x playground install-cli.sh
./playground list
```

## 🖥️ Interface Comparison

| Feature | TUI | Web UI | CLI |
|---------|-----|--------|-----|
| Add containers | ❌ | ✅ | ❌ |
| JSON output | ❌ | ✅ | ✅ |
| Bulk operations | ✅ | ✅ | ✅ |
| Group management | ❌ | ✅ | ✅ |

## 📖 Usage

### TUI Commands
```bash
./playground.sh
# Navigate with arrow keys
# SPACE to select, ENTER to confirm
```
<img width="788" height="484" alt="image" src="https://github.com/user-attachments/assets/d341037f-d006-4d08-b432-0e91aad22dcf" />
<img width="940" height="476" alt="image" src="https://github.com/user-attachments/assets/2c28f6ee-5ea8-4d91-9a9c-d61ecdff92bb" />

Main menu:
- Start containers / Start by category / Start group
- Stop containers / Stop group / Enter container
- View logs / Container statistics
- Search images / Browse catalog
- Export logs / Cleanup

### Web UI
```bash
./start-webui.sh
# Open http://localhost:8000
```
<img width="1208" height="894" alt="image" src="https://github.com/user-attachments/assets/707da583-f005-49cf-a3df-a9e1c64fc60d" />
<img width="1208" height="894" alt="image" src="https://github.com/user-attachments/assets/2d8cefce-7e3c-4c4d-a66d-990d92450b5d" />
<img width="1883" height="852" alt="image" src="https://github.com/user-attachments/assets/a7e31b44-3fbb-4a0c-8069-2f5ca47ef886" />
<img width="1883" height="852" alt="image" src="https://github.com/user-attachments/assets/6af387f7-4f5e-462a-b907-8bf0ded13eb9" />

Features:
- **Dashboard** - Visual container cards with actions
- **Filters** - Search, category, status (All/Running/Stopped)
- **Console** - Interactive terminal via WebSocket
- **Add Container** - Step-by-step wizard to create configs
- **Advanced Manager** - Bulk operations, group management, system info, backups

### CLI Commands
```bash
# Container management
playground list [--category <cat>] [--status running|stopped] [--json]
playground start <container> [--force]
playground stop <container>
playground restart <container>
playground ps [--all]
playground group start <group_name>
playground group stop <group_name>
playground group restart <group_name>

# Interaction
playground logs <container> [--follow] [--tail N]
playground exec <container> [command]
playground info <container>

# Bulk operations
playground stop-all [--yes]
playground cleanup [--yes] [--images]
playground clean-images [--unused] [--yes]

# Utilities
playground categories
playground version
```

## 🗂️ Groups

Groups allow you to organize related containers (e.g., a web server, database, and cache for a development stack) and manage them as a single unit. You can start, stop, or restart all containers in a group with a single command, simplifying workflows for complex environments. Groups are defined in configuration files (`config.yml`, `config.d/`, or `custom.d/`) and are accessible via all interfaces (TUI, Web UI, CLI).

Example:
```yaml
group:
  name: dev-stack
  description: Development stack with web and database
  containers:
    - nginx-latest
    - postgres-latest
    - redis-latest
```

Start the group:
```bash
# CLI
playground group start dev-stack

# Web UI
Dashboard → Groups → dev-stack → Start
```

## ⚙️ Configuration

### Structure
```
docker-playground/
├── config.yml              # Shared configs
├── config.d/              # Base (100+ images) (Git-tracked)
│   ├── linux.yml
│   ├── database.yml
│   └── programming.yml
└── custom.d/              # User configs (Git-ignored)
    └── my-containers.yml
```

### Add Custom Container

Create `custom.d/my-app.yml`:
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
    environment:
      MY_VAR: "value"
    
    # Optional: MOTD for TUI
    motd: |
      ╔════════════════════════════╗
      ║     My App Quick Guide     ║
      ╚════════════════════════════╝
      
      🚀 Start: nginx -s reload
      📁 Config: /etc/nginx/
    
    # Optional: Scripts
    scripts:
      post_start:
        inline: |
          #!/bin/bash
          echo "Initializing..."
          docker exec "playground-$1" apt-get update -qq
      
      pre_stop:
        inline: |
          #!/bin/bash
          echo "Creating backup..."
          mkdir -p "${SHARED_DIR}/backups"
```

Container appears immediately in all interfaces.

### Configuration Options

| Option | Required | Description |
|--------|----------|-------------|
| `image` | ✅ | Docker image (e.g., `ubuntu:latest`) |
| `category` | ✅ | Category (linux, database, programming, etc.) |
| `description` | ✅ | Human-readable description |
| `shell` | ✅ | Shell path (`/bin/bash` or `/bin/sh`) |
| `keep_alive_cmd` | ✅ | Command to keep running |
| `motd` | ❌ | Message of the day (TUI only) |
| `ports` | ❌ | Port mappings (`["8080:80"]`) |
| `environment` | ❌ | Environment variables |
| `scripts.post_start` | ❌ | Initialization script |
| `scripts.pre_stop` | ❌ | Cleanup/backup script |

## 🔍 Examples

### Start Development Stack (CLI)
```bash
./playground group start PHP-MySQL-Stack
./playground ps
```

### Create Database Backup (any interface)
The `pre_stop` script in PostgreSQL config automatically creates backups when stopping:
```bash
# Backup created in: shared-volumes/backups/postgres-16/
```

### Access Container Shell
```bash
# CLI
./playground exec postgres-16

# TUI
./playground.sh → Enter a container → Select postgres-16

# Web UI
Dashboard → postgres card → Console button
```

### Filter and Start Category
```bash
# CLI
./playground list --category database
./playground start postgres-16

# Web UI
Dashboard → Category dropdown → database → Start
```

## 🛠️ Advanced

### Makefile Commands
```bash
make install          # Install CLI globally
make uninstall        # Remove CLI
make web             # Start web server
make test            # Run CLI tests
make clean           # Clean virtual environments
```

### Shared Volume
All containers mount `./shared-volumes` as `/shared`:
```bash
# From host
echo "test" > shared-volumes/file.txt

# From container
playground exec alpine "cat /shared/file.txt"
```

### Network Communication
Containers can communicate using their names:
```bash
# From nginx container
playground exec nginx "ping postgres-16"
playground exec nginx "curl http://redis:6379"
```

## 📝 Logging

- **TUI**: `playground.log`
- **Web UI**: `venv/web.log`
- **CLI**: Outputs to stdout/stderr

## 🛟 Troubleshooting

### Docker not running
```bash
sudo systemctl start docker
sudo systemctl enable docker
```

### Permission denied
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### CLI: venv issues
```bash
rm -rf venv/environments venv/.cli_venv_ready
./playground list  # Rebuilds automatically
```

### Web UI: Port already in use
```bash
# Check what's using port 8000
sudo lsof -i :8000
# Kill process or change port in start-webui.sh
```

### Container won't start
```bash
# Check if image exists
docker pull <image-name>

# View logs
playground logs <container>  # CLI
./playground.sh → View logs  # TUI
Dashboard → Logs button      # Web UI
```

## 🤝 Contributing

Contributions welcome:
- Add container configurations in `config.d/`
- Improve Web UI (FastAPI, HTML/CSS/JS)
- Enhance CLI (Python/Typer)
- Fix bugs or add features
- Improve documentation

```bash
# Test your changes
./playground.sh        # TUI
./playground           # CLI
./start-webui.sh       # Web UI
make test              # CLI tests
```

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](https://opensource.org/licenses/MIT) file for details.

**Attribution Requirement:** If you use this project, please include:
- A link to the original repository
- Credit to the original author (Manzolo - Andrea Manzi)
- Mention of the MIT License

---

## 🤖 Shout-out to the AI Crew

Massive thanks to the squad of virtual minds who contributed ideas, code snippets, and robotic encouragement:

> **Grok, DeepSeek, Gemini, Claude, ChatGPT** - Thanks for lending your (metaphorical) neurons to this project. With your combined computational power and 16 virtual hands, we've turned chaos into a working container! More or less.

**Disclaimer:** No LLMs were harmed during development. Maybe just a little confused.

**Made with ❤️ for developers**

*Happy containerizing! 🐳*
