#!/bin/bash

#############################################
# Configuration Management Module
#############################################

# Get image property from config
get_image_property() {
  local image_name="$1"
  local property="$2"
  local default="${3:-}"
  
  local value
  value=$(yq eval ".images.\"$image_name\".${property}" "$CONFIG_FILE" 2>/dev/null)
  
  # If null or empty, return default
  if [ "$value" = "null" ] || [ -z "$value" ]; then
    echo "$default"
  else
    echo "$value"
  fi
}

# Get all images from config
get_all_images() {
  yq eval '.images | keys | .[]' "$CONFIG_FILE" 2>/dev/null | sort || true
}

# Get images by category
get_images_by_category() {
  local category="$1"
  yq eval ".images | to_entries[] | select(.value.category == \"$category\") | .key" "$CONFIG_FILE" 2>/dev/null | sort || true
}

# Get all categories
get_all_categories() {
  yq eval '.images | to_entries[].value.category' "$CONFIG_FILE" 2>/dev/null | sort -u || true
}

# Count images in category
count_images_in_category() {
  local category="$1"
  yq eval ".images | to_entries[] | select(.value.category == \"$category\") | .key" "$CONFIG_FILE" 2>/dev/null | wc -l
}

# Get total image count
get_total_image_count() {
  yq eval '.images | length' "$CONFIG_FILE" 2>/dev/null || echo "0"
}

# Check if image exists in config
image_exists() {
  local image_name="$1"
  yq eval ".images.\"$image_name\"" "$CONFIG_FILE" 2>/dev/null | grep -q "image:" 
  return $?
}

# Get MOTD for image
get_image_motd() {
  local image_name="$1"
  local value
  value=$(yq eval ".images.\"$image_name\".motd" "$CONFIG_FILE" 2>/dev/null)
  
  if [ "$value" = "null" ] || [ -z "$value" ]; then
    echo ""
  else
    echo "$value"
  fi
}

# Get post-start script for image
get_post_start_script() {
  local image_name="$1"
  local value
  value=$(yq eval ".images.\"$image_name\".scripts.post_start" "$CONFIG_FILE" 2>/dev/null)
  
  if [ "$value" = "null" ] || [ -z "$value" ]; then
    echo ""
  else
    echo "$value"
  fi
}

# Get pre-stop script for image
get_pre_stop_script() {
  local image_name="$1"
  local value
  value=$(yq eval ".images.\"$image_name\".scripts.pre_stop" "$CONFIG_FILE" 2>/dev/null)
  
  if [ "$value" = "null" ] || [ -z "$value" ]; then
    echo ""
  else
    echo "$value"
  fi
}

# Debug function to test config reading
debug_config() {
  echo "=== Config Debug Info ==="
  echo "Config file: $CONFIG_FILE"
  echo "File exists: $([ -f "$CONFIG_FILE" ] && echo "YES" || echo "NO")"
  echo ""
  echo "Total images found: $(get_total_image_count)"
  echo ""
  echo "First 5 images:"
  get_all_images | head -5
  echo ""
  echo "Categories:"
  get_all_categories
  echo ""
  echo "Sample image (mysql-8):"
  echo "  Image: $(get_image_property 'mysql-8' 'image')"
  echo "  Description: $(get_image_property 'mysql-8' 'description')"
  echo "  Category: $(get_image_property 'mysql-8' 'category')"
  echo "  Post-start script: $(get_post_start_script 'mysql-8')"
  echo "  Pre-stop script: $(get_pre_stop_script 'mysql-8')"
  echo ""
  echo "Sample image (ubuntu-24):"
  echo "  MOTD length: $(get_image_motd 'ubuntu-24' | wc -c) chars"
  echo "======================="
}