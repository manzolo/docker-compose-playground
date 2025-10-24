# 🐳 Docker Playground Manager

A professional tool for managing multiple Docker development environments. Choose between TUI (Terminal), Web UI (Browser), CLI (Command Line), or a standalone Docker container.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Docker](https://img.shields.io/badge/docker-required-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)

<a href="https://www.buymeacoffee.com/manzolo">
  <img src=".github/blue-button.png" alt="Buy Me A Coffee" width="200">
</a>

## ✨ Features

- 🎯 **Three Interfaces + Docker** - TUI (whiptail), Web UI (browser), CLI (terminal), or run as a standalone Docker container
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

## 📸 Screenshots

<details>
<summary>Click to view screenshots</summary>

<img width="1312" height="897" alt="immagine" src="https://github.com/user-attachments/assets/e4abe08f-14cc-4f43-944d-16a34996e6e7" />

<img width="1312" height="897" alt="immagine" src="https://github.com/user-attachments/assets/42dc7a5f-dfbb-4c40-a0bc-4ca7bc57d33c" />

<img width="1887" height="903" alt="immagine" src="https://github.com/user-attachments/assets/1de7a0c3-a63e-40e9-b6c9-6868a80ac6bc" />

<img width="1887" height="903" alt="immagine" src="https://github.com/user-attachments/assets/c7b078a5-fa1c-4005-b3eb-12278f733eff" />

<img width="1887" height="903" alt="immagine" src="https://github.com/user-attachments/assets/a02bd18c-54df-4ce0-8f55-25042621076e" />

<img width="1887" height="903" alt="immagine" src="https://github.com/user-attachments/assets/06105eca-0e84-49bd-b44f-1641565b6e4f" />


</details>

## 🗃️ Main Containers and Stacks

<details>
<summary>View the list of main containers and stacks</summary>

The Docker Playground Manager includes over 100 pre-configured containers and stacks, organized by category. Below is a curated list of the most commonly used ones:

### Linux Distributions
- **Ubuntu** (12, 14, 16, 18, 20, 22, 24, 24-fishell, 24-nushell, 24-tmux, 24-zsh, icewm, kde, mate, openbox, xfce)
- **Alpine** (3.19, 3.22, edge, tools)
- **Debian** (7, 8, 9, 10, 11, 12)
- **Fedora** (39)
- **Rocky Linux** (9)
- **Arch Linux** (arch, arch-nushell)
- **AlmaLinux** (9)
- **openSUSE** (leap)
- **Kali** (rolling)

### Databases
- **PostgreSQL** (15, 16, 17, alpine, latest)
- **MySQL** (5.7, 8)
- **MariaDB** (10, 11)
- **MongoDB** (6, 7)
- **Redis** (7, alpine, latest)
- **Cassandra**
- **CockroachDB**
- **Neo4j**
- **InfluxDB**

### Programming Languages
- **Python** (2.7, 3.9, 3.10, 3.11, 3.12, 3.13, alpine)
- **Node.js** (16, 18, 20, 22, alpine)
- **Bun**
- **Golang** (1.22, alpine)
- **Ruby** (3.3, alpine)
- **PHP** (5.6, 7.2, 7.4, 8.2, 8.3, fpm)
- **Java (OpenJDK)** (8, 11, 17, 21)
- **Rust** (1.75, alpine)
- **Elixir**
- **Erlang**
- **Haskell**
- **Kotlin**
- **Swift**
- **Perl**
- **Lua**
- **Clang**
- **GCC**

### Web Servers
- **Nginx** (latest, alpine)
- **Apache** (latest, alpine)
- **Caddy**
- **Traefik**

### Development Tools
- **Code Server** (browser-based VS Code)
- **Jupyter** (notebooks for Python, etc.)
- **Jenkins** (CI/CD)
- **Anaconda**
- **Miniconda**
- **Pytorch**
- **Tensorflow**
- **Gradle**
- **Maven**
- **Packer**
- **Ansible**
- **Deno**
- **Dotnet** (8)
- **Curl**
- **Busybox**
- **Docker DinD** (Docker in Docker)

### Stacks
- **PHP-MySQL** (PHP + MySQL + phpMyAdmin)
- **Wordpress** (WordPress + MySQL)
- **ELK** (Elasticsearch, Logstash, Kibana)
- **MinIO** (Object storage)
- **PostgreSQL-pgAdmin** (PostgreSQL + pgAdmin)
- **MySQL-phpMyAdmin** (MySQL + phpMyAdmin)
- **Mail Server Stack** (Postfix, Dovecot, Roundcube)
- **Node Express MongoDB** (Node.js + Express + MongoDB)
- **RabbitMQ Stack**
- **Redis Stack**
- **Selenium Stack**

### Other Services
- **RabbitMQ** (message broker)
- **ActiveMQ** (message broker)
- **Prometheus** (monitoring)
- **Grafana** (visualization)
- **Vault** (secrets management)
- **Consul** (service discovery)
- **Memcached** (caching)
- **Zipkin** (tracing)
- **Selenium** (Chrome, Firefox for testing)
- **Nextcloud** (file sharing)
- **CouchDB** (NoSQL)
- **Netshoot** (network troubleshooting)
- **Retro Terminal Games** (classic games)

This list covers key containers and stacks, but many more are available in `config.d/` and can be customized in `custom.d/`.

</details>

## 📋 Requirements

- **Docker** - [Install Docker](https://docs.docker.com/engine/install/ubuntu/)
- **Python 3.8+** - With `python3-venv` for Web UI and CLI (not needed for Docker deployment)
- **yq** - YAML processor (auto-installed by TUI if missing)
- **whiptail** - For TUI (usually pre-installed)

```bash
# Ubuntu/Debian (for local TUI/CLI/Web UI)
sudo apt-get update
sudo apt-get install python3 python3-venv
```

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/manzolo/docker-compose-playground.git
cd docker-compose-playground

# Choose your interface or deployment method:

# 1. Docker Compose (Recommended - Standalone Container)
make docker-build  # Build the Docker image
make docker-up     # Start the container
# Open http://localhost:8000 for Web UI

# 2. TUI (Terminal Interface)
chmod +x playground.sh
./playground.sh

# 3. Web UI (Browser Interface - Local)
chmod +x start-webui.sh
./start-webui.sh
# Open http://localhost:8000

# 4. CLI (Command Line)
chmod +x playground install-cli.sh
./playground list
```

## 🐳 Docker Compose Setup

Run Docker Playground Manager as a standalone container using `docker-compose-standalone.yml`, similar to tools like Portainer. This method packages the application and its dependencies into a Docker image, allowing easy deployment with access to the host's Docker socket and custom configurations.

### Prerequisites
- **Docker** and **Docker Compose** installed ([Install Docker](https://docs.docker.com/engine/install/ubuntu/))
- Directory for custom configurations and shared volumes (e.g., `/home/user/playground/custom.d` and `/home/user/playground/shared-volumes`)

### Setup Instructions
1. **Update Volume Paths**  
   Edit `docker-compose-standalone.yml` to set the correct paths for `custom.d` and `shared-volumes`:
   ```yaml
   volumes:
     - /var/run/docker.sock:/var/run/docker.sock
     - /home/user/playground/custom.d:/app/custom.d
     - /home/user/playground/shared-volumes:/app/shared-volumes
   ```
   Create these directories on the host:
   ```bash
   mkdir -p /home/user/playground/custom.d /home/user/playground/shared-volumes
   ```

2. **Build and Run**  
   Use the provided `Makefile` commands:
   ```bash
   make docker-build  # Build the Docker image
   make docker-up     # Start the container
   ```
   The Web UI will be available at `http://localhost:8000`.

3. **Manage the Container**  
   - View logs: `make docker-logs`
   - Stop and remove: `make docker-down`
   - Run CLI commands inside the container:
     ```bash
     docker exec docker-compose-playground /app/playground list
     ```

### Troubleshooting Docker Setup
- **"Missing dependencies: docker" Error**  
  If you see this error in the logs (`make docker-logs`), the Docker CLI may not be installed or cannot access the Docker daemon:
  - Verify Docker CLI is installed in the container:
    ```bash
    docker exec docker-compose-playground docker --version
    ```
    If it fails, rebuild the image with `make docker-build`.
  - Check Docker socket permissions:
    ```bash
    ls -l /var/run/docker.sock
    sudo usermod -aG docker $USER
    newgrp docker
    ```
  - Ensure the Docker daemon is running:
    ```bash
    sudo systemctl start docker
    sudo systemctl enable docker
    ```

- **Container Fails to Start**  
  Check logs with `make docker-logs` for details. Common issues:
  - Missing Python dependencies: Ensure `requirements.txt` includes all necessary packages (e.g., `fastapi`, `uvicorn`, `pyyaml`).
  - Port conflict: Check if port 8000 is in use:
    ```bash
    sudo lsof -i :8000
    ```
    Change the port in `docker-compose-standalone.yml` if needed (e.g., `8001:8000`).

### Notes
- The container mounts the host's Docker socket (`/var/run/docker.sock`) to manage Docker containers, similar to Portainer. This grants full control over the host, so use with caution.
- Custom configurations in `custom.d/` and data in `shared-volumes/` persist on the host.
- The `.dockerignore` file ensures a lean image by excluding unnecessary files like `venv/`.
- For advanced configuration, refer to the `docker-compose-standalone.yml`, `Dockerfile`, and `.dockerignore` in the repository root.

## 🖥️ Interface Comparison

| Feature | TUI | Web UI | CLI | Docker |
|---------|-----|--------|-----|--------|
| Add containers | ❌ | ✅ | ❌ | ✅ |
| JSON output | ❌ | ✅ | ✅ | ✅ |
| Bulk operations | ✅ | ✅ | ✅ | ✅ |
| Group management | ❌ | ✅ | ✅ | ✅ |

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
# Local
./start-webui.sh
# Docker
make docker-up
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

Groups allow you to organize related containers (e.g., a web server, database, and cache for a development stack) and manage them as a single unit. You can start, stop, or restart all containers in a group with a single command, simplifying workflows for complex environments. Groups are defined in configuration files (`config.yml`, `config.d/`, or `custom.d/`) and are accessible via all interfaces (TUI, Web UI, CLI, Docker).

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
# CLI (Local or Docker)
playground group start dev-stack
# Docker
docker exec docker-compose-playground /app/playground group start dev-stack

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
# Local
./playground group start PHP-MySQL-Stack
./playground ps
# Docker
docker exec docker-compose-playground /app/playground group start PHP-MySQL-Stack
```

### Create Database Backup (any interface)
The `pre_stop` script in PostgreSQL config automatically creates backups when stopping:
```bash
# Backup created in: shared-volumes/backups/postgres-16/
```

### Access Container Shell
```bash
# CLI (Local)
./playground exec postgres-16
# CLI (Docker)
docker exec -it docker-compose-playground /app/playground exec postgres-16

# TUI
./playground.sh → Enter a container → Select postgres-16

# Web UI
Dashboard → postgres card → Console button
```

### Filter and Start Category
```bash
# CLI (Local or Docker)
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
make docker-build     # Build Docker image using docker-compose
make docker-up        # Start Docker container
make docker-down      # Stop and remove Docker container
make docker-logs      # View container logs
make web              # Start web server (local)
make test             # Run CLI tests
make clean            # Clean virtual environments
make setup            # Complete setup (CLI + Docker + tests)
```

### Shared Volume
All containers mount `./shared-volumes` as `/shared`:
```bash
# From host
echo "test" > shared-volumes/file.txt

# From container
playground exec alpine "cat /shared/file.txt"
# Docker
docker exec docker-compose-playground /app/playground exec alpine "cat /shared/file.txt"
```

### Network Communication
Containers can communicate using their names:
```bash
# From nginx container
playground exec nginx "ping postgres-16"
playground exec nginx "curl http://redis:6379"
# Docker
docker exec docker-compose-playground /app/playground exec nginx "ping postgres-16"
```

## 📝 Logging

- **TUI**: `playground.log`
- **Web UI**: `venv/web.log` (local) or container logs (`make docker-logs`)
- **CLI**: Outputs to stdout/stderr

## 🛟 Troubleshooting

### Docker Not Running
```bash
sudo systemctl start docker
sudo systemctl enable docker
```

### Permission Denied
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### CLI: Venv Issues
```bash
rm -rf venv/environments venv/.cli_venv_ready
./playground list  # Rebuilds automatically
```

### Web UI: Port Already in Use
```bash
# Check what's using port 8000
sudo lsof -i :8000
# Kill process or change port in start-webui.sh or docker-compose-standalone.yml
```

### Container Won't Start
```bash
# Check if image exists
docker pull <image-name>

# View logs
playground logs <container>  # CLI
./playground.sh → View logs  # TUI
Dashboard → Logs button      # Web UI
make docker-logs             # Docker
```

### Docker-Specific Issues
- **"Missing dependencies: docker" Error**  
  If you see this error in the logs (`make docker-logs`), the Docker CLI may not be installed or cannot access the Docker daemon:
  - Verify Docker CLI is installed in the container:
    ```bash
    docker exec docker-compose-playground docker --version
    ```
    If it fails, rebuild the image with `make docker-build`.
  - Check Docker socket permissions:
    ```bash
    ls -l /var/run/docker.sock
    sudo usermod -aG docker $USER
    newgrp docker
    ```
  - Ensure the Docker daemon is running:
    ```bash
    sudo systemctl start docker
    sudo systemctl enable docker
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
make docker-up         # Docker
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
