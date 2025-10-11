# 🐳 Docker Playground Manager v2.4

A professional, feature-rich interactive tool for managing multiple Docker development environments with ease. Perfect for developers who need to quickly spin up containers for testing, development, learning, or experimenting with different technologies.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Shell Script](https://img.shields.io/badge/shell-bash-green.svg)
![Docker](https://img.shields.io/badge/docker-required-blue.svg)
![Version](https://img.shields.io/badge/version-2.4-orange.svg)

## ✨ Features

### Core Features
- 🎯 **Interactive TUI** - Beautiful terminal user interface using whiptail
- 📦 **100+ Pre-configured Images** - Linux distros, programming languages, databases, and more
- 🔄 **Smart Management** - Start, stop, enter, and monitor containers with ease
- 📁 **Shared Volumes** - Automatically mounted shared directory across all containers
- 🌐 **Network Isolation** - Containers communicate through a dedicated Docker network
- 🏷️ **Docker Labels** - Container tracking without filesystem dependencies

### New in v2.4
- 📚 **MOTD System** - Context-sensitive help when entering containers
- 🎯 **Category Filtering** - Start containers by category (database, programming, etc.)
- 🔍 **Quick Search** - Find images by name or description instantly
- 📺 **Dashboard** - Visual overview of your playground environment
- 📊 **Enhanced Statistics** - Better monitoring and resource tracking
- ❓ **Built-in Help** - Comprehensive documentation accessible from the menu
- 🎨 **Improved UI** - Color-coded sections and better organization

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

# Run the playground
./playground.sh
```

### First Run

1. The script will check for dependencies and offer to install missing ones
2. Navigate the menu using arrow keys
3. Select "Start containers" or "Start by category"
4. Choose one or more images from the catalog (SPACE to select, ENTER to confirm)
5. Use "Enter a container" to access an interactive shell
6. For supported containers (MySQL, PostgreSQL, etc.), you'll see helpful guides!

## 🎮 Usage

### Main Menu Categories

#### 🚀 Container Management
- **Start containers** - Launch one or more container instances from all categories
- **Start by category** - Filter and start containers from a specific category
- **Stop containers** - Stop running containers (pre-selected for convenience)
- **Enter a container** - Open an interactive shell with optional MOTD guides

#### 📊 Monitoring
- **List active containers** - View all running playground containers
- **View container logs** - Stream real-time logs (Ctrl+C to exit)
- **Restart container** - Restart a specific container
- **Container statistics** - Monitor resource usage (interactive refresh)
- **Dashboard** - Visual overview with statistics and running containers

#### 🔧 Tools
- **Search images** - Quick search by name or description
- **Browse catalog** - Explore all 100+ available images organized by category
- **System information** - Display configuration and system status
- **Help** - Comprehensive usage guide

#### 🛠️ Maintenance
- **Export logs** - Save activity logs with timestamp
- **Cleanup** - Stop all containers and remove shared volumes
- **Exit** - Close the playground manager

### Shared Volume

All containers have access to a shared directory:

- **Host path**: `./shared-volumes`
- **Container path**: `/shared`

Use this to:
- Exchange files between containers
- Test scripts across different environments
- Share configuration files
- Store backups

## 📚 MOTD (Message of the Day) System

When entering specific containers, you'll see helpful quick reference guides:

### Supported Containers with MOTD

- **MySQL** - Connection info, backup/restore, common queries
- **PostgreSQL** - psql commands, pg_dump/restore, useful queries
- **MongoDB** - mongosh basics, backup/restore, CRUD operations
- **Redis** - redis-cli commands, data types, persistence
- **Docker-in-Docker** - Docker commands, image building, networking
- **Python** - pip usage, quick testing, web servers
- **Node.js** - npm commands, Express setup, package management

Example: When you enter a MySQL container, you'll see:
```
╔══════════════════════════════════════════════════════════════╗
║                    MySQL Quick Reference                      ║
╚══════════════════════════════════════════════════════════════╝

🔐 Connection Info:
   Host: localhost
   User: playground / root
   Password: playground

💾 Backup & Restore:
   mysqldump -u root -pplayground playground > /shared/backup.sql
   mysql -u root -pplayground playground < /shared/backup.sql

[... more helpful commands ...]
```

## 📦 Available Images (100+)

### Categories

#### 🐧 Linux Distributions (13)
Ubuntu (24.04, 22.04, 20.04), Debian (12, 11), Alpine, Fedora, Rocky Linux, AlmaLinux, Arch, openSUSE Leap, Kali Linux

#### 💻 Programming Languages (40+)
- **Python**: 3.13, 3.12, 3.11, 3.10, Alpine, Anaconda, Miniconda
- **JavaScript/Node**: Node 22/20/18, Deno, Bun
- **JVM**: OpenJDK 21/17/11, Gradle, Maven, Kotlin, Scala
- **Compiled**: Go, Rust, GCC, Clang, Zig
- **Others**: PHP 8.3/8.2, Ruby, Elixir, Erlang, Haskell, Swift, .NET 8, Lua, Perl

#### 🗄️ Databases (20+)
- **SQL**: PostgreSQL 16/15, MySQL 8/5.7, MariaDB 11/10, CockroachDB
- **NoSQL**: MongoDB 7/6, Redis 7, Memcached, Cassandra, CouchDB, Neo4j
- **Analytics**: Elasticsearch, InfluxDB

#### 🌐 Web Servers (7)
Nginx, Apache, Caddy, Traefik, HAProxy (with management interfaces)

#### 📨 Message Queues (4)
RabbitMQ, Apache Kafka, NATS, ActiveMQ

#### 🔧 DevOps & CI/CD (8)
Docker-in-Docker, Jenkins, GitLab Runner, Ansible, Terraform, Packer, Vault, Consul

#### 📊 Monitoring (4)
Prometheus, Grafana, Jaeger, Zipkin

#### 🤖 Machine Learning (3)
Jupyter Notebook, TensorFlow, PyTorch

#### 🛠️ Utilities (7)
BusyBox, Alpine Tools, curl, Ubuntu Full, Network troubleshooting, Selenium (Chrome/Firefox)

## ⚙️ Configuration

Edit `config.yml` to add or modify images:

```yaml
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
    privileged: false  # optional
```

### Configuration Options

- `image`: Docker image name and tag (required)
- `shell`: Shell to use when entering the container (required)
- `keep_alive_cmd`: Command to keep the container running (required)
- `description`: Human-readable description (required)
- `category`: Category for organization (required)
- `environment`: Environment variables (optional)
- `ports`: Port mappings (optional)
- `privileged`: Enable privileged mode (optional, default: false)

## 🔍 Examples

### Example 1: Database Development with Quick Reference

```bash
# 1. Start PostgreSQL container
./playground.sh
# Select "Start by category" → "database" → postgres-16

# 2. Enter the container
# Select "Enter a container" → postgres-16
# You'll see the PostgreSQL quick reference guide!

# 3. Inside container, test backup/restore
psql -U playground
CREATE TABLE test (id INT, name VARCHAR(50));
INSERT INTO test VALUES (1, 'Alice');
\q

pg_dump -U playground playground > /shared/my_backup.sql
# Backup is now in ./shared-volumes/my_backup.sql on your host!
```

### Example 2: Multi-Language Testing

```bash
# 1. Start Python and Node containers
# Select "Start containers" → python-3.12, node-22

# 2. Create a shared script
echo 'print("Hello from Python!")' > shared-volumes/test.py
echo 'console.log("Hello from Node!");' > shared-volumes/test.js

# 3. Test in Python container
# Enter python-3.12 → python /shared/test.py

# 4. Test in Node container
# Enter node-22 → node /shared/test.js
```

### Example 3: Category-based Development Environment

```bash
# Setup a complete web dev environment
# 1. Start by category "programming" → select node-22, python-3.12
# 2. Start by category "database" → select postgres-16, redis-7
# 3. Start by category "webserver" → select nginx-latest

# Now you have a full stack ready to develop!
```

### Example 4: Using the Dashboard

```bash
# 1. Start several containers
# 2. Select "Dashboard" to see:
#    - How many containers are running
#    - Which ones are active
#    - Images breakdown by category
```

## 📝 Logging

All operations are logged to `playground.log` in the current directory with timestamps. Use the "Export logs" option to create a timestamped backup.

Log format:
```
[2025-10-11 18:30:45] Started containers: mysql-8 postgres-16
[2025-10-11 18:31:12] Entered container: mysql-8
[2025-10-11 18:35:20] Stopped containers: mysql-8
```

## 🛟 Troubleshooting

### Container won't start
- Check if the image exists: `docker pull <image-name>`
- Verify Docker daemon: `docker ps`
- View logs from the "View container logs" menu
- Check `playground.log` for errors

### Port conflicts
- Modify port mappings in `config.yml`
- Check for services using ports: `sudo netstat -tlnp | grep <port>`
- Example: Change `5432:5432` to `5433:5432` for PostgreSQL

### Permission denied
- Add user to docker group: `sudo usermod -aG docker $USER`
- Log out and back in
- Restart Docker: `sudo systemctl restart docker`

### yq not found
- Script offers automatic installation
- Manual: `sudo snap install yq`

### Shared volume not writable
- Check permissions: `ls -la shared-volumes/`
- Fix: `chmod -R 777 shared-volumes/`

### Container not visible after restart
- Containers use Docker labels for tracking
- Check: `docker ps --filter "label=playground.managed=true"`
- If missing, restart containers from the menu

## 🎯 Best Practices

1. **Use categories** - Organize your workflow by starting containers by category
2. **Check MOTD guides** - When available, read the quick reference for tips
3. **Use shared volume** - Store all your work in `/shared` for persistence
4. **Regular cleanup** - Use the cleanup option when switching projects
5. **Monitor resources** - Use the dashboard and stats to track usage
6. **Export logs** - Keep logs for troubleshooting and auditing

## 🤝 Contributing

Contributions are welcome! Areas for contribution:

- Adding more MOTD guides for containers
- New pre-configured images
- UI/UX improvements
- Bug fixes and optimizations
- Documentation improvements

### How to Contribute

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Test your changes thoroughly
4. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
5. Push to the branch (`git push origin feature/AmazingFeature`)
6. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Docker community for excellent documentation
- Contributors to yq, whiptail, and other tools
- All open-source projects that make this possible
- Everyone who provided feedback and suggestions

## 📧 Support

- 📖 Check the built-in help: Select "Help" from the menu
- 🐛 Report issues: GitHub Issues
- 💡 Feature requests: GitHub Discussions
- 📝 Documentation: This README and MOTD guides

---

**Made with ❤️ for the developer community**

*Happy containerizing! 🐳*eshooting

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

# Run the playground
./playground.sh
```

### First Run

1. The script will check for dependencies and offer to install missing ones
2. Select "Start containers" from the main menu
3. Choose one or more images from the catalog
4. Press SPACE to select, ENTER to confirm
5. Containers will start automatically
6. Use "Enter a container" to access the shell

## 🎮 Usage

### Main Menu Options

- **▶ Start containers** - Launch one or more container instances
- **■ Stop containers** - Stop running containers
- **📋 List active containers** - View all running playground containers
- **💻 Enter a container** - Open an interactive shell inside a container
- **📊 View container logs** - Stream real-time logs from a container
- **🔄 Restart container** - Restart a specific container
- **📈 Container statistics** - View CPU, memory, and network usage
- **📚 Browse image catalog** - Explore all available images by category
- **ℹ System information** - Display configuration and system status
- **📤 Export logs** - Save activity logs to a file
- **🧹 Cleanup** - Stop all containers and remove shared volumes
- **❌ Exit** - Close the playground manager

### Shared Volume

All containers have access to a shared directory:

- **Host path**: `./shared-volumes`
- **Container path**: `/shared`

Use this to:
- Exchange files between containers
- Test scripts across different environments
- Share configuration files

## 📚 Available Images

### Linux Distributions
- Ubuntu (24.04, 22.04, 20.04)
- Debian (12, 11)
- Alpine Linux
- Fedora
- Arch Linux

### Programming Languages
- Python (3.12, 3.11)
- Node.js (22, 20)
- Go
- Rust
- OpenJDK 21
- PHP 8.3
- Ruby

### Databases
- PostgreSQL 16
- MySQL 8
- MariaDB
- MongoDB
- Redis

### Web Servers
- Nginx (accessible at `http://localhost:8080`)
- Apache (accessible at `http://localhost:8081`)

### DevOps Tools
- Docker in Docker
- Ansible
- Terraform

### Utilities
- BusyBox
- curl

## ⚙️ Configuration

Edit `config.yml` to add or modify images:

```yaml
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
```

### Configuration Options

- `image`: Docker image name and tag
- `shell`: Shell to use when entering the container
- `keep_alive_cmd`: Command to keep the container running
- `description`: Human-readable description
- `category`: Category for organization (linux, programming, database, etc.)
- `environment`: Environment variables (optional)
- `ports`: Port mappings (optional)
- `privileged`: Enable privileged mode (optional, default: false)

## 🔍 Examples

### Example 1: Testing Python Script Across Versions

```bash
# 1. Start Python 3.11 and 3.12 containers
# 2. Create a script in shared-volumes/test.py
# 3. Enter Python 3.11 container
python /shared/test.py
# 4. Exit and enter Python 3.12 container
python /shared/test.py
# 5. Compare results
```

### Example 2: Database Development

```bash
# 1. Start PostgreSQL container
# 2. Enter the container
psql -U playground
# 3. Create your database and tables
# 4. Connection info:
#    Host: localhost
#    Port: 5432
#    User: playground
#    Password: playground
```

### Example 3: Testing Across Linux Distributions

```bash
# 1. Start Ubuntu, Debian, and Alpine
# 2. Create a shell script in shared-volumes/
# 3. Test the script in each environment
# 4. Identify compatibility issues
```

## 📝 Logging

All operations are logged to `playground.log` in the current directory. Use the "Export logs" option to create a timestamped copy.

## 🛟 Troubleshooting

### Container won't start
- Check if the image is available: `docker pull <image-name>`
- Verify Docker daemon is running: `docker ps`
- Check logs: View container logs from the menu

### Permission denied
- Ensure your user is in the docker group: `sudo usermod -aG docker $USER`
- Log out and back in for changes to take effect

### yq not found
- The script will offer to install it automatically
- Manual installation: `sudo snap install yq`

### Port conflicts
- Modify port mappings in `config.yml`
- Check for services using the same ports: `sudo netstat -tlnp`

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Docker community for excellent documentation
- Contributors to yq and whiptail
- All the open-source projects that make this possible

