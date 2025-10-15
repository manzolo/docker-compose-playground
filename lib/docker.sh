#!/bin/bash

#############################################
# Docker Operations Module
#############################################

generate_compose() {
  local selected=("$@")
  
  # Inizializza il file docker-compose.yml
  cat <<EOF > "$COMPOSE_FILE"
networks:
  $NETWORK_NAME:
    driver: bridge
EOF

  # Raccogli tutti i named volumes (top-level)
  local named_volumes=()
  for img in "${selected[@]}"; do
    img="${img//\"/}"
    local volume_count=$(yq eval ".images.\"$img\".volumes | length" "$CONFIG_FILE" 2>/dev/null || echo "0")
    if [ "$volume_count" -gt 0 ]; then
      for ((i=0; i<volume_count; i++)); do
        local vol_type=$(yq eval ".images.\"$img\".volumes[$i].type" "$CONFIG_FILE" 2>/dev/null || echo "named")
        local vol_name=$(yq eval ".images.\"$img\".volumes[$i].name" "$CONFIG_FILE" 2>/dev/null || echo "")
        if [ "$vol_type" = "named" ] && [ -n "$vol_name" ] && [ "$vol_name" != "null" ]; then
          if [[ ! " ${named_volumes[@]} " =~ " ${vol_name} " ]]; then
            named_volumes+=("$vol_name")
            echo "  $vol_name:" >> "$COMPOSE_FILE"
          fi
        fi
      done
    fi
  done

  echo "" >> "$COMPOSE_FILE"
  echo "services:" >> "$COMPOSE_FILE"

  for img in "${selected[@]}"; do
    img="${img//\"/}"
    
    # Proprietà di base dell'immagine
    local image_name=$(get_image_property "$img" "image")
    local keep_alive_cmd=$(get_image_property "$img" "keep_alive_cmd" "sleep infinity")
    local privileged=$(get_image_property "$img" "privileged" "false")
    
    # Scrivi la definizione del servizio
    cat <<EOF >> "$COMPOSE_FILE"
  $img:
    image: $image_name
    container_name: playground-$img
    hostname: $img
    networks:
      - $NETWORK_NAME
    volumes:
      - $SHARED_DIR:/shared
EOF

    # Aggiungi volumi specifici (bind, named, file)
    local volume_count=$(yq eval ".images.\"$img\".volumes | length" "$CONFIG_FILE" 2>/dev/null || echo "0")
    if [ "$volume_count" -gt 0 ]; then
      for ((i=0; i<volume_count; i++)); do
        local vol_type=$(yq eval ".images.\"$img\".volumes[$i].type" "$CONFIG_FILE" 2>/dev/null || echo "named")
        local vol_path=$(yq eval ".images.\"$img\".volumes[$i].path" "$CONFIG_FILE" 2>/dev/null)
        local readonly=$(yq eval ".images.\"$img\".volumes[$i].readonly" "$CONFIG_FILE" 2>/dev/null || echo "false")
        
        if [ "$vol_type" = "named" ]; then
          local vol_name=$(yq eval ".images.\"$img\".volumes[$i].name" "$CONFIG_FILE" 2>/dev/null)
          if [ -n "$vol_name" ] && [ "$vol_name" != "null" ]; then
            if [ "$readonly" = "true" ]; then
              echo "      - ${vol_name}:${vol_path}:ro" >> "$COMPOSE_FILE"
            else
              echo "      - ${vol_name}:${vol_path}" >> "$COMPOSE_FILE"
            fi
          fi
        elif [ "$vol_type" = "bind" ] || [ "$vol_type" = "file" ]; then
          local vol_host=$(yq eval ".images.\"$img\".volumes[$i].host" "$CONFIG_FILE" 2>/dev/null)
          if [ -n "$vol_host" ] && [ "$vol_host" != "null" ]; then
            # Converti percorsi relativi in assoluti
            if [[ ! "$vol_host" = /* ]]; then
              vol_host="${SCRIPT_DIR}/${vol_host}"
            fi
            
            # Crea directory/file se non esistono
            if [ "$vol_type" = "bind" ]; then
              mkdir -p "$vol_host"
            elif [ "$vol_type" = "file" ]; then
              mkdir -p "$(dirname "$vol_host")"
              touch "$vol_host"
            fi
            
            if [ "$readonly" = "true" ]; then
              echo "      - ${vol_host}:${vol_path}:ro" >> "$COMPOSE_FILE"
            else
              echo "      - ${vol_host}:${vol_path}" >> "$COMPOSE_FILE"
            fi
          fi
        fi
      done
    fi

    # Aggiungi il resto delle proprietà del servizio
    cat <<EOF >> "$COMPOSE_FILE"
    command: $keep_alive_cmd
    stdin_open: true
    tty: true
    restart: unless-stopped
    labels:
      - "playground.managed=true"
      - "playground.image=$img"
EOF

    # Privileged
    if [ "$privileged" = "true" ]; then
      echo "    privileged: true" >> "$COMPOSE_FILE"
    fi
    
    # Environment variables
    local env_keys=$(yq eval ".images.\"$img\".environment // {} | keys | .[]" "$CONFIG_FILE" 2>/dev/null || echo "")
    if [ -n "$env_keys" ]; then
      echo "    environment:" >> "$COMPOSE_FILE"
      while IFS= read -r key; do
        [ -z "$key" ] && continue
        local value=$(yq eval ".images.\"$img\".environment.\"$key\"" "$CONFIG_FILE")
        echo "      $key: $value" >> "$COMPOSE_FILE"
      done <<< "$env_keys"
    fi
    
    # Ports
    local port_count=$(yq eval ".images.\"$img\".ports | length" "$CONFIG_FILE" 2>/dev/null || echo "0")
    if [ "$port_count" -gt 0 ]; then
      echo "    ports:" >> "$COMPOSE_FILE"
      for ((i=0; i<port_count; i++)); do
        local port=$(yq eval ".images.\"$img\".ports[$i]" "$CONFIG_FILE")
        echo "      - \"$port\"" >> "$COMPOSE_FILE"
      done
    fi
    
    echo "" >> "$COMPOSE_FILE"
  done
  
  log_info "Generated docker-compose.yml with services: ${selected[*]}"
}

start_container() {
  local image_name="$1"
  
  log_info "Starting container: $image_name"
  
  # First, ensure the container is completely stopped and removed
  if docker ps -a -q --filter "name=^playground-${image_name}$" 2>/dev/null | grep -q .; then
    log_info "Removing existing container: $image_name"
    docker stop "playground-$image_name" 2>/dev/null || true
    docker rm "playground-$image_name" 2>/dev/null || true
  fi
  
  # Generate fresh compose file
  generate_compose "$image_name"
  
  # Start the container
  if docker compose -f "$COMPOSE_FILE" up -d "$image_name" 2>&1 | tee -a "$LOG_FILE"; then
    log_success "Started container: $image_name"
    
    # Wait for container to be fully running
    local max_wait=10
    local count=0
    while [ $count -lt $max_wait ]; do
      if docker ps -q --filter "name=^playground-${image_name}$" --filter "status=running" 2>/dev/null | grep -q .; then
        log_info "Container $image_name is now running"
        break
      fi
      sleep 1
      count=$((count + 1))
    done
    
    if [ $count -ge $max_wait ]; then
      log_warn "Container $image_name may not be fully started yet"
    fi
    
    # Run post-start script (file-based or inline)
    execute_post_start_script "$image_name"
    
    return 0
  else
    log_error "Failed to start container: $image_name"
    return 1
  fi
}

stop_container() {
  local image_name="$1"
  
  log_info "Stopping container: $image_name"
  
  # Run pre-stop script (file-based or inline)
  execute_pre_stop_script "$image_name"
  
  # Stop and remove container
  if docker stop "playground-$image_name" 2>/dev/null && docker rm "playground-$image_name" 2>/dev/null; then
    log_success "Stopped container: $image_name"
    return 0
  else
    log_error "Failed to stop container: $image_name (may not exist)"
    return 1
  fi
}

# New function to execute post-start scripts (file or inline)
execute_post_start_script() {
  local image_name="$1"
  
  # Check for inline script first
  local inline_script
  inline_script=$(yq eval ".images.\"$image_name\".scripts.post_start.inline" "$CONFIG_FILE" 2>/dev/null)
  
  if [ -n "$inline_script" ] && [ "$inline_script" != "null" ]; then
    log_info "Running inline post-start script for: $image_name"
    
    # Create temporary script file
    local temp_script="/tmp/playground-post-start-$image_name-$$.sh"
    echo "$inline_script" > "$temp_script"
    chmod +x "$temp_script"
    
    # Execute inline script
    bash "$temp_script" "$image_name" 2>&1 | tee -a "$LOG_FILE" || log_warn "Inline post-start script failed"
    
    # Cleanup
    rm -f "$temp_script"
    return
  fi
  
  # Check for file-based script
  local post_script=$(get_post_start_script "$image_name")
  if [ -n "$post_script" ]; then
    local script_path="$SCRIPTS_DIR/$post_script"
    if [ -f "$script_path" ]; then
      log_info "Running post-start script: $post_script"
      bash "$script_path" "$image_name" 2>&1 | tee -a "$LOG_FILE" || log_warn "Post-start script failed: $post_script"
    else
      log_warn "Post-start script not found: $script_path"
    fi
  fi
}

# New function to execute pre-stop scripts (file or inline)
execute_pre_stop_script() {
  local image_name="$1"
  
  # Check for inline script first
  local inline_script
  inline_script=$(yq eval ".images.\"$image_name\".scripts.pre_stop.inline" "$CONFIG_FILE" 2>/dev/null)
  
  if [ -n "$inline_script" ] && [ "$inline_script" != "null" ]; then
    log_info "Running inline pre-stop script for: $image_name"
    
    # Create temporary script file
    local temp_script="/tmp/playground-pre-stop-$image_name-$$.sh"
    echo "$inline_script" > "$temp_script"
    chmod +x "$temp_script"
    
    # Execute inline script
    bash "$temp_script" "$image_name" 2>&1 | tee -a "$LOG_FILE" || log_warn "Inline pre-stop script failed"
    
    # Cleanup
    rm -f "$temp_script"
    return
  fi
  
  # Check for file-based script
  local pre_script=$(get_pre_stop_script "$image_name")
  if [ -n "$pre_script" ]; then
    local script_path="$SCRIPTS_DIR/$pre_script"
    if [ -f "$script_path" ]; then
      log_info "Running pre-stop script: $pre_script"
      bash "$script_path" "$image_name" 2>&1 | tee -a "$LOG_FILE" || log_warn "Pre-stop script failed: $pre_script"
    else
      log_warn "Pre-stop script not found: $script_path"
    fi
  fi
}

get_running_containers() {
  docker ps --filter "label=playground.managed=true" --filter "status=running" --format "{{.Names}}" 2>/dev/null | sed 's/playground-//' | sort -u || true
}

is_container_running() {
  local image_name="$1"
  
  # Check if container exists and is running
  if docker ps -q --filter "name=^playground-${image_name}$" --filter "status=running" 2>/dev/null | grep -q .; then
    return 0
  else
    return 1
  fi
}

enter_container() {
  local service="$1"
  
  if ! is_container_running "$service"; then
    log_error "Container $service is not running"
    whiptail --msgbox "Container $service is not running!" 8 50
    return 1
  fi
  
  log_info "Entering container: $service"
  
  # Show MOTD BEFORE entering container
  local inline_motd
  inline_motd=$(get_image_motd "$service")
  
  # DEBUG
  log_info "MOTD length for $service: ${#inline_motd}"
  
  if [ -n "$inline_motd" ]; then
    log_info "Showing inline MOTD for $service"
    # Show inline MOTD - force output to TTY
    clear > /dev/tty
    echo "$inline_motd" > /dev/tty
    echo "" > /dev/tty
    log_info "User pressed Enter after MOTD"
  else
    log_info "No inline MOTD, checking for file"
    # Check for MOTD file
    local motd_file=""
    
    case "$service" in
      mysql*) motd_file="$MOTD_DIR/mysql.txt" ;;
      postgres*) motd_file="$MOTD_DIR/postgres.txt" ;;
      mongodb*) motd_file="$MOTD_DIR/mongodb.txt" ;;
      redis*) motd_file="$MOTD_DIR/redis.txt" ;;
      docker-dind) motd_file="$MOTD_DIR/docker.txt" ;;
      python*) motd_file="$MOTD_DIR/python.txt" ;;
      node*) motd_file="$MOTD_DIR/node.txt" ;;
      golang*) motd_file="$MOTD_DIR/golang.txt" ;;
      nginx*) motd_file="$MOTD_DIR/nginx.txt" ;;
      rust*) motd_file="$MOTD_DIR/rust.txt" ;;
      elasticsearch) motd_file="$MOTD_DIR/elasticsearch.txt" ;;
    esac
    
    log_info "MOTD file for $service: $motd_file"
    
    if [ -n "$motd_file" ] && [ -f "$motd_file" ]; then
      log_info "Found MOTD file: $motd_file"
      clear > /dev/tty
      cat "$motd_file" > /dev/tty
      echo "" > /dev/tty
    fi
  fi
  
  local shell_cmd=$(get_image_property "$service" "shell" "/bin/bash")
  
  # DON'T clear - just show entering message below the MOTD
  echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}" > /dev/tty
  echo -e "${GREEN}║  Entering container: playground-$service" > /dev/tty
  echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}" > /dev/tty
  echo -e "${YELLOW}Type 'exit' to return to the menu${NC}" > /dev/tty
  echo "" > /dev/tty
  
  docker exec -it "playground-$service" "$shell_cmd" || {
    log_error "Failed to enter $service"
    return 1
  }
  
  log_info "Exited container: $service"
  return 0
}