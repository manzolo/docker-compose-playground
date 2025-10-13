# 🎯 Docker Playground CLI - Examples

Practical examples for common use cases.

## 🚀 Getting Started

### First Time Setup

```bash
# Install globally
make install

# Or test without installing
make cli ARGS="--help"

# Verify installation
playground version
```

## 📋 Listing and Filtering

### Basic Listing

```bash
# List all containers
playground list

# Pretty table output with status
playground ps

# Include stopped containers
playground ps --all
```

### Filtered Listing

```bash
# Filter by category
playground list --category database
playground list --category linux
playground list --category programming

# Filter by status
playground list --status running
playground list --status stopped

# Combined filters
playground list --category database --status running
```

### JSON Output for Scripts

```bash
# Get JSON output
playground list --json

# Extract container names with jq
playground list --json | jq '.[].name'

# Get only running containers
playground list --status running --json | jq '.[].name'

# Count containers per category
playground list --json | jq 'group_by(.category) | map({category: .[0].category, count: length})'
```

## ▶️ Starting Containers

### Simple Start

```bash
# Start a container
playground start nginx

# Start with auto-restart if already running
playground start postgres --force
```

### Development Stack

```bash
# Start entire development stack
playground start postgres
playground start redis
playground start nginx
playground start mongodb

# Verify all started
playground ps
```

### Scripted Startup

```bash
#!/bin/bash
# start-dev-stack.sh

containers=("postgres" "redis" "nginx" "mongodb")

for container in "${containers[@]}"; do
    echo "Starting $container..."
    playground start "$container" --force
done

echo "✓ All containers started!"
playground ps
```

## ⏹️ Stopping Containers

### Individual Stop

```bash
# Stop a container
playground stop nginx

# Stop without removing
playground stop nginx --no-remove
```

### Bulk Stop

```bash
# Stop all running containers (with confirmation)
playground stop-all

# Skip confirmation
playground stop-all --yes
```

### Selective Stop

```bash
# Stop all database containers
for container in $(playground list --category database --status running --json | jq -r '.[].name'); do
    playground stop "$container"
done
```

## 🔄 Restart Operations

### Simple Restart

```bash
# Restart a container
playground restart nginx

# Quick restart script
playground restart postgres && playground logs postgres --follow
```

## 📋 Logs and Debugging

### View Logs

```bash
# Show last 100 lines (default)
playground logs nginx

# Show last 50 lines
playground logs nginx --tail 50

# Follow logs in real-time
playground logs postgres --follow

# Follow with Ctrl+C to stop
playground logs redis --follow
```

### Debug Container Issues

```bash
# Check if container is running
playground ps | grep nginx

# View detailed info
playground info nginx

# Check recent logs
playground logs nginx --tail 20

# Follow logs to see errors
playground logs nginx --follow
```

## 💻 Interactive Shell Access

### Open Shell

```bash
# Open interactive shell (uses configured shell)
playground exec nginx

# Run specific command
playground exec postgres "psql -U postgres -c 'SELECT version();'"

# Check files
playground exec nginx "ls -la /etc/nginx/"

# View environment
playground exec redis "env"
```

### Common Shell Operations

```bash
# Database operations
playground exec postgres "psql -U postgres -l"
playground exec mongodb "mongo --eval 'db.version()'"

# File inspection
playground exec nginx "cat /etc/nginx/nginx.conf"

# Process check
playground exec ubuntu "ps aux"

# Network check
playground exec alpine "netstat -tulpn"
```

## 🧹 Cleanup Operations

### Remove Specific Container

```bash
# Stop and remove
playground stop nginx

# Container is automatically removed after stop
```

### Full Cleanup

```bash
# Remove all containers (with confirmation)
playground cleanup

# Skip confirmation
playground cleanup --yes

# Also remove Docker images
playground cleanup --images --yes
```

### Clean Docker Images

```bash
# Remove images from config
playground clean-images

# Only remove unused images
playground clean-images --unused

# Skip confirmation
playground clean-images --yes

# Full cleanup (containers + images)
playground cleanup --images && playground clean-images --unused
```

## 📊 Status and Information

### Quick Status Check

```bash
# Show running containers
playground ps

# Show all containers
playground ps --all

# List categories
playground categories

# Get detailed container info
playground info postgres
```

### Health Check Script

```bash
#!/bin/bash
# health-check.sh

echo "🏥 Docker Playground Health Check"
echo "=================================="
echo ""

# Check running containers
echo "Running Containers:"
playground ps

echo ""
echo "Categories:"
playground categories

echo ""
echo "Docker Version:"
playground version
```

## 🔧 Advanced Workflows

### Development Workflow

```bash
# Morning routine - start your stack
playground start postgres
playground start redis
playground start nginx

# Check everything is running
playground ps

# Follow logs in separate terminals
playground logs postgres --follow  # Terminal 1
playground logs redis --follow     # Terminal 2
playground logs nginx --follow     # Terminal 3

# End of day - stop everything
playground stop-all --yes
```

### Testing Workflow

```bash
# Start fresh test environment
playground cleanup --yes
playground start test-postgres
playground start test-redis

# Run tests
playground exec test-postgres "psql -U postgres -f /shared/tests.sql"

# Check test logs
playground logs test-postgres --tail 100

# Cleanup after tests
playground stop test-postgres
playground stop test-redis
```

### Backup Workflow

```bash
# Start database if not running
playground start postgres

# Create backup
playground exec postgres "pg_dump -U postgres mydb > /shared/backup-$(date +%Y%m%d).sql"

# Verify backup
ls -lh shared-volumes/backup-*.sql

# Stop after backup
playground stop postgres
```

### Migration Workflow

```bash
# Start old version
playground start postgres-old

# Export data
playground exec postgres-old "pg_dumpall -U postgres > /shared/migration.sql"

# Stop old version
playground stop postgres-old

# Start new version
playground start postgres-new

# Import data
playground exec postgres-new "psql -U postgres < /shared/migration.sql"

# Verify
playground exec postgres-new "psql -U postgres -c '\l'"
```

## 🎨 Category-Based Management

### Work with Categories

```bash
# List all categories
playground categories

# View containers in a category
playground list --category database

# Start all in category (manual loop)
for container in $(playground list --category database --json | jq -r '.[].name'); do
    playground start "$container"
done

# Stop all in category
for container in $(playground list --category database --status running --json | jq -r '.[].name'); do
    playground stop "$container"
done
```

### Custom Category Scripts

```bash
#!/bin/bash
# start-category.sh

CATEGORY=$1

if [ -z "$CATEGORY" ]; then
    echo "Usage: $0 <category>"
    exit 1
fi

echo "Starting all containers in category: $CATEGORY"

containers=$(playground list --category "$CATEGORY" --json | jq -r '.[].name')

for container in $containers; do
    echo "Starting $container..."
    playground start "$container"
done

echo "✓ Done!"
playground list --category "$CATEGORY" --status running
```

## 🔍 Troubleshooting Examples

### Container Won't Start

```bash
# Check if image exists
docker images | grep <image-name>

# Try to pull image manually
docker pull <image-name>

# Check logs from previous run
playground logs <container> --tail 100

# Start with force restart
playground start <container> --force
```

### Port Conflicts

```bash
# Check what's using the port
sudo lsof -i :8080

# Stop container using that port
playground ps | grep <container>
playground stop <container>

# Or kill the process
sudo kill -9 $(sudo lsof -ti:8080)
```

### Disk Space Issues

```bash
# Check container sizes
docker ps -as

# Clean up unused images
playground clean-images --unused --yes

# Full cleanup
playground cleanup --images --yes

# Docker system cleanup
docker system prune -af
```

### Permission Issues

```bash
# Fix shared volume permissions
sudo chown -R $USER:$USER shared-volumes/

# Fix venv permissions
sudo chown -R $USER:$USER venv/

# Add user to docker group
sudo usermod -aG docker $USER
# Then logout and login again
```

## 🚀 Power User Tips

### Aliases for Speed

Add to `~/.bashrc` or `~/.zshrc`:

```bash
# Quick aliases
alias pg='playground'
alias pgl='playground list'
alias pgs='playground start'
alias pgst='playground stop'
alias pgp='playground ps'
alias pge='playground exec'
alias pglogs='playground logs'

# Start common stacks
alias pg-db='playground start postgres && playground start redis'
alias pg-web='playground start nginx && playground start nodejs'
alias pg-full='playground start postgres && playground start redis && playground start nginx'

# Quick stop
alias pg-stop='playground stop-all --yes'
```

### Monitoring Script

```bash
#!/bin/bash
# monitor.sh - Watch container status

watch -n 5 'playground ps'
```

### Auto-start on Boot

Create systemd service:

```bash
# /etc/systemd/system/playground-startup.service
[Unit]
Description=Docker Playground Auto-start
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
User=youruser
ExecStart=/path/to/playground start postgres
ExecStart=/path/to/playground start redis
ExecStart=/path/to/playground start nginx
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable playground-startup.service
sudo systemctl start playground-startup.service
```

### Backup Automation

```bash
#!/bin/bash
# auto-backup.sh

BACKUP_DIR="$HOME/playground-backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup each database container
for db in $(playground list --category database --status running --json | jq -r '.[].name'); do
    echo "Backing up $db..."
    playground exec "$db" "pg_dump -U postgres > /shared/$db-backup.sql" 2>/dev/null || true
    cp "shared-volumes/$db-backup.sql" "$BACKUP_DIR/" 2>/dev/null || true
done

echo "✓ Backups saved to $BACKUP_DIR"
```

## 📱 Integration Examples

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Test with Docker Playground

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Install CLI
        run: make install
      
      - name: Start test environment
        run: |
          playground start test-db
          playground start test-redis
      
      - name: Run tests
        run: |
          playground exec test-db "psql -U postgres -f /shared/tests.sql"
      
      - name: Cleanup
        run: playground cleanup --yes
```

### Docker Compose Migration

Instead of `docker-compose.yml`, use playground:

```bash
# Old way
docker-compose up -d

# New way
playground start postgres
playground start redis
playground start nginx

# Benefits: Better isolation, easier management, web UI
```

## 🎓 Learning Path

### Beginner

```bash
# 1. List available containers
playground list

# 2. Start your first container
playground start alpine

# 3. Check it's running
playground ps

# 4. Open a shell
playground exec alpine

# 5. Stop it
playground stop alpine
```

### Intermediate

```bash
# 1. Work with categories
playground categories
playground list --category database

# 2. Manage logs
playground logs postgres --follow

# 3. Use JSON output
playground list --json | jq

# 4. Bulk operations
playground stop-all
```

### Advanced

```bash
# 1. Create custom startup scripts
# 2. Integrate with CI/CD
# 3. Automate backups
# 4. Write monitoring tools
# 5. Contribute new features
```

## 📚 More Resources

- **CLI Reference:** `playground --help`
- **Command Help:** `playground <command> --help`
- **Web Dashboard:** `./start-web.sh`
- **Configuration:** Edit `custom.d/*.yml` files

---

**Need help?** Run `playground --help` or check CLI-README.md