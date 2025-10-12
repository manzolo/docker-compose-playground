# 🐳 Docker Playground Manager v3.0

A professional, modular, feature-rich interactive tool for managing multiple Docker development environments with ease. Perfect for developers who need to quickly spin up containers for testing, development, learning, or experimenting with different technologies.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Shell Script](https://img.shields.io/badge/shell-bash-green.svg)
![Docker](https://img.shields.io/badge/docker-required-blue.svg)
![Version](https://img.shields.io/badge/version-3.0-orange.svg)

## ✨ Features

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

#### 📂 Modular Configuration System
- **Split configuration files** - Keep your config organized with `config.d/` directory
- **Auto-merge on startup** - Base `config.yml` + all `config.d/*.yml` files merged automatically
- **Easy to extend** - Add new containers without touching the main config file
- **Validate independently** - Each config file can be validated separately
- **Share configurations** - Team members can add their own config files to `config.d/`

#### 📝 Inline MOTD System
- **YAML-based MOTDs** - Define help text directly in `config.yml` or `config.d/*.yml`
- **File-based MOTDs** - Support for external `.txt` files in `motd/` (legacy)
- **Context-aware** - Automatic detection and display when entering containers
- **Always visible** - MOTD stays on screen like real system login messages (no more disappearing!)
- **10+ pre-built guides** - MySQL, PostgreSQL, MongoDB, Redis, Python, Node.js, Go, Rust, Nginx, Docker-in-Docker

#### 🔧 Inline Pre/Post Script System
- **Inline scripts** - Define scripts directly in YAML configuration (no separate files needed!)
- **File-based scripts** - Support for external scripts in `scripts/` directory
- **post_start scripts** - Execute custom scripts after container starts (auto-install packages, initialize DBs, etc.)
- **pre_stop scripts** - Run cleanup or backup before stopping containers
- **Auto-discovery** - Scripts defined inline or referenced from `scripts/`
- **Built-in examples** - MySQL/PostgreSQL initialization, Python/Node package installation, automatic backups
- **Easy to extend** - Add your own custom scripts inline or as files

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


<img width="788" height="484" alt="image" src="https://github.com/user-attachments/assets/d341037f-d006-4d08-b432-0e91aad22dcf" />
<img width="940" height="476" alt="image" src="https://github.com/user-attachments/assets/2c28f6ee-5ea8-4d91-9a9c-d61ecdff92bb" />


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
├── config.yml                # Base configuration (100+ images)
├── config.d/                 # 🆕 Modular configuration directory
│   ├── ubuntu-24.yml        # Example: Ubuntu 24.04 with inline MOTD & scripts
│   ├── postgres-16.yml      # Example: PostgreSQL 16 with inline scripts
│   ├── mysql-8.yml          # Example: MySQL 8 with initialization
│   ├── python-3.13.yml      # Example: Python with auto-pip install
│   └── custom.yml           # Add your own custom containers here!
├── create_scripts.sh         # Helper to generate example scripts
├── lib/                      # Modular library files
│   ├── config.sh            # Configuration management (yq parsing)
│   ├── config_loader.sh     # 🆕 Config merging and validation
│   ├── docker.sh            # Docker operations (start/stop/enter)
│   ├── logging.sh           # Logging utilities with colors
│   ├── motd.sh              # MOTD management (inline + file-based)
│   ├── ui.sh                # User interface (whiptail menus)
│   └── utils.sh             # Utility functions (dependencies, init)
├── scripts/                  # Pre/Post execution scripts (optional)
│   ├── mysql_init.sh        # MySQL initialization (legacy)
│   ├── postgres_init.sh     # PostgreSQL setup (legacy)
│   ├── postgres_backup.sh   # PostgreSQL automatic backup (legacy)
│   ├── python_init.sh       # Python packages (legacy)
│   ├── node_init.sh         # Node.js packages (legacy)
│   └── generic_backup.sh    # Generic backup script
├── motd/                     # Message of the Day files (legacy support)
│   ├── mysql.txt
│   ├── postgres.txt
│   ├── python.txt
│   └── ...
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

### Supported Containers with Inline MOTD

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

## ⚙️ Configuration

### 🆕 Modular Configuration System

The v3.0 introduces a powerful modular configuration system that allows you to split your configuration into multiple files!

#### Directory Structure

```
docker-playground/
├── config.yml              # Base configuration (required)
└── config.d/               # Additional configurations (optional)
    ├── ubuntu-24.yml       # Example: Custom Ubuntu config
    ├── postgres-16.yml     # Example: PostgreSQL with inline scripts
    ├── mysql-8.yml         # Example: MySQL configuration
    └── my-custom.yml       # Your custom containers
```

#### How It Works

1. **Base Config**: `config.yml` contains 100+ pre-configured images
2. **Modular Configs**: Files in `config.d/*.yml` are automatically merged on startup
3. **Override Behavior**: Files in `config.d/` can override base configuration
4. **Validation**: Each file is validated independently before merging

#### Benefits

✅ **Organization** - Keep related containers together in separate files  
✅ **Team Collaboration** - Team members can add their own config files  
✅ **Easy Updates** - Update base config without touching custom configs  
✅ **Version Control** - Commit only your custom configs, ignore others  
✅ **No Conflicts** - Each file can be edited independently  

### Basic Configuration

Create a new file in `config.d/` directory:

```yaml
# config.d/my-custom-image.yml
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

### 🆕 Advanced Configuration with Inline MOTD and Scripts

This is the **new way** to configure containers in v3.0 - everything in one YAML file!

```yaml
# config.d/my-advanced-container.yml
images:
  my-advanced-image:
    image: myimage:latest
    shell: /bin/bash
    keep_alive_cmd: sleep infinity
    description: "Advanced Container with Inline MOTD and Scripts"
    category: custom
    
    # 🆕 Inline MOTD (displayed when entering container)
    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  My Custom Quick Reference                    ║
      ╚══════════════════════════════════════════════════════════════╝
      
      🔧 Important Commands:
         myapp start                                   # Start service
         myapp status                                  # Check status
         myapp logs                                    # View logs
      
      📁 Important Paths:
         Config: /etc/myapp/config.yml
         Data: /var/lib/myapp/
         Logs: /var/log/myapp/
      
      💡 Quick Tips:
         - Use /shared for persistent storage
         - Logs are automatically backed up on stop
         - Check /shared/backups/ for backups
    
    # 🆕 Inline Scripts (no separate files needed!)
    scripts:
      post_start:
        inline: |
          #!/bin/bash
          CONTAINER_NAME="$1"
          echo "🚀 Initializing $CONTAINER_NAME..."
          
          # Install dependencies
          docker exec "playground-$CONTAINER_NAME" apt-get update -qq
          docker exec "playground-$CONTAINER_NAME" apt-get install -y -qq curl wget
          
          # Create necessary directories
          docker exec "playground-$CONTAINER_NAME" mkdir -p /app/data
          
          # Initialize application
          docker exec "playground-$CONTAINER_NAME" sh -c "
            echo 'Container initialized at $(date)' > /app/initialized.txt
          "
          
          echo "✓ $CONTAINER_NAME initialized successfully"
      
      pre_stop:
        inline: |
          #!/bin/bash
          CONTAINER_NAME="$1"
          echo "💾 Creating backup for $CONTAINER_NAME..."
          
          # Create backup directory
          BACKUP_DIR="${SHARED_DIR:-./shared-volumes}/backups/my-advanced-image"
          mkdir -p "$BACKUP_DIR"
          
          TIMESTAMP=$(date +%Y%m%d_%H%M%S)
          
          # Backup application data
          docker exec "playground-$CONTAINER_NAME" tar czf - /app/data \
            > "$BACKUP_DIR/data_${TIMESTAMP}.tar.gz" 2>/dev/null
          
          # Backup logs
          docker exec "playground-$CONTAINER_NAME" tar czf - /var/log/myapp \
            > "$BACKUP_DIR/logs_${TIMESTAMP}.tar.gz" 2>/dev/null
          
          echo "✓ Backup saved to: backups/my-advanced-image/"
    
    environment:
      MY_VAR: "custom_value"
      DEBUG: "true"
    
    ports:
      - "8080:80"
      - "8443:443"
```

### 🆕 Real-World Example: PostgreSQL 16

Here's a complete real-world example from `config.d/postgres-16.yml`:

```yaml
# config.d/postgres-16.yml
images:
  postgres-16:
    image: postgres:16
    shell: /bin/bash
    keep_alive_cmd: postgres
    description: "PostgreSQL 16 (Latest)"
    category: database
    
    environment:
      POSTGRES_PASSWORD: playground
      POSTGRES_USER: playground
      POSTGRES_DB: playground
    
    ports:
      - "5432:5432"
    
    # Inline MOTD with PostgreSQL quick reference
    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                PostgreSQL 16 Quick Reference                  ║
      ╚══════════════════════════════════════════════════════════════╝
      
      🔐 Connection Info:
         Host: localhost / Container IP
         Port: 5432
         User: playground
         Password: playground
         Database: playground
      
      📊 Basic Commands:
         psql -U playground                            # Connect to PostgreSQL
         \l                                            # List databases
         \c database_name                              # Connect to database
         \dt                                           # List tables
         \d table_name                                 # Describe table
         \q                                            # Quit
      
      💾 Backup & Restore:
         pg_dump -U playground playground > /shared/backup.sql
         psql -U playground playground < /shared/backup.sql
      
      📝 Quick Table Example:
         CREATE TABLE users (
           id SERIAL PRIMARY KEY,
           name VARCHAR(100),
           email VARCHAR(100) UNIQUE,
           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
         );
         INSERT INTO users (name, email) VALUES ('Test', 'test@example.com');
         SELECT * FROM users;
    
    # Inline post-start script: Initialize PostgreSQL
    scripts:
      post_start:
        inline: |
          #!/bin/bash
          CONTAINER_NAME="$1"
          echo "🐘 Initializing PostgreSQL for $CONTAINER_NAME..."
          
          # Wait for PostgreSQL to be ready
          sleep 3
          
          # Create example table
          docker exec "playground-$CONTAINER_NAME" psql -U playground -d playground -c "
          CREATE TABLE IF NOT EXISTS playground_info (
              id SERIAL PRIMARY KEY,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              message TEXT
          );
          
          INSERT INTO playground_info (message) 
          VALUES ('PostgreSQL initialized by playground manager');
          " 2>/dev/null
          
          echo "✓ PostgreSQL initialized with test table"
      
      # Inline pre-stop script: Automatic backup
      pre_stop:
        inline: |
          #!/bin/bash
          CONTAINER_NAME="$1"
          echo "💾 Backing up PostgreSQL database from $CONTAINER_NAME..."
          
          # Create backup directory for this specific container
          BACKUP_DIR="${SHARED_DIR:-./shared-volumes}/backups/postgres-16"
          mkdir -p "$BACKUP_DIR"
          
          TIMESTAMP=$(date +%Y%m%d_%H%M%S)
          BACKUP_FILE="$BACKUP_DIR/postgres_${TIMESTAMP}.sql"
          
          # Create backup
          docker exec "playground-$CONTAINER_NAME" \
            pg_dump -U playground playground > "$BACKUP_FILE" 2>/dev/null
          
          if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
              echo "✓ Backup saved to: backups/postgres-16/postgres_${TIMESTAMP}.sql"
          else
              rm -f "$BACKUP_FILE"
              echo "✗ Backup failed"
          fi
```

### 🆕 Real-World Example: Ubuntu 24.04

Here's another complete example from `config.d/ubuntu-24.yml`:

```yaml
# config.d/ubuntu-24.yml
images:
  ubuntu-24:
    image: ubuntu:24.04
    shell: /bin/bash
    keep_alive_cmd: sleep infinity
    description: "Ubuntu 24.04 LTS (Noble Numbat) - Latest LTS"
    category: linux
    
    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                 Ubuntu 24.04 Quick Reference                  ║
      ╚══════════════════════════════════════════════════════════════╝
      
      📦 Package Management:
         apt update                                    # Update package list
         apt upgrade                                   # Upgrade packages
         apt install package_name                      # Install package
         apt search package_name                       # Search package
      
      🔧 System Info:
         lsb_release -a                                # Ubuntu version
         uname -a                                      # Kernel info
         df -h                                         # Disk usage
         free -h                                       # Memory usage
      
      🚀 Quick Setup:
         apt update && apt install -y vim curl git wget build-essential
    
    scripts:
      post_start:
        inline: |
          #!/bin/bash
          CONTAINER_NAME="$1"
          echo "🐧 Initializing Ubuntu 24.04 for $CONTAINER_NAME..."
          
          # Update package list
          docker exec "playground-$CONTAINER_NAME" apt-get update -qq 2>/dev/null
          
          # Install essential tools
          docker exec "playground-$CONTAINER_NAME" apt-get install -y -qq \
            vim curl wget git build-essential 2>/dev/null
          
          echo "✓ Ubuntu 24.04 initialized with essential tools"
      
      pre_stop:
        inline: |
          #!/bin/bash
          CONTAINER_NAME="$1"
          echo "💾 Backing up Ubuntu configuration for $CONTAINER_NAME..."
          
          BACKUP_DIR="${SHARED_DIR:-./shared-volumes}/backups/ubuntu-24"
          mkdir -p "$BACKUP_DIR"
          
          TIMESTAMP=$(date +%Y%m%d_%H%M%S)
          
          # Backup installed packages list
          docker exec "playground-$CONTAINER_NAME" dpkg --get-selections > \
            "$BACKUP_DIR/packages_${TIMESTAMP}.txt" 2>/dev/null
          
          echo "✓ Backup saved to: backups/ubuntu-24/"
```

### Configuration Options Reference

| Option | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| `image` | ✅ | string | Docker image name and tag | `ubuntu:24.04` |
| `shell` | ✅ | string | Shell to use when entering | `/bin/bash` or `/bin/sh` |
| `keep_alive_cmd` | ✅ | string | Command to keep container running | `sleep infinity` |
| `description` | ✅ | string | Human-readable description | `"Ubuntu 24.04 LTS"` |
| `category` | ✅ | string | Category for organization | `linux`, `programming`, `database` |
| `motd` | ❌ | multiline | 🆕 Inline MOTD text (YAML block) | See examples above |
| `scripts.post_start` | ❌ | string or object | Script file name or inline script | `python_init.sh` or `{inline: "#!/bin/bash..."}` |
| `scripts.pre_stop` | ❌ | string or object | Script file name or inline script | `generic_backup.sh` or `{inline: "#!/bin/bash..."}` |
| `environment` | ❌ | map | Environment variables | `{VAR: value}` |
| `ports` | ❌ | array | Port mappings | `["8080:80"]` |
| `privileged` | ❌ | boolean | Enable privileged mode | `true` or `false` |

### 🆕 Script Configuration: File vs Inline

You can configure scripts in two ways:

**Method 1: File-based (Legacy)**
```yaml
scripts:
  post_start: mysql_init.sh      # References scripts/mysql_init.sh
  pre_stop: generic_backup.sh    # References scripts/generic_backup.sh
```

**Method 2: Inline (New in v3.0)** ⭐ Recommended
```yaml
scripts:
  post_start:
    inline: |
      #!/bin/bash
      CONTAINER_NAME="$1"
      echo "Initializing..."
      # Your script here
  pre_stop:
    inline: |
      #!/bin/bash
      CONTAINER_NAME="$1"
      echo "Cleaning up..."
      # Your script here
```

**Benefits of Inline Scripts:**
- ✅ Everything in one file - easier to manage
- ✅ No need to create separate script files
- ✅ Better for version control (single file to track)
- ✅ Easier to share configurations
- ✅ Inline scripts are automatically made executable

## 🔍 Examples

### Example 1: Creating a Custom Container with Inline Config

Create a new file `config.d/my-python-ml.yml`:

```yaml
images:
  python-ml-custom:
    image: python:3.13
    shell: /bin/bash
    keep_alive_cmd: sleep infinity
    description: "Python 3.13 with ML Libraries"
    category: programming
    
    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║              Python ML Environment Ready!                     ║
      ╚══════════════════════════════════════════════════════════════╝
      
      📊 Installed Libraries:
         - TensorFlow, PyTorch
         - scikit-learn, pandas, numpy
         - matplotlib, seaborn
      
      🚀 Quick Start:
         python /shared/your_script.py
         jupyter notebook --ip=0.0.0.0 --allow-root
    
    scripts:
      post_start:
        inline: |
          #!/bin/bash
          CONTAINER_NAME="$1"
          echo "🤖 Installing ML libraries..."
          
          docker exec "playground-$CONTAINER_NAME" pip install --quiet \
            tensorflow pytorch scikit-learn pandas numpy \
            matplotlib seaborn jupyter
          
          echo "✓ ML environment ready!"
    
    ports:
      - "8888:8888"
```

Now run: `./playground.sh` → "Start containers" → "python-ml-custom"

### Example 2: Override Base Configuration

Create `config.d/postgres-custom.yml` to override base postgres-16:

```yaml
images:
  postgres-16:
    # This will merge with base postgres-16 config
    environment:
      POSTGRES_PASSWORD: my_secure_password  # Override password
      POSTGRES_DB: my_database               # Override database name
    
    ports:
      - "5433:5432"  # Use different host port
```

### Example 3: Team Collaboration

Each team member can have their own config file:

```yaml
# config.d/john-dev-env.yml
images:
  john-workspace:
    image: ubuntu:24.04
    shell: /bin/bash
    keep_alive_cmd: sleep infinity
    description: "John's Development Workspace"
    category: custom
    
    scripts:
      post_start:
        inline: |
          #!/bin/bash
          CONTAINER_NAME="$1"
          
          # Install John's preferred tools
          docker exec "playground-$CONTAINER_NAME" apt-get update -qq
          docker exec "playground-$CONTAINER_NAME" apt-get install -y -qq \
            vim tmux zsh git nodejs npm python3
          
          # Setup John's dotfiles
          docker exec "playground-$CONTAINER_NAME" sh -c "
            git clone https://github.com/john/dotfiles /root/dotfiles
            cd /root/dotfiles && ./install.sh
          "
```

## 📝 Logging

All operations are logged to `playground.log` with detailed timestamps and context.

### Log Format

```
[2025-10-12 11:01:14] [INFO] Docker Playground Manager v3.0 starting...
[2025-10-12 11:01:14] [INFO] Merging configuration files...
[2025-10-12 11:01:14] [INFO] Merging: ubuntu-24.yml
[2025-10-12 11:01:14] [SUCCESS]   ✓ Merged: ubuntu-24.yml
[2025-10-12 11:01:14] [INFO] Merging: postgres-16.yml
[2025-10-12 11:01:14] [SUCCESS]   ✓ Merged: postgres-16.yml
[2025-10-12 11:01:15] [SUCCESS] Merged base config + 12 files = 103 total images
```

## 🛟 Troubleshooting

### Config file not merging

```bash
# Check if config.d/ exists
ls -la config.d/

# Validate individual config files
yq eval '.' config.d/ubuntu-24.yml

# Use debug mode
./playground.sh → "Debug config"
```

### Container not visible in menu

```bash
# Check if container is already running
docker ps --filter "label=playground.managed=true"

# Containers already running won't appear in "Start" menu
# Use "List active containers" or "Stop containers" first
```

### Inline script not executing

```bash
# Check log for script execution
grep "post-start\|pre-stop" playground.log

# Verify script syntax in config file
yq eval '.images."your-container".scripts.post_start.inline' config.d/your-file.yml

# Test script manually (extract to temp file and run)
```

## 🎯 Best Practices

### Configuration Management

1. **Use config.d/** - Keep custom configs separate from base config.yml
2. **One container per file** - Makes it easier to manage and share
3. **Use inline scripts** - Keep everything in one YAML file for better organization
4. **Version control** - Commit your `config.d/*.yml` files
5. **Validate before commit** - Use `yq eval '.' config.d/yourfile.yml` to check syntax

### Modular Configuration Tips

1. **Naming convention** - Use descriptive names: `postgres-16.yml`, `python-ml.yml`
2. **Category organization** - Group related containers in same file if needed
3. **Document inline scripts** - Add comments in your bash scripts
4. **Test incrementally** - Test each new config file separately
5. **Share with team** - Team members can add their own config files without conflicts

## 🤝 Contributing

Contributions are very welcome! This project benefits from community input.

### Areas for Contribution

- 📝 **More inline configs** - Add complete container configs in `config.d/`
- 🔧 **More inline scripts** - Create useful initialization and backup scripts
- 📦 **New images** - Add more pre-configured containers to the catalog
- 🎨 **UI improvements** - Enhance the whiptail interface
- 🐛 **Bug fixes** - Fix issues and improve reliability
- 📖 **Documentation** - Improve README, add tutorials
- 🧪 **Testing** - Test on different platforms
- 🌍 **Internationalization** - Translate MOTDs and UI

### How to Contribute a Container Configuration

1. Create a new file in `config.d/`:
```bash
cp config.d/ubuntu-24.yml config.d/my-new-container.yml
```

2. Edit with your configuration (inline MOTD + inline scripts)

3. Test it:
```bash
./playground.sh
# Select "Start containers" → your-new-container
```

4. Submit a pull request!

---

**Made with ❤️ for the developer community**

*Happy containerizing! 🐳*