#!/usr/bin/env python3
"""
Configuration Standardization Script
Automates the process of adding MOTDs and standardizing config files
"""

import yaml
import os
import sys
from pathlib import Path
from typing import Dict, List

# MOTD Templates by category
MOTD_TEMPLATES = {
    "linux": {
        "alpine": """╔══════════════════════════════════════════════════════════════╗
║           {name} Quick Reference                            ║
╚══════════════════════════════════════════════════════════════╝

📦 Package Manager (apk):
   apk update                               # Update package index
   apk add package_name                     # Install package
   apk del package_name                     # Remove package
   apk search package_name                  # Search for package
   apk info                                 # List installed packages

🔧 System Information:
   uname -a                                 # Kernel and system info
   cat /etc/alpine-release                  # Alpine version
   df -h                                    # Disk usage
   free -m                                  # Memory usage

💡 Tips:
   • Alpine uses musl libc (not glibc)
   • Very lightweight - perfect for containers
   • Use /shared for persistent files

📚 Documentation: https://wiki.alpinelinux.org/""",

        "debian": """╔══════════════════════════════════════════════════════════════╗
║           {name} Quick Reference                            ║
╚══════════════════════════════════════════════════════════════╝

📦 Package Manager (apt):
   apt update                               # Update package index
   apt install package_name                 # Install package
   apt remove package_name                  # Remove package
   apt search package_name                  # Search for package
   apt list --installed                     # List installed packages

🔧 System Information:
   uname -a                                 # Kernel and system info
   cat /etc/debian_version                  # Debian version
   cat /etc/os-release                      # Distribution details
   df -h                                    # Disk usage
   free -h                                  # Memory usage

💡 Tips:
   • Use apt-get for scripts, apt for interactive use
   • Common packages: curl, wget, git, vim
   • Use /shared for persistent files

📚 Documentation: https://www.debian.org/doc/""",

        "ubuntu": """╔══════════════════════════════════════════════════════════════╗
║           {name} Quick Reference                            ║
╚══════════════════════════════════════════════════════════════╝

📦 Package Manager (apt):
   apt update                               # Update package index
   apt install package_name                 # Install package
   apt remove package_name                  # Remove package
   apt search package_name                  # Search for package
   apt list --installed                     # List installed packages

🔧 System Information:
   uname -a                                 # Kernel and system info
   lsb_release -a                           # Ubuntu version
   df -h                                    # Disk usage
   free -h                                  # Memory usage

💡 Tips:
   • Ubuntu is Debian-based
   • Use /shared for persistent files
   • Common packages: build-essential, git, curl

📚 Documentation: https://ubuntu.com/server/docs""",

        "fedora": """╔══════════════════════════════════════════════════════════════╗
║           {name} Quick Reference                            ║
╚══════════════════════════════════════════════════════════════╝

📦 Package Manager (dnf):
   dnf install package_name                 # Install package
   dnf remove package_name                  # Remove package
   dnf search package_name                  # Search for package
   dnf list installed                       # List installed packages
   dnf update                               # Update all packages

🔧 System Information:
   uname -a                                 # Kernel and system info
   cat /etc/fedora-release                  # Fedora version
   df -h                                    # Disk usage
   free -h                                  # Memory usage

💡 Tips:
   • Fedora uses dnf (next-gen yum)
   • Use /shared for persistent files
   • Bleeding edge packages

📚 Documentation: https://docs.fedoraproject.org/""",

        "arch": """╔══════════════════════════════════════════════════════════════╗
║           {name} Quick Reference                            ║
╚══════════════════════════════════════════════════════════════╝

📦 Package Manager (pacman):
   pacman -S package_name                   # Install package
   pacman -R package_name                   # Remove package
   pacman -Ss package_name                  # Search for package
   pacman -Q                                # List installed packages
   pacman -Syu                              # System upgrade

🔧 System Information:
   uname -a                                 # Kernel and system info
   cat /etc/os-release                      # Distribution details
   df -h                                    # Disk usage
   free -h                                  # Memory usage

💡 Tips:
   • Arch is rolling release
   • Use /shared for persistent files
   • Check Arch Wiki for everything

📚 Documentation: https://wiki.archlinux.org/""",
    },

    "programming": {
        "python": """╔══════════════════════════════════════════════════════════════╗
║          {name} Development Environment                      ║
╚══════════════════════════════════════════════════════════════╝

📦 Package Manager (pip):
   pip install package_name                 # Install package
   pip install -r requirements.txt          # Install from file
   pip list                                 # List installed packages
   pip freeze > /shared/requirements.txt    # Save dependencies

🚀 Quick Start:
   python3                                  # Interactive REPL
   python3 script.py                        # Run a script
   python3 -m venv /shared/myenv            # Create virtual environment

🔧 Development Tools:
   python3 --version                        # Check version
   pip install ipython jupyter              # Better REPL & notebooks
   pip install pytest                       # Testing framework

💡 Workspace: /shared/projects/
📚 Docs: https://docs.python.org/""",

        "node": """╔══════════════════════════════════════════════════════════════╗
║          {name} Development Environment                      ║
╚══════════════════════════════════════════════════════════════╝

📦 Package Manager (npm):
   npm install package_name                 # Install package
   npm install                              # Install from package.json
   npm list                                 # List installed packages
   npm init                                 # Create package.json

🚀 Quick Start:
   node                                     # Interactive REPL
   node script.js                           # Run a script
   npm start                                # Run npm start script

🔧 Development Tools:
   node --version                           # Check version
   npm install -g nodemon                   # Auto-restart on changes
   npm install -g pm2                       # Process manager

💡 Workspace: /shared/projects/
📚 Docs: https://nodejs.org/docs/""",

        "java": """╔══════════════════════════════════════════════════════════════╗
║          {name} Development Environment                      ║
╚══════════════════════════════════════════════════════════════╝

🚀 Quick Start:
   java -version                            # Check version
   javac HelloWorld.java                    # Compile
   java HelloWorld                          # Run

🔧 Development Tools:
   jshell                                   # Interactive REPL
   jar cf app.jar files/                    # Create JAR
   java -jar app.jar                        # Run JAR

💡 Workspace: /shared/projects/
📚 Docs: https://docs.oracle.com/javase/""",

        "go": """╔══════════════════════════════════════════════════════════════╗
║          {name} Development Environment                      ║
╚══════════════════════════════════════════════════════════════╝

📦 Package Manager:
   go get package                           # Install package
   go mod init module_name                  # Initialize module
   go mod tidy                              # Clean dependencies

🚀 Quick Start:
   go run main.go                           # Run program
   go build                                 # Compile program
   go test                                  # Run tests

💡 Workspace: /shared/projects/
📚 Docs: https://go.dev/doc/""",

        "rust": """╔══════════════════════════════════════════════════════════════╗
║          {name} Development Environment                      ║
╚══════════════════════════════════════════════════════════════╝

📦 Package Manager (cargo):
   cargo new project_name                   # Create new project
   cargo build                              # Build project
   cargo run                                # Run project
   cargo test                               # Run tests

🔧 Development Tools:
   rustc --version                          # Check version
   cargo fmt                                # Format code
   cargo clippy                             # Linter

💡 Workspace: /shared/projects/
📚 Docs: https://doc.rust-lang.org/""",
    }
}


def detect_distro(container_name: str, image: str) -> str:
    """Detect Linux distribution type"""
    name_lower = container_name.lower()
    image_lower = image.lower()

    if 'alpine' in name_lower or 'alpine' in image_lower:
        return 'alpine'
    elif 'debian' in name_lower or 'debian' in image_lower:
        return 'debian'
    elif 'ubuntu' in name_lower or 'ubuntu' in image_lower:
        return 'ubuntu'
    elif 'fedora' in name_lower or 'fedora' in image_lower:
        return 'fedora'
    elif 'arch' in name_lower or 'arch' in image_lower:
        return 'arch'
    else:
        return 'debian'  # Default


def detect_language(container_name: str, image: str) -> str:
    """Detect programming language"""
    name_lower = container_name.lower()
    image_lower = image.lower()

    if 'python' in name_lower or 'python' in image_lower:
        return 'python'
    elif 'node' in name_lower or 'node' in image_lower:
        return 'node'
    elif 'java' in name_lower or 'openjdk' in image_lower:
        return 'java'
    elif 'go' in name_lower or 'golang' in image_lower:
        return 'go'
    elif 'rust' in name_lower or 'rust' in image_lower:
        return 'rust'
    else:
        return None


def generate_motd(container_name: str, image: str, category: str) -> str:
    """Generate appropriate MOTD based on category"""

    if category == 'linux':
        distro = detect_distro(container_name, image)
        template = MOTD_TEMPLATES['linux'].get(distro, MOTD_TEMPLATES['linux']['debian'])
        name = container_name.replace('-', ' ').title()
        return template.format(name=name)

    elif category == 'programming':
        lang = detect_language(container_name, image)
        if lang and lang in MOTD_TEMPLATES['programming']:
            template = MOTD_TEMPLATES['programming'][lang]
            name = container_name.replace('-', ' ').title()
            return template.format(name=name)

    return None


def process_config_file(filepath: Path, dry_run: bool = False) -> bool:
    """Process a single config file"""
    try:
        with open(filepath, 'r') as f:
            config = yaml.safe_load(f)

        if not config or 'images' not in config:
            return False

        modified = False

        for container_name, container_config in config['images'].items():
            # Skip if already has motd
            if 'motd' in container_config:
                continue

            category = container_config.get('category', '')
            image = container_config.get('image', '')

            # Generate MOTD
            motd = generate_motd(container_name, image, category)

            if motd:
                if dry_run:
                    print(f"  Would add MOTD to: {container_name}")
                else:
                    container_config['motd'] = motd
                    modified = True
                    print(f"  ✓ Added MOTD to: {container_name}")

        if modified and not dry_run:
            with open(filepath, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            return True

        return False

    except Exception as e:
        print(f"  ✗ Error processing {filepath}: {e}")
        return False


def main():
    config_dir = Path('config.d')

    if not config_dir.exists():
        print("Error: config.d directory not found")
        sys.exit(1)

    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("DRY RUN MODE - No files will be modified\n")

    print("Scanning config files...\n")

    # Skip stack files (they have groups)
    files = [f for f in config_dir.glob('*.yml') if not f.name.startswith('stack-')]

    total = len(files)
    modified = 0

    for filepath in sorted(files):
        if process_config_file(filepath, dry_run):
            modified += 1

    print(f"\nSummary:")
    print(f"  Total files scanned: {total}")
    print(f"  Files modified: {modified}")

    if dry_run:
        print(f"\nRun without --dry-run to apply changes")


if __name__ == '__main__':
    main()
