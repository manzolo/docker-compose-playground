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
  
  if [ ! -f "$CONFIG_FILE" ]; then
    log_error "Base config file not found: $CONFIG_FILE"
    return 1
  fi
  
  cp "$CONFIG_FILE" "$MERGED_CONFIG"
  
  if [ ! -d "$CONFIG_D_DIR" ]; then
    log_info "No config.d directory found, using base config only"
    export CONFIG_FILE="$MERGED_CONFIG"
    return 0
  fi
  
  local config_files=("$CONFIG_D_DIR"/*.yml)
  local file_count=0
  
  if [ ! -e "${config_files[0]}" ]; then
    log_info "No additional config files in config.d/"
    export CONFIG_FILE="$MERGED_CONFIG"
    return 0
  fi
  
  for config_file in "$CONFIG_D_DIR"/*.yml; do
    [ -f "$config_file" ] || continue
    
    local filename=$(basename "$config_file")
    log_info "Merging: $filename"
    
    # Semplicemente appendi/sovrascrivi usando yq eval-all con strategia corretta
    yq eval-all '. as $item ireduce ({}; . *+ $item)' \
      "$MERGED_CONFIG" "$config_file" > "${MERGED_CONFIG}.tmp"
    
    if [ $? -eq 0 ]; then
      mv "${MERGED_CONFIG}.tmp" "$MERGED_CONFIG"
      file_count=$((file_count + 1))
      log_success "  ✓ Merged: $filename"
    else
      log_error "  ✗ Failed to merge: $filename"
      rm -f "${MERGED_CONFIG}.tmp"
    fi
  done
  
  local total_images=$(yq eval '.images | length' "$MERGED_CONFIG" 2>/dev/null)
  log_success "Merged base config + $file_count files = $total_images total images"
  
  export CONFIG_FILE="$MERGED_CONFIG"
  return 0
}

# Function to cleanup merged config on exit
cleanup_merged_config() {
  if [ -f "$MERGED_CONFIG" ]; then
    rm -f "$MERGED_CONFIG"
    log_info "Cleaned up merged configuration"
  fi
  
  # Cleanup any temporary files
  rm -f /tmp/playground-img-*.yml
  rm -f /tmp/playground-temp-$$.yml
}

# Function to list all config files
list_config_files() {
  echo "Base configuration:"
  echo "  - config.yml"
  
  if [ -f "$CONFIG_FILE" ]; then
    local base_count=$(yq eval '.images | length' "$CONFIG_FILE" 2>/dev/null)
    echo "    ($base_count images)"
  fi
  
  echo ""
  
  if [ -d "$CONFIG_D_DIR" ]; then
    echo "Additional configurations (config.d/):"
    local found=0
    for config_file in "$CONFIG_D_DIR"/*.yml; do
      [ -f "$config_file" ] || continue
      local img_count=$(yq eval '.images | length' "$config_file" 2>/dev/null)
      echo "  - $(basename "$config_file") ($img_count images)"
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
  
  local img_count=$(yq eval '.images | length' "$file" 2>/dev/null)
  echo "✓ Valid: $file ($img_count images)"
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

# Function to show merged config (for debugging)
show_merged_config() {
  if [ -f "$MERGED_CONFIG" ]; then
    echo "Merged configuration images:"
    yq eval '.images | keys | .[]' "$MERGED_CONFIG" 2>/dev/null | nl
  else
    echo "No merged configuration available"
  fi
}