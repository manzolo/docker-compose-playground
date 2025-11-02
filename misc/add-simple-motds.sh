#!/bin/bash
# Script to add simple MOTDs to config files that don't have them

CONFIG_DIR="config.d"

# Function to add MOTD to a YAML file
add_motd() {
    local file="$1"
    local container_name=$(basename "$file" .yml)
    local description=$(grep "description:" "$file" | sed 's/.*description: *//' | tr -d '"')
    local category=$(grep "category:" "$file" | sed 's/.*category: *//' | tr -d '"')

    # Skip if already has motd
    if grep -q "motd:" "$file"; then
        echo "⏭️  Skipping $file (already has MOTD)"
        return
    fi

    # Create a simple MOTD based on category
    local motd=""

    case "$category" in
        database)
            motd="    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║            $description - Quick Reference                    ║
      ╚══════════════════════════════════════════════════════════════╝

      📊 Database Container:
         This is a database server container.
         Check the container logs and environment variables for connection details.

      📁 Useful Directories:
         /shared                                       # Shared with host

      💾 Data Persistence:
         Use /shared directory for storing backups

      💡 Tips:
         • Keep database dumps in /shared for persistence
         • Check container logs for startup messages
         • Connection details are in environment variables"
            ;;
        programming)
            motd="    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║          $description - Development Environment              ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Development Container:
         This container provides a development environment.

      📁 Useful Directories:
         /shared                                       # Shared with host
         /shared/projects                              # Store your projects

      💡 Tips:
         • Keep your code in /shared for persistence
         • Use /shared directory for data exchange with host
         • Check official documentation for specific commands"
            ;;
        webserver)
            motd="    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║               $description - Web Server                      ║
      ╚══════════════════════════════════════════════════════════════╝

      🌐 Web Server Container:
         Check the ports configuration for access URL.

      📁 Content Directories:
         /shared                                       # Shared with host

      💡 Tips:
         • Place web content in /shared for persistence
         • Check container logs for server status
         • Refer to official documentation for configuration"
            ;;
        utility|devops|messaging)
            motd="    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                $description - Quick Reference                ║
      ╚══════════════════════════════════════════════════════════════╝

      🔧 Utility Container:
         This is a ${category} tool container.

      📁 Useful Directories:
         /shared                                       # Shared with host

      💡 Tips:
         • Use /shared directory for persistence
         • Check official documentation for usage
         • Configuration files can be stored in /shared"
            ;;
        *)
            motd="    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                $description - Quick Reference                ║
      ╚══════════════════════════════════════════════════════════════╝

      📁 Useful Directories:
         /shared                                       # Shared with host

      💡 Tips:
         • Use /shared directory for persistence
         • Check container documentation for specific usage
         • Logs and data can be stored in /shared"
            ;;
    esac

    # Add MOTD at the end of the file
    echo "$motd" >> "$file"
    echo "✅ Added MOTD to $file ($category: $description)"
}

# Main script
echo "🔍 Scanning config files in $CONFIG_DIR..."
echo "=" * 70

count=0
for file in "$CONFIG_DIR"/*.yml; do
    if [ -f "$file" ]; then
        add_motd "$file"
        ((count++))
    fi
done

echo "=" * 70
echo "✨ Processed $count files"
