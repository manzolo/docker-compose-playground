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

## 📋 Requirements

- **Docker** - [Install Docker](https://docs.docker.com/engine/install/ubuntu/)
- **Python 3.8+** - With `python3-venv` for Web UI and CLI
- **yq** - YAML processor (auto-installed by TUI if missing)
- **whiptail** - For TUI (usually pre-installed)

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io python3 python3-venv

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
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
chmod +x start-web.sh
./start-web.sh
# Open http://localhost:8000

# 3. CLI (Command Line)
chmod +x playground install-cli.sh
make install  # or ./install-cli.sh
playground list
```

## 🖥️ Interface Comparison

| Feature | TUI | Web UI | CLI |
|---------|-----|--------|-----|
| Interactive menus | ✅ | ✅ | ❌ |
| Remote access | ❌ | ✅ | ❌ |
| Scriptable | ❌ | ❌ | ✅ |
| Real-time console | ✅ | ✅ | ✅ |
| Add containers | ❌ | ✅ | ❌ |
| JSON output | ❌ | ✅ | ✅ |
| Bulk operations | ✅ | ✅ | ✅ |

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
- Start containers / Start by category
- Stop containers / Enter container
- View logs / Container statistics
- Search images / Browse catalog
- Export logs / Cleanup

### Web UI
```bash
./start-web.sh
# Open http://localhost:8000
```
<img width="1883" height="592" alt="image" src="https://github.com/user-attachments/assets/712a5e7a-ad92-4c30-b6dd-e9a472c819bb" />
<img width="1883" height="852" alt="image" src="https://github.com/user-attachments/assets/a7e31b44-3fbb-4a0c-8069-2f5ca47ef886" />
<img width="1883" height="852" alt="image" src="https://github.com/user-attachments/assets/6af387f7-4f5e-462a-b907-8bf0ded13eb9" />

Features:
- **Dashboard** - Visual container cards with actions
- **Filters** - Search, category, status (All/Running/Stopped)
- **Console** - Interactive terminal via WebSocket
- **Add Container** - Step-by-step wizard to create configs
- **Advanced Manager** - Bulk operations, system info, backups

### CLI Commands
```bash
# Container management
playground list [--category <cat>] [--status running|stopped] [--json]
playground start <container> [--force]
playground stop <container>
playground restart <container>
playground ps [--all]

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

## ⚙️ Configuration

### Structure
```
docker-playground/
├── config.yml              # Base (100+ images)
├── config.d/              # Shared configs (Git-tracked)
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
playground start postgres-latest
playground start redis-latest
playground start nginx-latest
playground ps
```

### Create Database Backup (any interface)
The `pre_stop` script in PostgreSQL config automatically creates backups when stopping:
```bash
# Backup created in: shared-volumes/backups/postgres/
```

### Access Container Shell
```bash
# CLI
playground exec postgres

# TUI
./playground.sh → Enter a container → Select postgres

# Web UI
Dashboard → postgres card → Console button
```

### Filter and Start Category
```bash
# CLI
playground list --category database
playground start postgres

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
playground exec nginx "ping postgres"
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
# Kill process or change port in start-web.sh
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
./start-web.sh         # Web UI
make test              # CLI tests
```

## 📄 License

MIT License - see LICENSE file

---

**Made with ❤️ for developers**

*Happy containerizing! 🐳*
