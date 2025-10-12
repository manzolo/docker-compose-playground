#!/bin/bash

#############################################
# Config Loader Module
# Loads and merges config.yml with config.d/*.yml files
#############################################

CONFIG_D_DIR="${SCRIPT_DIR}/config.d"
MERGED_CONFIG="/tmp/playground-merged-config-$$.yml"

# Function to merge all config files
merge_configs() {
  log_info "Merging configuration files..."
  
  # Start with base config.yml
  if [ ! -f "$CONFIG_FILE" ]; then
    log_error "Base config file not found: $CONFIG_FILE"
    return 1
  fi
  
  cp "$CONFIG_FILE" "$MERGED_CONFIG"
  
  # Check if config.d directory exists
  if [ ! -d "$CONFIG_D_DIR" ]; then
    log_info "No config.d directory found, using base config only"
    export CONFIG_FILE="$MERGED_CONFIG"
    return 0
  fi
  
  # Count files to merge
  local config_files=("$CONFIG_D_DIR"/*.yml)
  local file_count=0
  
  # Check if any yml files exist
  if [ ! -e "${config_files[0]}" ]; then
    log_info "No additional config files in config.d/"
    export CONFIG_FILE="$MERGED_CONFIG"
    return 0
  fi
  
  # Merge each config.d/*.yml file
  for config_file in "$CONFIG_D_DIR"/*.yml; do
    [ -f "$config_file" ] || continue
    
    local filename=$(basename "$config_file")
    log_info "Merging: $filename"
    
    # Extract images from the config.d file and merge
    local temp_merged="/tmp/playground-temp-$$.yml"
    
    # Use yq to merge the images section
    yq eval-all 'select(fileIndex == 0) * select(fileIndex == 1)' \
      "$MERGED_CONFIG" "$config_file" > "$temp_merged"
    
    if [ $? -eq 0 ]; then
      mv "$temp_merged" "$MERGED_CONFIG"
      file_count=$((file_count + 1))
      log_info "✓ Merged: $filename"
    else
      log_error "✗ Failed to merge: $filename"
      rm -f "$temp_merged"
    fi
  done
  
  log_success "Merged base config + $file_count additional files"
  
  # Export the merged config path for use by other modules
  export CONFIG_FILE="$MERGED_CONFIG"
  
  return 0
}

# Function to cleanup merged config on exit
cleanup_merged_config() {
  if [ -f "$MERGED_CONFIG" ]; then
    rm -f "$MERGED_CONFIG"
    log_info "Cleaned up merged configuration"
  fi
}

# Function to list all config files
list_config_files() {
  echo "Base configuration:"
  echo "  - config.yml"
  echo ""
  
  if [ -d "$CONFIG_D_DIR" ]; then
    echo "Additional configurations (config.d/):"
    local found=0
    for config_file in "$CONFIG_D_DIR"/*.yml; do
      [ -f "$config_file" ] || continue
      echo "  - $(basename "$config_file")"
      found=1
    done
    
    if [ $found -eq 0 ]; then
      echo "  (none)"
    fi
  else
    echo "config.d/ directory not found"
  fi
}

# Function to validate a config file
validate_config_file() {
  local file="$1"
  
  if [ ! -f "$file" ]; then
    echo "✗ File not found: $file"
    return 1
  fi
  
  # Check YAML syntax
  if ! yq eval '.' "$file" &>/dev/null; then
    echo "✗ Invalid YAML syntax: $file"
    return 1
  fi
  
  # Check if it has images section
  if ! yq eval '.images' "$file" &>/dev/null; then
    echo "✗ No 'images' section found: $file"
    return 1
  fi
  
  echo "✓ Valid: $file"
  return 0
}

# Function to validate all config files
validate_all_configs() {
  echo "Validating configuration files..."
  echo ""
  
  local errors=0
  
  # Validate base config
  if ! validate_config_file "$CONFIG_FILE"; then
    errors=$((errors + 1))
  fi
  
  # Validate config.d files
  if [ -d "$CONFIG_D_DIR" ]; then
    for config_file in "$CONFIG_D_DIR"/*.yml; do
      [ -f "$config_file" ] || continue
      if ! validate_config_file "$config_file"; then
        errors=$((errors + 1))
      fi
    done
  fi
  
  echo ""
  if [ $errors -eq 0 ]; then
    echo "✓ All configuration files are valid"
    return 0
  else
    echo "✗ Found $errors error(s) in configuration files"
    return 1
  fi
}