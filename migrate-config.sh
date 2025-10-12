#!/bin/bash

##############################################
# Migrate images with MOTD/scripts to config.d/
##############################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_D_DIR="$SCRIPT_DIR/config.d"
CONFIG_FILE="$SCRIPT_DIR/config.yml"

# Create config.d directory
mkdir -p "$CONFIG_D_DIR"

echo "🔄 Starting migration to config.d/"
echo ""

# List of images to migrate (those with MOTD and/or scripts)
IMAGES_TO_MIGRATE=(
  "ubuntu-24"
  "alpine-3.19"
  "python-3.13"
  "node-22"
  "golang-1.22"
  "rust-1.75"
  "mysql-8"
  "postgres-16"
  "mongodb-7"
  "redis-7"
  "nginx-latest"
  "docker-dind"
)

migrate_count=0

for image in "${IMAGES_TO_MIGRATE[@]}"; do
  echo "📦 Migrating: $image"
  
  # Extract image configuration
  if ! yq eval ".images.\"$image\"" "$CONFIG_FILE" &>/dev/null; then
    echo "  ⚠️  Image $image not found in config.yml, skipping..."
    continue
  fi
  
  # Create individual config file
  cat > "$CONFIG_D_DIR/${image}.yml" <<EOF
images:
  $image:
EOF
  
  # Copy the entire image configuration
  yq eval ".images.\"$image\"" "$CONFIG_FILE" | sed 's/^/    /' >> "$CONFIG_D_DIR/${image}.yml"
  
  echo "  ✓ Created: config.d/${image}.yml"
  migrate_count=$((migrate_count + 1))
done

echo ""
echo "✅ Migration complete!"
echo "   Migrated $migrate_count images to config.d/"
echo ""
echo "📝 Next steps:"
echo "   1. Review the generated files in config.d/"
echo "   2. Remove migrated images from config.yml to avoid duplicates"
echo "   3. Run: ./playground.sh to test"
echo ""
echo "💡 To keep both (merge at runtime):"
echo "   - Leave images in config.yml"
echo "   - config.d/ will override/extend them"