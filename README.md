# 🐳 Docker Playground Manager

A professional, interactive tool for managing multiple Docker development environments with ease. Perfect for developers who need to quickly spin up containers for testing, development, or learning different technologies.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Shell Script](https://img.shields.io/badge/shell-bash-green.svg)
![Docker](https://img.shields.io/badge/docker-required-blue.svg)

## ✨ Features

- 🎯 **Interactive TUI** - Beautiful terminal user interface using whiptail
- 📦 **40+ Pre-configured Images** - Linux distros, programming languages, databases, and more
- 🔄 **Easy Management** - Start, stop, enter, and monitor containers with a few keystrokes
- 📁 **Shared Volumes** - Automatically mounted shared directory across all containers
- 🌐 **Network Isolation** - Containers communicate through a dedicated Docker network
- 📊 **Real-time Monitoring** - View logs and statistics for running containers
- 🧹 **Clean Cleanup** - Remove all playground resources with one command
- 📝 **Activity Logging** - All operations logged for troubleshooting

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

