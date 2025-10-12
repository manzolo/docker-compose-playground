```markdown
# 🐳 Docker Playground Manager v3.0

A professional, modular, feature-rich interactive tool for managing multiple Docker development environments with ease. Perfect for developers who need to quickly spin up containers for testing, development, learning, or experimenting with different technologies.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Shell Script](https://img.shields.io/badge/shell-bash-green.svg)
![Docker](https://img.shields.io/badge/docker-required-blue.svg)
![Python](https://img.shields.io/badge/python-required-blue.svg)
![Version](https://img.shields.io/badge/version-3.0-orange.svg)

<a href="https://www.buymeacoffee.com/manzolo">
  <img src=".github/blue-button.png" alt="Buy Me A Coffee" width="200">
</a>

## ✨ Features

### Core Features
- 🎯 **Interactive TUI** - Beautiful terminal user interface using whiptail
- 🌐 **Web UI (NEW!)** - Modern web interface for managing containers with real-time console, logs, and smart filtering
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
- **Always visible** - MOTD stays on screen like real system login messages
- **10+ pre-built guides** - MySQL, PostgreSQL, MongoDB, Redis, Python, Node.js, Go, Rust, Nginx, Docker-in-Docker

#### 🔧 Inline Pre/Post Script System
- **Inline scripts** - Define scripts directly in YAML configuration
- **File-based scripts** - Support for external scripts in `scripts/` directory
- **post_start scripts** - Execute custom scripts after container starts
- **pre_stop scripts** - Run cleanup or backup before stopping containers
- **Auto-discovery** - Scripts defined inline or referenced from `scripts/`
- **Built-in examples** - MySQL/PostgreSQL initialization, Python/Node package installation, automatic backups
- **Easy to extend** - Add your own custom scripts inline or as files

#### 🌐 Web UI (NEW!)
- **Dashboard** - Visual overview of containers with status, category, and actions
- **Smart Filtering** - Filter containers by name, category, or status (Running/Stopped)
- **Real-time Console** - Interactive terminal access via WebSocket using xterm.js
- **Log Viewer** - View and export container logs directly from the browser
- **Responsive Design** - Mobile-friendly interface for on-the-go management
- **Toast Notifications** - Real-time feedback for actions (start, stop, errors)
- **Stop All** - Quickly stop all running containers with one click

#### 📊 Enhanced Features
- 🔍 **Debug mode** - Built-in configuration debugging tool to troubleshoot issues
- 📈 **Better statistics** - Real-time container resource monitoring with auto-refresh
- 🎨 **Improved UI** - Color-coded sections, cleaner layout, better organization
- 🔄 **Restart containers** - Easily restart running containers without manual stop/start
- 📤 **Export logs** - Timestamped log exports for debugging and auditing
- 🔎 **Smart filtering** - Only show relevant containers in TUI; advanced filtering in Web UI

## 📋 Requirements

### For TUI
- **Docker** (version 20.10 or higher)
- **Docker Compose** (version 2.0 or higher)
- **yq** (YAML processor - auto-installed via snap if missing)
- **whiptail** (usually pre-installed on most Linux distributions)
- **Bash** (version 4.0 or higher)
<img width="788" height="484" alt="image" src="https://github.com/user-attachments/assets/d341037f-d006-4d08-b432-0e91aad22dcf" />
<img width="940" height="476" alt="image" src="https://github.com/user-attachments/assets/2c28f6ee-5ea8-4d91-9a9c-d61ecdff92bb" />

### For Web UI
- **Python 3.8+** (with `pip` for installing dependencies)
- **Flask** (auto-installed via `requirements.txt`)
- **Docker Python SDK** (auto-installed via `requirements.txt`)
- **Modern web browser** (Chrome, Firefox, Safari, Edge)

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/manzolo/docker-compose-playground.git
cd docker-compose-playground

# Make the scripts executable
chmod +x playground.sh start-webui.sh

# Generate example scripts (optional but recommended)
chmod +x create_scripts.sh
./create_scripts.sh

# Install Web UI dependencies (optional, for Web UI only)
pip install -r requirements.txt
```

### Using the TUI

1. Run the playground:
   ```bash
   ./playground.sh
   ```
2. The script checks for dependencies and offers to install missing ones.
3. Navigate the menu using arrow keys.
4. Select "Start containers" or "Start by category".
5. Choose one or more images (SPACE to select, ENTER to confirm).
6. Use "Enter a container" to access an interactive shell with MOTD display.
7. Post-start scripts initialize your environment automatically.

### Using the Web UI

1. Start the web server:
   ```bash
   ./start-webui.sh
   ```
2. Open your browser and navigate to `http://localhost:8000`.
3. Use the dashboard to:
   - Start/stop containers with one click.
   - Filter containers by name, category, or status (All, Running, Stopped).
   - Access real-time console for running containers.
   - View container logs in a modal window.
   - Stop all running containers with the "Stop All" button.
4. Use the search bar (Ctrl+K) for quick filtering.
5. Check `venv/web.log` for Web UI logs if issues arise.

### First Run Notes
- **TUI**: MOTD guides are displayed when entering containers (e.g., MySQL, PostgreSQL).
- **Web UI**: Containers are displayed as cards with status indicators and action buttons.
- **Shared Volume**: Accessible at `./shared-volumes` on the host and `/shared` in containers.

## 🏗️ Project Structure

```
docker-playground/
├── playground.sh              # Main entry point for TUI
├── start-webui.sh            # 🆕 Script to start Web UI server
├── app.py                    # 🆕 Flask backend for Web UI
├── index.html                # 🆕 Web UI dashboard
├── style.css                 # 🆕 Styling for Web UI
├── manager.js                # 🆕 JavaScript for Web UI logic
├── config.yml                # Base configuration (100+ images)
├── config.d/                 # 🆕 Modular configuration directory
│   ├── ubuntu-24.yml        # Example: Ubuntu 24.04 with inline MOTD & scripts
│   ├── postgres-16.yml      # Example: PostgreSQL 16 with inline scripts
│   ├── mysql-8.yml          # Example: MySQL 8 with initialization
│   ├── python-3.13.yml      # Example: Python with auto-pip install
│   └── custom.yml           # Add your own custom containers here!
├── create_scripts.sh         # Helper to generate example scripts
├── lib/                      # Modular library files for TUI
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
├── playground.log            # Activity log for TUI with timestamps
└── venv/                     # 🆕 Virtual environment for Web UI
    ├── web.log              # Web UI logs
    └── requirements.txt      # Python dependencies for Web UI
```

## 🎮 Usage

### Main Menu Categories (TUI)

#### 🚀 Container Management
- **Start containers** - Launch one or more container instances from all categories
- **Start by category** - Filter and start containers from a specific category
- **Stop containers** - Stop running containers (only shows running containers)
- **Enter a container** - Open an interactive shell with automatic MOTD display

#### 📊 Monitoring
- **List active containers** - View all running playground containers with image info
- **View container logs** - Stream real-time logs (Ctrl+C to exit gracefully)
- **Restart container** - Restart a specific container (runs pre-stop + post-start scripts)
- **Container statistics** - Monitor CPU, memory, network I/O with auto-refresh
- **Dashboard** - Visual overview with statistics, running containers, and category breakdown

#### 🔧 Tools
- **Search images** - Quick search by name or description (fuzzy matching)
- **Browse catalog** - Explore all 100+ available images organized by category
- **System information** - Display Docker version, disk usage, network info
- **Help** - Comprehensive usage guide with examples
- **Debug config** - Troubleshoot configuration issues

#### 🛠️ Maintenance
- **Export logs** - Save activity logs with timestamp for auditing
- **Cleanup (remove all)** - Stop and remove ALL playground containers (with confirmation)
- **Exit** - Close the playground manager

### Web UI Usage

1. **Access the Dashboard**:
   - Navigate to `http://localhost:8000` after running `./start-webui.sh`.
   - View all configured containers as cards with name, category, status, and actions.

2. **Manage Containers**:
   - **Start/Stop**: Click "Start Container" or "Stop" buttons on each card.
   - **Console**: Open an interactive terminal for running containers (supports WebSocket-based interaction).
   - **Logs**: View real-time container logs in a modal window.
   - **Stop All**: Stop all running containers with a single button.

3. **Filter Containers**:
   - Use the search bar (Ctrl+K) to filter by container name or category.
   - Select a category from the dropdown to filter by category.
   - Use status buttons (All, Running, Stopped) to filter by container status.
   - Badge counters show the number of containers in each state/category.

4. **Responsive Design**:
   - Access the Web UI from mobile devices or desktops with a consistent experience.

5. **Error Handling**:
   - Toast notifications provide feedback for actions (success, error, info).
   - Check `venv/web.log` for detailed error logs if issues occur.

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

When entering containers via TUI, you'll see helpful quick reference guides that **stay visible** on your terminal. For the Web UI, MOTDs are not displayed in the console but are defined in `config.yml` or `config.d/*.yml` for reference.

### Supported Containers with Inline MOTD

- **MySQL 8.0** - Connection info, backup/restore, common queries
- **PostgreSQL 16** - psql commands, pg_dump/restore, useful queries
- **MongoDB 7** - mongosh basics, backup/restore, CRUD operations
- **Redis 7** - redis-cli commands, data types, persistence
- **Python 3.13** - pip usage, quick testing, web servers
- **Node.js 22** - npm commands, Express setup, package management
- **Go 1.22** - go commands, module management, building
- **Rust 1.75** - cargo commands, building, testing
- **Docker-in-Docker** - Docker commands, image building
- **Nginx** - Configuration, site setup, log viewing
- **Ubuntu 24.04** - apt commands, system info utilities
- **Alpine Linux 3.19** - apk package manager, musl libc notes

## ⚙️ Configuration

### 🆕 Modular Configuration System

The v3.0 introduces a powerful modular configuration system for both TUI and Web UI:

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

1. **Base Config**: `config.yml` contains 100+ pre-configured images.
2. **Modular Configs**: Files in `config.d/*.yml` are automatically merged on startup.
3. **Override Behavior**: Files in `config.d/` can override base configuration.
4. **Validation**: Each file is validated independently before merging.
5. **Web UI Integration**: The Web UI reads the merged configuration to display containers.

#### Benefits

✅ **Organization** - Keep related containers together in separate files  
✅ **Team Collaboration** - Team members can add their own config files  
✅ **Easy Updates** - Update base config without touching custom configs  
✅ **Version Control** - Commit only your custom configs  
✅ **Web UI Support** - Seamlessly displays all configured containers  

### Basic Configuration

Create a new file in `config.d/` directory:

```yaml
# config.d/my-custom-image.yml
images:
  my-custom-image:
    image: custom/image:tag
    shell: /bin/bash
    keep_alive_cmd: sleep infinity
    description: "My Custom Container"
    category: custom
    environment:
      MY_VAR: value
    ports:
      - "8080:80"
    privileged: false
```

### 🆕 Advanced Configuration with Inline MOTD and Scripts

```yaml
# config.d/my-advanced-container.yml
images:
  my-advanced-image:
    image: myimage:latest
    shell: /bin/bash
    keep_alive_cmd: sleep infinity
    description: "Advanced Container with Inline MOTD and Scripts"
    category: custom
    
    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  My Custom Quick Reference                    ║
      ╚══════════════════════════════════════════════════════════════╝
      
      🔧 Important Commands:
         myapp start
         myapp status
         myapp logs
      
      📁 Important Paths:
         Config: /etc/myapp/config.yml
         Data: /var/lib/myapp/
         Logs: /var/log/myapp/
    
    scripts:
      post_start:
        inline: |
          #!/bin/bash
          CONTAINER_NAME="$1"
          echo "🚀 Initializing $CONTAINER_NAME..."
          docker exec "playground-$CONTAINER_NAME" apt-get update -qq
          docker exec "playground-$CONTAINER_NAME" apt-get install -y -qq curl wget
          docker exec "playground-$CONTAINER_NAME" mkdir -p /app/data
          docker exec "playground-$CONTAINER_NAME" sh -c "
            echo 'Container initialized at $(date)' > /app/initialized.txt
          "
          echo "✓ $CONTAINER_NAME initialized successfully"
      
      pre_stop:
        inline: |
          #!/bin/bash
          CONTAINER_NAME="$1"
          echo "💾 Creating backup for $CONTAINER_NAME..."
          BACKUP_DIR="${SHARED_DIR:-./shared-volumes}/backups/my-advanced-image"
          mkdir -p "$BACKUP_DIR"
          TIMESTAMP=$(date +%Y%m%d_%H%M%S)
          docker exec "playground-$CONTAINER_NAME" tar czf - /app/data \
            > "$BACKUP_DIR/data_${TIMESTAMP}.tar.gz" 2>/dev/null
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

### Configuration Options Reference

| Option | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| `image` | ✅ | string | Docker image name and tag | `ubuntu:24.04` |
| `shell` | ✅ | string | Shell to use when entering | `/bin/bash` or `/bin/sh` |
| `keep_alive_cmd` | ✅ | string | Command to keep container running | `sleep infinity` |
| `description` | ✅ | string | Human-readable description | `"Ubuntu 24.04 LTS"` |
| `category` | ✅ | string | Category for organization | `linux`, `programming`, `database` |
| `motd` | ❌ | multiline | Inline MOTD text (YAML block, TUI only) | See examples above |
| `scripts.post_start` | ❌ | string or object | Script file or inline script | `python_init.sh` or `{inline: "#!/bin/bash..."}` |
| `scripts.pre_stop` | ❌ | string or object | Script file or inline script | `generic_backup.sh` or `{inline: "#!/bin/bash..."}` |
| `environment` | ❌ | map | Environment variables | `{VAR: value}` |
| `ports` | ❌ | array | Port mappings | `["8080:80"]` |
| `privileged` | ❌ | boolean | Enable privileged mode | `true` or `false` |

## 🔍 Examples

### Example 1: Using Web UI to Manage Containers

1. Start the Web UI:
   ```bash
   ./start-webui.sh
   ```
2. Open `http://localhost:8000` in your browser.
3. Filter containers by category (e.g., "database") and status (e.g., "Running").
4. Start a container (e.g., `postgres-16`) and open its console.
5. View logs or stop the container from the dashboard.

### Example 2: Creating a Custom Container with Inline Config

Create `config.d/my-python-ml.yml`:

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

Run `./playground.sh` (TUI) or `./start-webui.sh` (Web UI) and select `python-ml-custom`.

### Example 3: Team Collaboration

Create `config.d/john-dev-env.yml`:

```yaml
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
          docker exec "playground-$CONTAINER_NAME" apt-get update -qq
          docker exec "playground-$CONTAINER_NAME" apt-get install -y -qq \
            vim tmux zsh git nodejs npm python3
          docker exec "playground-$CONTAINER_NAME" sh -c "
            git clone https://github.com/john/dotfiles /root/dotfiles
            cd /root/dotfiles && ./install.sh
          "
```

## 📝 Logging

- **TUI**: Logs are saved to `playground.log` with timestamps.
- **Web UI**: Logs are saved to `venv/web.log` for server-side actions and errors.

### Log Format (TUI)

```
[2025-10-12 11:01:14] [INFO] Docker Playground Manager v3.0 starting...
[2025-10-12 11:01:14] [SUCCESS] Merged base config + 12 files = 103 total images
```

### Log Format (Web UI)

```
2025-10-12 11:01:14,123 - INFO - Starting Flask server on port 8000
2025-10-12 11:01:15,456 - INFO - Loaded 103 images from configuration
2025-10-12 11:01:16,789 - ERROR - Failed to start container: myimage (Image not found)
```

## 🛟 Troubleshooting

### Web UI Issues

- **Server not starting**:
  ```bash
  # Check logs
  cat venv/web.log
  # Ensure dependencies are installed
  pip install -r requirements.txt
  # Verify Python version
  python3 --version
  ```

- **Console not connecting**:
  - Check browser console (F12) for JavaScript errors.
  - Ensure WebSocket endpoint (`/ws/console/{container}`) is accessible.
  - Verify container is running (`docker ps`).

- **Filters not working**:
  - Check `config.yml` and `config.d/*.yml` for correct `category` fields.
  - Ensure container status is correctly reported in `index.html` cards.

### TUI Issues

- **Config file not merging**:
  ```bash
  ls -la config.d/
  yq eval '.' config.d/ubuntu-24.yml
  ./playground.sh → "Debug config"
  ```

- **Container not visible**:
  ```bash
  docker ps --filter "label=playground.managed=true"
  ```

- **Inline script not executing**:
  ```bash
  grep "post-start\|pre-stop" playground.log
  yq eval '.images."your-container".scripts.post_start.inline' config.d/your-file.yml
  ```

## 🎯 Best Practices

### Web UI Usage
1. **Use Filters** - Combine name, category, and status filters for quick navigation.
2. **Monitor Logs** - Regularly check `venv/web.log` for errors.
3. **Secure Access** - Run the Web UI on `localhost` or use HTTPS for remote access.
4. **Responsive Design** - Test on mobile devices for usability.
5. **Backup Regularly** - Use pre-stop scripts to back up data to `/shared/backups`.

### Configuration Management
1. **Use config.d/** - Keep custom configs separate from `config.yml`.
2. **One container per file** - Simplifies management and sharing.
3. **Use inline scripts** - Keep configurations self-contained.
4. **Validate configs** - Use `yq eval '.' config.d/yourfile.yml` before running.
5. **Version control** - Commit `config.d/*.yml` files for team collaboration.

## 🤝 Contributing

Contributions are welcome! Areas for contribution include:

- 📝 **More inline configs** - Add container configs in `config.d/`.
- 🔧 **Web UI enhancements** - Improve `index.html`, `style.css`, or `app.py`.
- 🐛 **Bug fixes** - Fix issues in TUI or Web UI.
- 📦 **New images** - Add more pre-configured containers.
- 🎨 **UI improvements** - Enhance TUI (whiptail) or Web UI (CSS/JS).
- 📖 **Documentation** - Improve README, add tutorials.
- 🧪 **Testing** - Test on different platforms.
- 🌍 **Internationalization** - Translate MOTDs and UI.

### How to Contribute a Web UI Feature

1. Modify `app.py`, `index.html`, `style.css`, or `manager.js`.
2. Test with:
   ```bash
   ./start-webui.sh
   # Open http://localhost:8000
   ```
3. Submit a pull request with your changes.

### How to Contribute a Container Configuration

1. Create a new file in `config.d/`:
   ```bash
   cp config.d/ubuntu-24.yml config.d/my-new-container.yml
   ```
2. Edit with your configuration.
3. Test with TUI (`./playground.sh`) or Web UI (`./start-webui.sh`).
4. Submit a pull request.

---

**Made with ❤️ for the developer community**

*Happy containerizing! 🐳*
```