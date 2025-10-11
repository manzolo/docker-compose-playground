# 🐳 Docker Playground Manager v3.0

A professional, modular, feature-rich interactive tool for managing multiple Docker development environments with ease. Perfect for developers who need to quickly spin up containers for testing, development, learning, or experimenting with different technologies.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Shell Script](https://img.shields.io/badge/shell-bash-green.svg)
![Docker](https://img.shields.io/badge/docker-required-blue.svg)
![Version](https://img.shields.io/badge/version-3.0-orange.svg)

## ✨ Features

<img width="788" height="484" alt="image" src="https://github.com/user-attachments/assets/d341037f-d006-4d08-b432-0e91aad22dcf" />
<img width="940" height="476" alt="image" src="https://github.com/user-attachments/assets/2c28f6ee-5ea8-4d91-9a9c-d61ecdff92bb" />


### Core Features
- 🎯 **Interactive TUI** - Beautiful terminal user interface using whiptail
- 📦 **100+ Pre-configured Images** - Linux distros, programming languages, databases, and more
- 🔄 **Smart Management** - Start, stop, enter, and monitor containers with ease
- 📁 **Shared Volumes** - Automatically mounted shared directory across all containers
- 🌐 **Network Isolation** - Containers communicate through a dedicated Docker network
- 🏷️ **Docker Labels** - Container tracking without filesystem dependencies

### 🎉 New in v3.0 - Major Architecture Overhaul!

#### 🏗️ Modular Architecture
- **Clean code structure** - Organized into separate modules (`lib/`)
- **Easy maintenance** - Each module handles specific functionality
- **Extensible design** - Add new features without touching core code
- **Professional organization** - Follows best practices for large bash projects

#### 📝 Inline MOTD System
- **YAML-based MOTDs** - Define help text directly in `config.yml`
- **File-based MOTDs** - Support for external `.txt` files in `motd/`
- **Context-aware** - Automatic detection and display when entering containers
- **Always visible** - MOTD stays on screen like real system login messages (no more disappearing!)
- **10+ pre-built guides** - MySQL, PostgreSQL, MongoDB, Redis, Python, Node.js, Go, Rust, Nginx, Docker-in-Docker

#### 🔧 Pre/Post Script System
- **post_start scripts** - Execute custom scripts after container starts (auto-install packages, initialize DBs, etc.)
- **pre_stop scripts** - Run cleanup or backup before stopping containers
- **Auto-discovery** - Scripts defined in `config.yml`, stored in `scripts/`
- **Built-in examples** - MySQL/PostgreSQL initialization, Python/Node package installation, automatic backups
- **Easy to extend** - Add your own custom scripts for any container

#### 📊 Enhanced Features
- 🔍 **Debug mode** - Built-in configuration debugging tool to troubleshoot issues
- 📈 **Better statistics** - Real-time container resource monitoring with auto-refresh
- 🎨 **Improved UI** - Color-coded sections, cleaner layout, better organization
- 🔄 **Restart containers** - Easily restart running containers without manual stop/start
- 📤 **Export logs** - Timestamped log exports for debugging and auditing
- 🔎 **Smart filtering** - Only show relevant containers (stoppable when running, startable when stopped)

## 📋 Requirements

- **Docker** (version 20.10 or higher)
- **Docker Compose** (version 2.0 or higher)
- **yq** (YAML processor - auto-installed via snap if missing)
- **whiptail** (usually pre-installed on most Linux distributions)
- **Bash** (version 4.0 or higher)

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/manzolo/docker-compose-playground.git
cd docker-compose-playground

# Make the script executable
chmod +x playground.sh

# Generate example scripts (optional but recommended)
chmod +x create_scripts.sh
./create_scripts.sh

# Run the playground
./playground.sh
```

### First Run

1. The script will check for dependencies and offer to install missing ones
2. Navigate the menu using arrow keys
3. Select "Start containers" or "Start by category"
4. Choose one or more images from the catalog (SPACE to select, ENTER to confirm)
5. Use "Enter a container" to access an interactive shell
6. **NEW!** See helpful MOTD guides for supported containers (MySQL, Postgres, Python, etc.)
7. **NEW!** Post-start scripts initialize your environment automatically (e.g., pip packages for Python)

## 🏗️ Project Structure

```
docker-playground/
├── playground.sh              # Main entry point
├── config.yml                # 100+ images configuration with MOTD and scripts
├── create_scripts.sh         # Helper to generate example scripts
├── lib/                      # Modular library files
│   ├── config.sh            # Configuration management (yq parsing)
│   ├── docker.sh            # Docker operations (start/stop/enter)
│   ├── logging.sh           # Logging utilities with colors
│   ├── motd.sh              # MOTD management (inline + file-based)
│   ├── ui.sh                # User interface (whiptail menus)
│   └── utils.sh             # Utility functions (dependencies, init)
├── scripts/                  # Pre/Post execution scripts
│   ├── mysql_init.sh        # MySQL initialization (creates test table)
│   ├── postgres_init.sh     # PostgreSQL setup (creates test table)
│   ├── postgres_backup.sh   # PostgreSQL automatic backup
│   ├── python_init.sh       # Python packages (requests, pandas, numpy)
│   ├── node_init.sh         # Node.js packages (express, axios)
│   └── generic_backup.sh    # Generic backup script for any container
├── motd/                     # Message of the Day files (legacy support)
│   ├── mysql.txt
│   ├── postgres.txt
│   ├── python.txt
│   ├── node.txt
│   ├── golang.txt
│   ├── rust.txt
│   ├── nginx.txt
│   ├── docker.txt
│   ├── redis.txt
│   ├── mongodb.txt
│   └── elasticsearch.txt
├── shared-volumes/           # Shared data directory (mounted at /shared)
│   ├── backups/             # Auto-created by backup scripts
│   └── README.txt           # Instructions for shared volume
└── playground.log            # Activity log with timestamps
```

## 🎮 Usage

### Main Menu Categories

#### 🚀 Container Management
- **Start containers** - Launch one or more container instances from all categories
- **Start by category** - Filter and start containers from a specific category (10+ categories)
- **Stop containers** - Stop running containers (only shows running containers)
- **Enter a container** - Open an interactive shell with automatic MOTD display

#### 📊 Monitoring
- **List active containers** - View all running playground containers with image info
- **View container logs** - Stream real-time logs (Ctrl+C to exit gracefully)
- **Restart container** - **NEW!** Restart a specific container (runs pre-stop + post-start scripts)
- **Container statistics** - **NEW!** Monitor CPU, memory, network I/O with auto-refresh
- **Dashboard** - Visual overview with statistics, running containers, and category breakdown

#### 🔧 Tools
- **Search images** - Quick search by name or description (fuzzy matching)
- **Browse catalog** - Explore all 100+ available images organized by category
- **System information** - Display Docker version, disk usage, network info
- **Help** - Comprehensive usage guide with examples
- **Debug config** - **NEW!** Troubleshoot configuration issues (shows parsed YAML, scripts, MOTDs)

#### 🛠️ Maintenance
- **Export logs** - Save activity logs with timestamp for auditing
- **Cleanup (remove all)** - Stop and remove ALL playground containers (with confirmation)
- **Exit** - Close the playground manager

### Shared Volume

All containers have access to a shared directory:

- **Host path**: `./shared-volumes`
- **Container path**: `/shared`

Use this to:
- Exchange files between containers
- Test scripts across different environments
- Share configuration files
- Store backups (automatically created by pre-stop scripts in `/shared/backups`)
- Persist data across container restarts

## 📚 MOTD (Message of the Day) System

When entering containers, you'll see helpful quick reference guides that **stay visible** on your terminal (just like real SSH logins!).

### Supported Containers with Inline MOTD (in config.yml)

- **MySQL 8.0** - Connection info, backup/restore, common queries, quick test examples
- **PostgreSQL 16** - psql commands, pg_dump/restore, useful queries, table examples
- **MongoDB 7** - mongosh basics, backup/restore, CRUD operations, aggregation
- **Redis 7** - redis-cli commands, data types (strings, lists, hashes), persistence
- **Python 3.13** - pip usage, quick testing, web servers, virtual environments
- **Node.js 22** - npm commands, Express setup, package management, quick scripts
- **Go 1.22** - go commands, module management, building, testing, HTTP server
- **Rust 1.75** - cargo commands, building, testing, formatting, dependencies
- **Docker-in-Docker** - Docker commands, image building, networking, volumes
- **Nginx** - Configuration, site setup, log viewing, reload commands
- **Ubuntu 24.04** - apt commands, system info utilities
- **Alpine Linux 3.19** - apk package manager, musl libc notes

### Supported Containers with File-based MOTD (in motd/ directory)

All the above plus legacy support for external `.txt` files.

### MOTD Example

When you enter MySQL, you'll see:
```
╔══════════════════════════════════════════════════════════════╗
║                    MySQL 8.0 Quick Reference                  ║
╚══════════════════════════════════════════════════════════════╝

🔐 Connection Info:
   Host: localhost / Container IP
   Port: 3306
   User: playground / root
   Password: playground
   Database: playground

📊 Basic Commands:
   mysql -u root -pplayground                    # Connect as root
   mysql -u playground -pplayground playground   # Connect to DB

📁 Database Operations:
   SHOW DATABASES;                               # List databases
   USE playground;                               # Switch database
   SHOW TABLES;                                  # List tables
   DESCRIBE tablename;                           # Table structure

💾 Quick Test:
   CREATE TABLE test (id INT, name VARCHAR(50));
   INSERT INTO test VALUES (1, 'Hello MySQL');
   SELECT * FROM test;

📝 Backup & Restore:
   mysqldump -u root -pplayground playground > /shared/backup.sql
   mysql -u root -pplayground playground < /shared/backup.sql

🔍 Useful Queries:
   SELECT USER(), DATABASE();                    # Current user/DB
   SHOW PROCESSLIST;                            # Active connections
   SHOW VARIABLES LIKE '%version%';             # MySQL version

╔════════════════════════════════════════════════════════╗
║  Entering container: playground-mysql-8
╚════════════════════════════════════════════════════════╝
Type 'exit' to return to the menu

bash-5.1# _
```

The MOTD **stays visible** so you can reference it while working!

## 🔧 Script System

### Post-Start Scripts (Automatic Initialization)

These scripts run automatically after a container starts:

**mysql_init.sh** (MySQL 8)
```bash
# Auto-executed after MySQL starts
# - Waits for MySQL to be ready
# - Creates a test table: playground_info
# - Inserts initialization message
```

**postgres_init.sh** (PostgreSQL 16)
```bash
# Auto-executed after PostgreSQL starts
# - Waits for PostgreSQL to be ready
# - Creates a test table: playground_info
# - Inserts initialization message
```

**python_init.sh** (Python 3.13, 3.12)
```bash
# Auto-executed after Python container starts
# - Upgrades pip to latest version
# - Installs: requests, beautifulsoup4, pandas, numpy
```

**node_init.sh** (Node.js 22, 20)
```bash
# Auto-executed after Node.js container starts
# - Initializes package.json in /shared if not exists
# - Installs: express, axios
```

### Pre-Stop Scripts (Cleanup & Backup)

These scripts run automatically before a container stops:

**postgres_backup.sh** (PostgreSQL 16)
```bash
# Auto-executed before PostgreSQL stops
# - Creates timestamped backup: postgres_YYYYMMDD_HHMMSS.sql
# - Saves to /shared/backups/
```

**generic_backup.sh** (MySQL 8, others)
```bash
# Auto-executed before container stops
# - Attempts to backup /data directory
# - Creates timestamped tar.gz: container_YYYYMMDD_HHMMSS.tar.gz
# - Saves to /shared/backups/
```

### Adding Custom Scripts

1. Create your script in `scripts/` directory:
```bash
#!/bin/bash
CONTAINER_NAME="$1"
echo "Running custom setup for $CONTAINER_NAME"
# Your commands here
```

2. Make it executable:
```bash
chmod +x scripts/my_custom_script.sh
```

3. Add to `config.yml`:
```yaml
  my-container:
    image: myimage:latest
    # ... other settings ...
    scripts:
      post_start: my_custom_script.sh
      pre_stop: my_cleanup_script.sh
```

4. Done! The script runs automatically when container starts/stops.

## 📦 Available Images (100+)

### Categories

#### 🐧 Linux Distributions (13)
Ubuntu (24.04, 22.04, 20.04), Debian (12, 11), Alpine (3.19, Edge), Fedora 39, Rocky Linux 9, AlmaLinux 9, Arch, openSUSE Leap, Kali Rolling

#### 💻 Programming Languages (42)
- **Python**: 3.13, 3.12, 3.11, 3.10, Alpine, Anaconda, Miniconda (with post-start package installation)
- **JavaScript/Node**: Node 22/20/18, Alpine, Deno, Bun (with post-start package installation)
- **JVM**: OpenJDK 21/17/11, Gradle, Maven, Kotlin, Scala
- **Compiled**: Go 1.22/Alpine, Rust 1.75/Alpine, GCC, Clang, Zig
- **Others**: PHP 8.3/8.2/FPM, Ruby 3.3/Alpine, Elixir, Erlang, Haskell, Swift, .NET 8, Lua, Perl

#### 🗄️ Databases (20)
- **SQL**: PostgreSQL 16/15/Alpine (with init scripts), MySQL 8/5.7 (with init scripts), MariaDB 11/10, CockroachDB
- **NoSQL**: MongoDB 7/6, Redis 7/Alpine, Memcached, Cassandra, CouchDB, Neo4j
- **Analytics**: Elasticsearch 8.11, InfluxDB

#### 🌐 Web Servers (7)
Nginx (Latest/Alpine), Apache (Latest/Alpine), Caddy, Traefik, HAProxy

#### 📨 Message Queues (4)
RabbitMQ (with management UI), Apache Kafka, NATS, ActiveMQ Classic

#### 🔧 DevOps & CI/CD (8)
Docker-in-Docker (privileged), Jenkins LTS, GitLab Runner, Ansible, Terraform, Packer, Vault (dev mode), Consul (dev mode)

#### 📊 Monitoring (4)
Prometheus, Grafana (admin:playground), Jaeger, Zipkin

#### 🤖 Machine Learning (3)
Jupyter Notebook (with JupyterLab), TensorFlow, PyTorch

#### 🛠️ Utilities (7)
BusyBox, Alpine Tools, curl, Ubuntu Full, Netshoot (network troubleshooting), Selenium Chrome, Selenium Firefox

## ⚙️ Configuration

### Basic Configuration

Edit `config.yml` to add or modify images:

```yaml
images:
  my-custom-image:
    image: custom/image:tag           # Docker image
    shell: /bin/bash                  # Shell to use
    keep_alive_cmd: sleep infinity    # Keep container running
    description: "My Custom Container"
    category: custom                  # For organization
    environment:                      # Optional: env vars
      MY_VAR: value
    ports:                           # Optional: port mappings
      - "8080:80"
    privileged: false                # Optional: privileged mode
```

### Advanced Configuration with MOTD and Scripts

```yaml
images:
  my-advanced-image:
    image: myimage:latest
    shell: /bin/bash
    keep_alive_cmd: sleep infinity
    description: "Advanced Container with MOTD and Scripts"
    category: custom
    
    # Inline MOTD (displayed when entering container)
    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  My Custom Quick Reference                    ║
      ╚══════════════════════════════════════════════════════════════╝
      
      🔧 Important Commands:
         myapp start                                   # Start service
         myapp status                                  # Check status
      
      📁 Important Paths:
         Config: /etc/myapp/config.yml
         Data: /var/lib/myapp/
    
    # Scripts (auto-executed)
    scripts:
      post_start: my_init_script.sh      # Runs after container starts
      pre_stop: my_cleanup_script.sh     # Runs before container stops
    
    environment:
      MY_VAR: "custom_value"
    
    ports:
      - "8080:80"
      - "8443:443"
```

### Configuration Options Reference

| Option | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| `image` | ✅ | string | Docker image name and tag | `ubuntu:24.04` |
| `shell` | ✅ | string | Shell to use when entering | `/bin/bash` or `/bin/sh` |
| `keep_alive_cmd` | ✅ | string | Command to keep container running | `sleep infinity` |
| `description` | ✅ | string | Human-readable description | `"Ubuntu 24.04 LTS"` |
| `category` | ✅ | string | Category for organization | `linux`, `programming`, `database` |
| `motd` | ❌ | multiline | Inline MOTD text (YAML block) | See examples above |
| `scripts.post_start` | ❌ | string | Script to run after start | `python_init.sh` |
| `scripts.pre_stop` | ❌ | string | Script to run before stop | `generic_backup.sh` |
| `environment` | ❌ | map | Environment variables | `{VAR: value}` |
| `ports` | ❌ | array | Port mappings | `["8080:80"]` |
| `privileged` | ❌ | boolean | Enable privileged mode | `true` or `false` |

## 🔍 Examples

### Example 1: Database Development with Automatic Initialization

```bash
# 1. Start PostgreSQL container
./playground.sh
# Select "Start by category" → "database" → postgres-16

# 2. Post-start script automatically:
#    - Waits for PostgreSQL to be ready
#    - Creates test table "playground_info"
#    - Inserts initialization message

# 3. Enter the container
# Select "Enter a container" → postgres-16
# You'll see the PostgreSQL MOTD with all commands!

# 4. Inside container, verify initialization
psql -U playground
\dt                                # See playground_info table
SELECT * FROM playground_info;     # See initialization message
\q

# 5. Create your own data
psql -U playground
CREATE TABLE users (id INT, name VARCHAR(50));
INSERT INTO users VALUES (1, 'Alice'), (2, 'Bob');
\q

# 6. Stop the container (automatic backup!)
# Select "Stop containers" → postgres-16
# Pre-stop script automatically creates backup in shared-volumes/backups/

# 7. Check your backup on host
ls -lh shared-volumes/backups/
# You'll see: postgres_postgres-16_20251011_235959.sql
```

### Example 2: Python Development with Auto-Installed Packages

```bash
# 1. Start Python container
./playground.sh
# Select "Start containers" → python-3.13

# 2. Post-start script automatically:
#    - Upgrades pip
#    - Installs requests, beautifulsoup4, pandas, numpy

# 3. Create a test script on host
cat > shared-volumes/test_pandas.py <<'EOF'
import pandas as pd
import numpy as np

data = pd.DataFrame({
    'name': ['Alice', 'Bob', 'Charlie'],
    'age': [25, 30, 35],
    'score': np.random.randint(60, 100, 3)
})

print(data)
data.to_csv('/shared/output.csv', index=False)
print("\nSaved to /shared/output.csv")
EOF

# 4. Enter container and run
# Select "Enter a container" → python-3.13
# You'll see Python MOTD with pip commands

python /shared/test_pandas.py

# 5. Check output on host
cat shared-volumes/output.csv
```

### Example 3: Full Stack Development Environment

```bash
# Setup a complete web development environment

# 1. Start backend (Node.js with auto-installed express)
# Select "Start by category" → "programming" → node-22

# 2. Start database (PostgreSQL with test table)
# Select "Start by category" → "database" → postgres-16

# 3. Start cache (Redis)
# Select "Start by category" → "database" → redis-7

# 4. Start web server (Nginx)
# Select "Start by category" → "webserver" → nginx-latest

# 5. Create Express app
cat > shared-volumes/server.js <<'EOF'
const express = require('express');
const app = express();

app.get('/', (req, res) => {
    res.json({ 
        message: 'Full stack playground!',
        services: ['node', 'postgres', 'redis', 'nginx']
    });
});

app.listen(3000, () => {
    console.log('Server running on port 3000');
});
EOF

# 6. Run in Node container
# Enter node-22 → node /shared/server.js

# Now you have a complete environment ready!
```

### Example 4: Using Debug Mode

```bash
# If something isn't working, use debug mode

./playground.sh
# Select "Debug config"

# You'll see:
# - Config file location
# - Total images found
# - Sample parsing of mysql-8:
#   * Image name
#   * Description
#   * Category
#   * Post-start script
#   * Pre-stop script
#   * MOTD length
# - This helps identify configuration issues!
```

### Example 5: Docker-in-Docker (Build Images Inside Container)

```bash
# 1. Start Docker-in-Docker
# Select "Start containers" → docker-dind

# 2. Create a Dockerfile in shared volume
cat > shared-volumes/Dockerfile <<'EOF'
FROM alpine:latest
RUN apk add --no-cache curl vim
CMD ["sh"]
EOF

# 3. Enter Docker-in-Docker container
# Select "Enter a container" → docker-dind
# You'll see Docker-in-Docker MOTD with commands!

# 4. Build and run your image
cd /shared
docker build -t myimage:latest .
docker run -it myimage:latest

# 5. Your custom image runs inside the playground container!
```

## 📝 Logging

All operations are logged to `playground.log` with detailed timestamps and context.

### Log Format

```
[2025-10-11 23:30:45] [INFO] Docker Playground Manager v3.0 starting...
[2025-10-11 23:30:45] [INFO] All dependencies check passed
[2025-10-11 23:30:45] [INFO] Environment initialized successfully
[2025-10-11 23:30:50] [INFO] Starting container: mysql-8
[2025-10-11 23:30:51] [SUCCESS] Started container: mysql-8
[2025-10-11 23:30:51] [INFO] Container mysql-8 is now running
[2025-10-11 23:30:51] [INFO] Running post-start script: mysql_init.sh
[2025-10-11 23:30:56] [INFO] Entering container: mysql-8
[2025-10-11 23:30:56] [INFO] MOTD length for mysql-8: 1278
[2025-10-11 23:30:56] [INFO] Showing inline MOTD for mysql-8
[2025-10-11 23:32:15] [INFO] Exited container: mysql-8
[2025-10-11 23:35:20] [INFO] Stopping container: mysql-8
[2025-10-11 23:35:20] [INFO] Running pre-stop script: generic_backup.sh
[2025-10-11 23:35:22] [SUCCESS] Stopped container: mysql-8
```

### Viewing Logs

```bash
# View recent logs
tail -50 playground.log

# Follow logs in real-time
tail -f playground.log

# Export logs with timestamp
# Use menu option "Export logs"
# Creates: playground-logs-YYYYMMDD-HHMMSS.txt
```

## 🛟 Troubleshooting

### Container won't start
```bash
# 1. Check if the image exists
docker pull 

# 2. Verify Docker daemon is running
docker ps

# 3. View logs from the menu
# Select "View container logs" → your-container

# 4. Check playground log
tail -50 playground.log

# 5. Use debug mode
# Select "Debug config" to verify configuration
```

### Post-start script not running
```bash
# 1. Check if script exists
ls -la scripts/

# 2. Verify script is executable
chmod +x scripts/*.sh

# 3. Check config.yml syntax
yq eval '.images."mysql-8".scripts.post_start' config.yml

# 4. View log for script execution
grep "post-start" playground.log

# 5. Test script manually
bash scripts/mysql_init.sh mysql-8
```

### MOTD not showing
```bash
# 1. Test MOTD retrieval
source lib/config.sh
export CONFIG_FILE="./config.yml"
get_image_motd "mysql-8" | head -5

# 2. Check config.yml indentation (YAML is strict!)
# MOTD must be indented correctly under the image

# 3. Look for errors in log
grep "MOTD" playground.log

# 4. Verify /dev/tty output (MOTD uses TTY)
# Should work in most terminals
```

### Port conflicts
```bash
# 1. Check what's using the port
sudo netstat -tlnp | grep 

# 2. Modify port mapping in config.yml
# Change "5432:5432" to "5433:5432"

# 3. Restart the container
```

### Permission denied on shared volume
```bash
# 1. Check permissions
ls -la shared-volumes/

# 2. Fix permissions
chmod -R 777 shared-volumes/

# 3. Create backup directory manually if needed
mkdir -p shared-volumes/backups
chmod 777 shared-volumes/backups
```

### yq not found
```bash
# Auto-install (recommended)
# Script will offer to install via snap

# Manual install
sudo snap install yq

# Verify installation
yq --version
```

### Container not visible after restart
```bash
# Containers use Docker labels for tracking
# Verify label exists
docker ps -a --filter "label=playground.managed=true"

# If missing, restart from menu
# The playground will recreate with correct labels
```

### Can't enter container (shell not found)
```bash
# 1. Check shell configuration in config.yml
yq eval '.images."your-container".shell' config.yml

# 2. Common shells: /bin/bash, /bin/sh
# Alpine uses /bin/sh, most others use /bin/bash

# 3. Fix in config.yml if needed
```

## 🎯 Best Practices

### Development Workflow
1. **Use categories** - Start containers by category to get complete environments (e.g., "database" for all DB tools)
2. **Read MOTDs** - Always check the MOTD for important connection info and commands
3. **Use shared volume** - Store all your work in `/shared` for persistence and easy access from host
4. **Leverage scripts** - Let post-start scripts handle initialization (no manual package installation!)
5. **Regular backups** - Pre-stop scripts handle backups automatically, but export important data manually too

### Container Management
1. **Start what you need** - Don't start all 100+ containers at once! Use category filtering
2. **Monitor resources** - Use Dashboard and Statistics to track CPU/memory usage
3. **Regular cleanup** - Stop unused containers to free resources
4. **Check logs** - If something fails, check container logs and playground.log
5. **Use restart** - Instead of stop/start, use the "Restart" option to preserve data

### Configuration
1. **Backup config** - Keep a copy of config.yml before major changes
2. **Test scripts** - Test custom scripts manually before adding to config.yml
3. **Validate YAML** - Use `yq eval '.' config.yml` to check syntax
4. **Document MOTDs** - Add helpful MOTDs to your custom containers
5. **Use debug mode** - When adding new containers, use "Debug config" to verify

### Shared Volume
1. **Organize files** - Create subdirectories in shared-volumes/ for different projects
2. **Check backups** - Periodically verify backups in shared-volumes/backups/
3. **Clean old files** - Remove old backups and test files to save space
4. **Use .gitignore** - Add shared-volumes/ to .gitignore (it's already there!)
5. **Share configs** - Store config files in /shared for reuse across containers

### Troubleshooting
1. **Start simple** - Test with basic containers (Ubuntu, Alpine) first
2. **Check logs** - Always check playground.log for detailed error messages
3. **Use debug** - The "Debug config" option shows parsed configuration
4. **One at a time** - When troubleshooting, start one container at a time
5. **Export logs** - Export logs before reporting issues

## 🤝 Contributing

Contributions are very welcome! This project benefits from community input.

### Areas for Contribution

- 📝 **More MOTDs** - Add inline MOTDs for containers that don't have them yet
- 🔧 **More scripts** - Create useful post-start/pre-stop scripts for common tasks
- 📦 **New images** - Add more pre-configured containers to the catalog
- 🎨 **UI improvements** - Enhance the whiptail interface with better layouts
- 🐛 **Bug fixes** - Fix issues and improve reliability
- 📖 **Documentation** - Improve README, add tutorials, create video guides
- 🧪 **Testing** - Test on different platforms and Docker versions
- 🌍 **Internationalization** - Translate MOTDs and UI to other languages
  
**Made with ❤️ for the developer community**

*Happy containerizing!
