# 🐳 Docker Playground CLI

A powerful command-line interface for managing Docker Playground containers.

## 🚀 Quick Start

### Installation

```bash
# Make scripts executable
chmod +x playground install-cli.sh uninstall-cli.sh

# Install globally (recommended)
./install-cli.sh
# Or use: make install

# Or use directly without installing
./playground --help
```

### First Run

The first time you run the CLI, it will automatically:
- Create a Python virtual environment
- Install required dependencies (takes ~30 seconds)
- Cache the setup for instant future runs

Subsequent runs are instant thanks to intelligent caching.

## 📖 Commands

### Container Management

```bash
# List all containers
playground list
playground list --category linux
playground list --status running
playground list --json  # JSON output

# Start a container
playground start nginx
playground start postgres --force  # Force restart if running

# Stop a container
playground stop nginx
playground stop nginx --no-remove  # Keep container after stopping

# Restart a container
playground restart nginx

# Show running containers
playground ps
playground ps --all  # Include stopped containers
```

### Container Interaction

```bash
# View logs
playground logs nginx
playground logs nginx --follow  # Follow mode (like tail -f)
playground logs nginx --tail 50  # Last 50 lines

# Execute commands
playground exec nginx  # Open interactive shell
playground exec nginx "ls -la /etc"  # Run specific command

# Show detailed info
playground info nginx
```

### Bulk Operations

```bash
# Stop all running containers
playground stop-all
playground stop-all --yes  # Skip confirmation

# Cleanup all containers
playground cleanup
playground cleanup --yes  # Skip confirmation
playground cleanup --images  # Also remove Docker images

# Clean up Docker images from config
playground clean-images
playground clean-images --unused  # Only remove unused images
playground clean-images --yes  # Skip confirmation
```

### Utilities

```bash
# List categories
playground categories

# Show version
playground version
```

## 🎯 Common Workflows

### Development Workflow

```bash
# Start your development stack
playground start postgres
playground start redis
playground start nginx

# Check status
playground ps

# View logs
playground logs postgres --follow

# Access shell
playground exec postgres
```

### Cleanup Workflow

```bash
# Stop everything
playground stop-all

# Remove all containers
playground cleanup

# Remove unused images to free space
playground clean-images --unused
```

### Category-based Management

```bash
# List database containers
playground list --category database

# List all categories
playground categories
```

## 🔧 Configuration

The CLI reads from the same configuration files as the web dashboard:
- `config.yml` - Main configuration (Git-tracked)
- `config.d/*.yml` - Additional configurations (Git-tracked)
- `custom.d/*.yml` - User configurations (Git-ignored)

### Adding Custom Containers

Add a new YAML file in `custom.d/`:

```yaml
# custom.d/my-container.yml
images:
  my-app:
    image: "myapp:latest"
    category: "custom"
    description: "My custom application"
    keep_alive_cmd: "tail -f /dev/null"
    shell: "/bin/bash"
    ports:
      - "8080:80"
    environment:
      APP_ENV: "development"
```

Then:
```bash
playground list  # Your container appears
playground start my-app
```

## 📦 Virtual Environment

The CLI manages its own Python virtual environment:

**Location:** `venv/environments/python-3.12/`

**Cache file:** `venv/.cli_venv_ready`

The venv is automatically created on first run and cached for instant subsequent runs.

### Manual Venv Rebuild

If you encounter issues:

```bash
# Remove cache
rm -rf venv/environments venv/.cli_venv_ready

# Next run will rebuild
./playground list
```

## 🗑️ Uninstallation

```bash
# Remove global command and clean up
./uninstall-cli.sh

# Or manually
sudo rm /usr/local/bin/playground
rm -rf venv/environments
```

## 💡 Tips & Tricks

### Aliases

Add to your `.bashrc` or `.zshrc`:

```bash
alias pg='playground'
alias pgl='playground list'
alias pgs='playground start'
alias pgp='playground ps'
alias pge='playground exec'
```

### Quick Access

```bash
# Start and exec in one command
playground start nginx && playground exec nginx

# View logs while starting
playground start postgres && playground logs postgres --follow
```

### JSON Output for Scripting

```bash
# Get all running containers as JSON
playground list --status running --json | jq '.[].name'

# Count containers per category
playground list --json | jq 'group_by(.category) | map({category: .[0].category, count: length})'
```

## 🐛 Troubleshooting

### "Could not connect to Docker"
```bash
# Check Docker is running
sudo systemctl status docker

# Start Docker
sudo systemctl start docker

# Add user to docker group (then logout/login)
sudo usermod -aG docker $USER
```

### "Failed to create venv"
```bash
# Install Python venv package
sudo apt-get install python3-venv

# Or for other distros
sudo dnf install python3-virtualenv  # Fedora
sudo pacman -S python-virtualenv     # Arch
```

### Slow First Run
The first run takes ~30 seconds to setup the venv. Subsequent runs are instant thanks to caching.

### Permission Issues
```bash
# If you get permission errors
sudo chown -R $USER:$USER venv/

# For Docker permission issues
sudo usermod -aG docker $USER
# Then logout and login again
```

## 📚 Additional Resources

- **Web Dashboard:** Run `./start-web.sh` for GUI management
- **Configuration Examples:** See `config.d/` directory
- **Docker Documentation:** https://docs.docker.com/

## 🤝 Contributing

To add new features:

1. Edit `src/cli/cli.py`
2. Test with `./playground <command>`
3. Update this README

## 📄 License

Part of Docker Playground project.
