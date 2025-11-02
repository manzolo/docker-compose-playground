#!/usr/bin/env python3
"""
Script to add MOTDs to container configuration files that are missing them.
"""

import yaml
import os
from pathlib import Path

CONFIG_DIR = Path("config.d")

# MOTD templates by category
MOTD_TEMPLATES = {
    "database": """
      ╔══════════════════════════════════════════════════════════════╗
      ║                 {name} Quick Reference                       ║
      ╚══════════════════════════════════════════════════════════════╝

      🔐 Connection Info:
         Port: {port}
         Default credentials are typically in the environment variables
         Check the container configuration for specific details

      📊 Basic Commands:
         {basic_commands}

      💾 Data Persistence:
         Use /shared directory for storing backups and data files

      📁 Useful Directories:
         /shared                                   # Shared with host

      💡 Tips:
         • Keep backups in /shared for persistence
         • Check logs if connection issues occur
         • Data persists in container volumes
""",

    "programming": """
      ╔══════════════════════════════════════════════════════════════╗
      ║            {name} Development Environment                    ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Start:
         {quick_start}

      📦 Package Management:
         {package_mgmt}

      📁 Useful Directories:
         /shared                                   # Shared with host
         /shared/projects                          # Store your projects

      💡 Tips:
         • Keep your code in /shared for persistence
         • Use the /shared directory for data exchange
""",

    "webserver": """
      ╔══════════════════════════════════════════════════════════════╗
      ║                  {name} Web Server                           ║
      ╚══════════════════════════════════════════════════════════════╝

      🌐 Server Info:
         Port: {port}
         Access: http://localhost:{port}

      📁 Content Directories:
         /usr/share/nginx/html (for Nginx)
         /var/www/html (for Apache)
         Use /shared for custom content

      🔧 Configuration:
         {config_info}

      💡 Tips:
         • Place static files in /shared
         • Check logs for debugging
""",

    "messaging": """
      ╔══════════════════════════════════════════════════════════════╗
      ║             {name} Message Broker                            ║
      ╚══════════════════════════════════════════════════════════════╝

      🔌 Connection Info:
         {connection_info}

      📊 Management:
         Web UI: {webui}

      💡 Tips:
         • Check the documentation for specific configuration
         • Use /shared for storing configuration files
""",

    "devops": """
      ╔══════════════════════════════════════════════════════════════╗
      ║                 {name} DevOps Tool                           ║
      ╚══════════════════════════════════════════════════════════════╝

      🛠️  Quick Start:
         {quick_start}

      📁 Useful Directories:
         /shared                                   # Shared with host

      💡 Tips:
         • Keep configuration files in /shared
         • Use /shared for playbooks/scripts
""",

    "utility": """
      ╔══════════════════════════════════════════════════════════════╗
      ║                    {name} Utility                            ║
      ╚══════════════════════════════════════════════════════════════╝

      🔧 Basic Usage:
         {basic_usage}

      📁 Useful Directories:
         /shared                                   # Shared with host

      💡 Tips:
         • This is a minimal utility container
         • Use /shared for file operations
""",

    "generic": """
      ╔══════════════════════════════════════════════════════════════╗
      ║                    {name} Container                          ║
      ╚══════════════════════════════════════════════════════════════╝

      📁 Useful Directories:
         /shared                                   # Shared with host

      💡 Tips:
         • Use /shared directory for persistence
         • Check container documentation for specific usage
         • Logs and data can be stored in /shared
"""
}

# Specific configurations for known containers
CONTAINER_CONFIGS = {
    "mariadb-10": {
        "port": "3307",
        "basic_commands": "mysql -u root -pplayground                    # Connect as root\n         mysql -u playground -pplayground playground   # Connect to playground DB"
    },
    "mariadb-11": {
        "port": "3308",
        "basic_commands": "mysql -u root -pplayground                    # Connect as root\n         mysql -u playground -pplayground playground   # Connect to playground DB"
    },
    "nginx-alpine": {
        "port": "8081",
        "config_info": "Config: /etc/nginx/nginx.conf\n         Test config: nginx -t\n         Reload: nginx -s reload"
    },
    "nginx-latest": {
        "port": "8080",
        "config_info": "Config: /etc/nginx/nginx.conf\n         Test config: nginx -t\n         Reload: nginx -s reload"
    },
    "apache-alpine": {
        "port": "8082",
        "config_info": "Config: /usr/local/apache2/conf/httpd.conf\n         Test config: apachectl -t\n         Reload: apachectl -k graceful"
    },
    "apache-latest": {
        "port": "8083",
        "config_info": "Config: /usr/local/apache2/conf/httpd.conf\n         Test config: apachectl -t\n         Reload: apachectl -k graceful"
    },
    "activemq": {
        "connection_info": "Broker: localhost:61616\n         Console: localhost:8161",
        "webui": "http://localhost:8161 (admin/admin)"
    },
    "cassandra": {
        "port": "9042",
        "basic_commands": "cqlsh                                        # Connect to Cassandra\n         nodetool status                              # Check cluster status"
    },
    "cockroachdb": {
        "port": "26257",
        "basic_commands": "cockroach sql --insecure                     # Connect to CockroachDB\n         cockroach node status --insecure            # Check node status"
    },
    "couchdb": {
        "port": "5984",
        "basic_commands": "curl http://localhost:5984                   # Check CouchDB status\n         Web UI: http://localhost:5984/_utils       # Fauxton UI"
    },
    "influxdb": {
        "port": "8086",
        "basic_commands": "influx                                       # Connect to InfluxDB CLI\n         Web UI: http://localhost:8086              # InfluxDB UI"
    },
    "elasticsearch": {
        "port": "9200",
        "basic_commands": "curl http://localhost:9200                   # Check cluster health\n         curl http://localhost:9200/_cat/indices    # List indices"
    },
    "grafana": {
        "port": "3000",
        "basic_commands": "Web UI: http://localhost:3000                # Grafana Dashboard\n         Default: admin/admin"
    }
}

# Language-specific configs
LANGUAGE_CONFIGS = {
    "bun": {
        "quick_start": "bun --version                             # Check version\n         bun init                                  # Initialize project\n         bun install                               # Install dependencies",
        "package_mgmt": "bun add package_name                     # Add package\n         bun remove package_name                   # Remove package\n         bun update                                # Update packages"
    },
    "deno": {
        "quick_start": "deno --version                            # Check version\n         deno run script.ts                        # Run TypeScript file\n         deno run --allow-net script.ts            # Run with network permission",
        "package_mgmt": "deno cache deps.ts                       # Cache dependencies\n         deno info                                 # Show cached dependencies"
    },
    "dotnet-8": {
        "quick_start": "dotnet --version                          # Check version\n         dotnet new console                        # Create new console app\n         dotnet run                                # Run application",
        "package_mgmt": "dotnet add package PackageName           # Add NuGet package\n         dotnet restore                            # Restore dependencies"
    },
    "elixir": {
        "quick_start": "elixir --version                          # Check version\n         iex                                       # Interactive Elixir\n         elixir script.exs                         # Run Elixir script",
        "package_mgmt": "mix new myapp                            # Create new project\n         mix deps.get                              # Install dependencies"
    },
    "erlang": {
        "quick_start": "erl                                       # Erlang shell\n         erl -version                              # Check version",
        "package_mgmt": "rebar3 new app myapp                     # Create new app\n         rebar3 compile                            # Compile project"
    },
    "gradle": {
        "quick_start": "gradle --version                          # Check version\n         gradle init                               # Initialize project\n         gradle build                              # Build project",
        "package_mgmt": "Check build.gradle for dependencies"
    },
    "haskell": {
        "quick_start": "ghci                                      # GHC interactive\n         ghc --version                             # Check version\n         runhaskell script.hs                      # Run script",
        "package_mgmt": "cabal update                             # Update package list\n         cabal install package_name                # Install package"
    },
    "kotlin": {
        "quick_start": "kotlinc -version                          # Check version\n         kotlinc script.kt -include-runtime -d app.jar  # Compile\n         java -jar app.jar                         # Run compiled jar",
        "package_mgmt": "Use Gradle or Maven for dependency management"
    },
    "lua": {
        "quick_start": "lua -v                                    # Check version\n         lua script.lua                            # Run Lua script\n         lua                                       # Interactive mode",
        "package_mgmt": "luarocks install package_name            # Install package\n         luarocks list                             # List packages"
    },
    "clang": {
        "quick_start": "clang --version                           # Check version\n         clang hello.c -o hello                    # Compile C\n         clang++ hello.cpp -o hello                # Compile C++",
        "package_mgmt": "System packages via package manager"
    },
    "gcc": {
        "quick_start": "gcc --version                             # Check version\n         gcc hello.c -o hello                      # Compile C\n         g++ hello.cpp -o hello                    # Compile C++",
        "package_mgmt": "System packages via package manager"
    }
}

# Tool-specific configs
TOOL_CONFIGS = {
    "ansible": {
        "quick_start": "ansible --version                         # Check version\n         ansible all -m ping                       # Ping all hosts\n         ansible-playbook playbook.yml             # Run playbook"
    },
    "curl": {
        "basic_usage": "curl --version                            # Check version\n         curl https://example.com                  # Fetch URL\n         curl -X POST -d 'data' https://api.com   # POST request"
    },
    "busybox": {
        "basic_usage": "busybox --help                            # Show available commands\n         ls, cat, grep, etc.                       # Standard Unix utilities"
    },
    "consul": {
        "quick_start": "consul --version                          # Check version\n         consul agent -dev                         # Start dev agent\n         Web UI: http://localhost:8500             # Consul UI"
    },
    "caddy": {
        "config_info": "Caddyfile: /etc/caddy/Caddyfile\n         caddy reload --config /etc/caddy/Caddyfile  # Reload config\n         Web UI: http://localhost:80               # Default port"
    },
    "anaconda": {
        "quick_start": "conda --version                           # Check version\n         conda create -n myenv python=3.9          # Create environment\n         conda activate myenv                      # Activate environment",
        "package_mgmt": "conda install package_name               # Install package\n         conda list                                # List packages"
    },
    "jupyter": {
        "quick_start": "jupyter notebook --ip=0.0.0.0             # Start Jupyter\n         Access: http://localhost:8888             # Default port"
    }
}


def get_container_name(file_path):
    """Extract container name from file path"""
    return file_path.stem


def load_yaml_file(file_path):
    """Load YAML file"""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)


def save_yaml_file(file_path, data):
    """Save YAML file with proper formatting"""
    with open(file_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def generate_motd(container_name, category, description, ports=None):
    """Generate appropriate MOTD based on container type"""

    # Get template based on category
    template = MOTD_TEMPLATES.get(category, MOTD_TEMPLATES["generic"])

    # Extract port if available
    port = ""
    if ports and len(ports) > 0:
        port = str(ports[0]).split(":")[0] if ":" in str(ports[0]) else str(ports[0])

    # Get specific config if available
    config = CONTAINER_CONFIGS.get(container_name, {})
    lang_config = LANGUAGE_CONFIGS.get(container_name, {})
    tool_config = TOOL_CONFIGS.get(container_name, {})

    # Merge configs
    merged_config = {**config, **lang_config, **tool_config}
    if port and "port" not in merged_config:
        merged_config["port"] = port

    # Format template
    try:
        motd = template.format(
            name=description.split("-")[0].strip() if description else container_name,
            port=merged_config.get("port", "N/A"),
            basic_commands=merged_config.get("basic_commands", "Check documentation for specific commands"),
            connection_info=merged_config.get("connection_info", "Check environment variables for connection details"),
            webui=merged_config.get("webui", "Check documentation"),
            quick_start=merged_config.get("quick_start", f"{container_name} --version               # Check version"),
            package_mgmt=merged_config.get("package_mgmt", "Check documentation for package management"),
            config_info=merged_config.get("config_info", "Check documentation for configuration"),
            basic_usage=merged_config.get("basic_usage", f"{container_name} --help                   # Show help")
        )
        return motd
    except KeyError as e:
        print(f"Warning: Missing key {e} for {container_name}, using generic template")
        return MOTD_TEMPLATES["generic"].format(name=description or container_name)


def process_config_file(file_path):
    """Process a single config file and add MOTD if missing"""
    try:
        data = load_yaml_file(file_path)

        if not data or "images" not in data:
            print(f"⚠️  Skipping {file_path.name}: Invalid format")
            return False

        modified = False
        for image_name, image_config in data["images"].items():
            # Skip if already has motd
            if "motd" in image_config:
                continue

            category = image_config.get("category", "generic")
            description = image_config.get("description", image_name)
            ports = image_config.get("ports", [])

            # Generate and add MOTD
            motd = generate_motd(file_path.stem, category, description, ports)
            image_config["motd"] = motd
            modified = True

            print(f"✅ Added MOTD to {file_path.name} ({category})")

        if modified:
            # Save with preserving order (manually to keep formatting nice)
            with open(file_path, 'r') as f:
                content = f.read()

            # Add motd before scripts or at the end
            for image_name, image_config in data["images"].items():
                if "motd" in image_config:
                    motd_text = image_config["motd"]
                    # Insert motd in the YAML manually
                    image_section_start = content.find(f"{image_name}:")
                    if image_section_start != -1:
                        # Find the right place to insert
                        if "scripts:" in content[image_section_start:]:
                            insert_point = content.find("scripts:", image_section_start)
                            # Insert before scripts
                            motd_yaml = f"    motd: |{motd_text}\n    "
                            content = content[:insert_point] + motd_yaml + content[insert_point:]
                        else:
                            # Add at end of image config (before next image or end of file)
                            next_image = content.find("\n  ", image_section_start + len(image_name) + 2)
                            if next_image == -1:
                                # Last image in file
                                motd_yaml = f"    motd: |{motd_text}\n"
                                content = content + motd_yaml
                            else:
                                motd_yaml = f"    motd: |{motd_text}\n"
                                content = content[:next_image] + motd_yaml + content[next_image:]

            # Actually, let's use a safer approach - append at the end
            with open(file_path, 'r') as f:
                lines = f.readlines()

            with open(file_path, 'w') as f:
                in_image = False
                indent_level = 0
                for i, line in enumerate(lines):
                    f.write(line)

                    # Check if we're entering an image definition
                    if line.strip().endswith(":") and not line.startswith(" "):
                        in_image = False
                    elif "  " in line and line.strip().endswith(":") and len(line) - len(line.lstrip()) == 2:
                        in_image = True
                        image_name = line.strip().rstrip(":")

                    # Add MOTD if this is the last line of an image config without scripts
                    if in_image and i + 1 < len(lines):
                        next_line = lines[i + 1]
                        # Check if next line is a new image or end of file
                        if (next_line.strip() and not next_line.startswith("    ")) or i + 1 == len(lines) - 1:
                            # Add motd here
                            if "motd" in data["images"].get(image_name, {}):
                                motd_text = data["images"][image_name]["motd"]
                                f.write(f"    motd: |{motd_text}\n")

            return True
        return False

    except Exception as e:
        print(f"❌ Error processing {file_path.name}: {e}")
        return False


def main():
    """Main function"""
    config_dir = Path(CONFIG_DIR)

    if not config_dir.exists():
        print(f"❌ Directory {CONFIG_DIR} not found")
        return

    print("🔍 Scanning config files...")
    print("=" * 70)

    files_to_process = []

    # Find all files without MOTD
    for file_path in sorted(config_dir.glob("*.yml")):
        try:
            data = load_yaml_file(file_path)
            if data and "images" in data:
                for image_name, image_config in data["images"].items():
                    if "motd" not in image_config:
                        files_to_process.append(file_path)
                        break
        except Exception as e:
            print(f"⚠️  Error reading {file_path.name}: {e}")

    print(f"📋 Found {len(files_to_process)} files without MOTD\n")

    if not files_to_process:
        print("✨ All files already have MOTDs!")
        return

    # Process each file
    processed = 0
    for file_path in files_to_process:
        if process_config_file(file_path):
            processed += 1

    print("=" * 70)
    print(f"✨ Complete! Processed {processed}/{len(files_to_process)} files")


if __name__ == "__main__":
    main()
