#!/bin/bash

#############################################
# UI Management Module
#############################################

select_containers_menu() {
  local action="$1"
  local category_filter="${2:-}"
  local options=()
  
  log_info "select_containers_menu called with action=$action category_filter=$category_filter"
  
  mapfile -t images < <(get_all_images)
  
  log_info "Found ${#images[@]} images in config"
  
  # Debug: check if we got any images
  if [ ${#images[@]} -eq 0 ]; then
    log_error "No images found in config file!"
    whiptail --msgbox "ERROR: No images found in config.yml\n\nPlease check:\n1. config.yml exists\n2. YAML syntax is valid\n3. yq is installed correctly" 12 60
    return
  fi
  
  local total_processed=0
  local running_count=0
  local available_for_start=0
  local available_for_stop=0
  
  for img in "${images[@]}"; do
    # Skip empty lines
    [ -z "$img" ] && continue
    
    total_processed=$((total_processed + 1))
    
    local description=$(get_image_property "$img" "description" "No description")
    local category=$(get_image_property "$img" "category" "other")
    
    log_info "Processing image: $img (category: $category)"
    
    # Filter by category if specified
    if [ -n "$category_filter" ] && [ "$category" != "$category_filter" ]; then
      log_info "  Skipping $img - category mismatch"
      continue
    fi
    
    local is_running=""
    if is_container_running "$img"; then
      is_running="[RUNNING]"
      running_count=$((running_count + 1))
      log_info "  Container $img is RUNNING"
    else
      log_info "  Container $img is NOT running"
    fi
    
    # Logic fix: For START action, show only NON-running containers
    if [ "$action" = "start" ]; then
      if [ -z "$is_running" ]; then
        options+=("$img" "[$category] $description" off)
        available_for_start=$((available_for_start + 1))
        log_info "  Added $img to START options"
      fi
    # For STOP action, show only RUNNING containers
    elif [ "$action" = "stop" ]; then
      if [ -n "$is_running" ]; then
        options+=("$img" "[$category] $description $is_running" off)
        available_for_stop=$((available_for_stop + 1))
        log_info "  Added $img to STOP options"
      fi
    # For other actions, show all
    else
      options+=("$img" "[$category] $description $is_running" off)
      log_info "  Added $img to options (other action)"
    fi
  done
  
  log_info "Total processed: $total_processed, Running: $running_count, Available for start: $available_for_start, Available for stop: $available_for_stop"
  log_info "Options array size: ${#options[@]}"
  
  if [ ${#options[@]} -eq 0 ]; then
    if [ "$action" = "start" ]; then
      log_warn "No containers available to start (all running or filtered out)"
      whiptail --msgbox "No containers available to start.\n\nTotal images: $total_processed\nRunning: $running_count\n\nAll containers may already be running." 12 60
    elif [ "$action" = "stop" ]; then
      log_warn "No containers available to stop (none running)"
      whiptail --msgbox "No containers available to stop.\n\nNo containers are currently running." 10 60
    fi
    echo ""
    return
  fi
  
  local title="Select Container Instances"
  if [ -n "$category_filter" ]; then
    title="Select Containers - Category: $category_filter"
  fi
  
  log_info "Showing whiptail menu with ${#options[@]} options"
  
  local selected
  selected=$(whiptail --title "$title" \
    --checklist "Choose containers to $action:" \
    22 85 14 "${options[@]}" 3>&1 1>&2 2>&3) || {
    log_info "User cancelled selection"
    return 0
  }
  
  log_info "User selected: $selected"
  echo "$selected"
}

select_single_container() {
  local title="$1"
  local message="$2"
  
  local running_containers
  running_containers=$(get_running_containers)
  
  if [ -z "$running_containers" ]; then
    echo ""
    return
  fi
  
  local options=()
  while IFS= read -r service; do
    [ -z "$service" ] && continue
    
    if image_exists "$service"; then
      local description=$(get_image_property "$service" "description" "N/A")
      local category=$(get_image_property "$service" "category" "other")
      options+=("$service" "[$category] $description")
    fi
  done <<< "$running_containers"
  
  if [ ${#options[@]} -eq 0 ]; then
    echo ""
    return
  fi
  
  local selected
  selected=$(whiptail --title "$title" --menu "$message" 22 75 14 "${options[@]}" 3>&1 1>&2 2>&3) || return 0
  echo "$selected"
}

select_category_menu() {
  local categories=()
  local options=()
  
  mapfile -t categories < <(get_all_categories)
  
  for cat in "${categories[@]}"; do
    local count=$(count_images_in_category "$cat")
    if [ "$count" -gt 0 ]; then
      options+=("$cat" "$count images")
    fi
  done
  
  if [ ${#options[@]} -eq 0 ]; then
    echo ""
    return
  fi
  
  local selected
  selected=$(whiptail --title "Select Category" --menu "Choose a category:" 20 60 12 "${options[@]}" 3>&1 1>&2 2>&3) || return 0
  echo "$selected"
}

start_containers_ui() {
  local category_filter="${1:-}"
  local selected
  
  selected=$(select_containers_menu "start" "$category_filter")
  
  if [ -z "$selected" ]; then
    if [ -n "$category_filter" ]; then
      whiptail --msgbox "No available instances in category '$category_filter'." 10 55
    else
      whiptail --msgbox "No instances selected or all are already running." 10 55
    fi
    return
  fi
  
  read -r -a selected_array <<< "$selected"
  
  local success=()
  local failed=()
  
  for img in "${selected_array[@]}"; do
    img="${img//\"/}"
    if start_container "$img"; then
      success+=("$img")
    else
      failed+=("$img")
    fi
  done
  
  local msg=""
  if [ ${#success[@]} -gt 0 ]; then
    msg+="✓ Successfully started:\n$(printf '%s\n' "${success[@]}")\n"
  fi
  if [ ${#failed[@]} -gt 0 ]; then
    msg+="\n✗ Failed to start:\n$(printf '%s\n' "${failed[@]}")"
  fi
  
  whiptail --msgbox "$msg" 18 65
}

stop_containers_ui() {
  local selected
  selected=$(select_containers_menu "stop")
  
  if [ -z "$selected" ]; then
    whiptail --msgbox "No running instances to stop." 8 40
    return
  fi
  
  read -r -a selected_array <<< "$selected"
  
  local success=()
  local failed=()
  
  for img in "${selected_array[@]}"; do
    img="${img//\"/}"
    if stop_container "$img"; then
      success+=("$img")
    else
      failed+=("$img")
    fi
  done
  
  local msg=""
  if [ ${#success[@]} -gt 0 ]; then
    msg+="✓ Successfully stopped:\n$(printf '%s\n' "${success[@]}")\n"
  fi
  if [ ${#failed[@]} -gt 0 ]; then
    msg+="\n✗ Failed to stop:\n$(printf '%s\n' "${failed[@]}")"
  fi
  
  whiptail --msgbox "$msg" 18 65
}

enter_container_ui() {
  cleanup_dead_containers
  
  local service
  service=$(select_single_container "Enter Container" "Choose a container:")
  
  if [ -z "$service" ]; then
    whiptail --msgbox "No running containers available." 8 50
    return
  fi
  
  enter_container "$service" || whiptail --msgbox "Failed to enter $service." 10 60
}

show_dashboard() {
  clear
  print_header
  
  local running=$(docker ps --filter "label=playground.managed=true" -q | wc -l)
  local total=$(get_total_image_count)
  
  echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${CYAN}║                    PLAYGROUND DASHBOARD                    ║${NC}"
  echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
  echo ""
  
  echo -e "${BLUE}📊 Statistics:${NC}"
  echo -e "   Active Containers: ${GREEN}$running${NC} / ${YELLOW}$total${NC} available"
  echo ""
  
  if [ $running -gt 0 ]; then
    echo -e "${BLUE}🔥 Running Containers:${NC}"
    docker ps --filter "label=playground.managed=true" --format "{{.Names}} {{.Image}}" 2>/dev/null | while read -r name image; do
      echo -e "   ${GREEN}•${NC} $name ${CYAN}($image)${NC}"
    done
    echo ""
  fi
  
  echo -e "${BLUE}📦 Images by Category:${NC}"
  mapfile -t categories < <(get_all_categories)
  for cat in "${categories[@]}"; do
    local count=$(count_images_in_category "$cat")
    if [ "$count" -gt 0 ]; then
      printf "   ${YELLOW}%-15s${NC}: %2d images\n" "$cat" "$count"
    fi
  done
  
  echo ""
  echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  read -p "Press Enter to continue..." -r
}

restart_container_ui() {
  local service
  service=$(select_single_container "Restart Container" "Choose a container to restart:")
  
  if [ -z "$service" ]; then
    whiptail --msgbox "No running containers available." 8 50
    return
  fi
  
  if whiptail --yesno "Restart container: $service?" 8 50; then
    if stop_container "$service" && start_container "$service"; then
      whiptail --msgbox "✓ Container $service restarted successfully" 8 50
    else
      whiptail --msgbox "✗ Failed to restart $service" 8 50
    fi
  fi
}

show_container_logs_ui() {
  local service
  service=$(select_single_container "View Logs" "Choose a container:")
  
  if [ -z "$service" ]; then
    whiptail --msgbox "No running containers available." 8 50
    return
  fi
  
  clear
  echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║  Logs for: playground-$service"
  echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
  echo -e "${YELLOW}Press Ctrl+C to exit${NC}"
  echo ""
  
  docker logs -f "playground-$service" 2>&1 || {
    echo -e "${RED}Failed to fetch logs${NC}"
    read -p "Press Enter to continue..." -r
  }
}

show_container_stats_ui() {
  clear
  echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║  Container Statistics (Press Ctrl+C to exit)       ║${NC}"
  echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
  echo ""
  
  # Get list of playground container IDs
  local container_ids
  container_ids=$(docker ps -q --filter "label=playground.managed=true" 2>/dev/null)
  
  if [ -z "$container_ids" ]; then
    echo -e "${YELLOW}No playground containers running${NC}"
    echo ""
    read -p "Press Enter to continue..." -r
    return
  fi
  
  # Setup trap to handle Ctrl+C cleanly
  trap 'echo ""; echo "Exiting stats..."; return 0' INT
  
  # Show live stats
  docker stats $container_ids || true
  
  # Remove trap
  trap - INT
}

search_images_ui() {
  local search_term
  search_term=$(whiptail --inputbox "Enter search term:" 10 60 3>&1 1>&2 2>&3)
  
  if [ -z "$search_term" ]; then
    return
  fi
  
  local results=""
  mapfile -t images < <(get_all_images)
  
  for img in "${images[@]}"; do
    local description=$(get_image_property "$img" "description" "")
    local category=$(get_image_property "$img" "category" "")
    
    if echo "$img $description $category" | grep -qi "$search_term"; then
      local is_running=""
      if is_container_running "$img"; then
        is_running="[RUNNING]"
      fi
      results+="$img - [$category] $description $is_running\n"
    fi
  done
  
  if [ -z "$results" ]; then
    whiptail --msgbox "No images found matching '$search_term'" 10 60
  else
    whiptail --msgbox "Search results for '$search_term':\n\n$results" 22 80 --scrolltext
  fi
}

browse_catalog_ui() {
  local category
  category=$(select_category_menu)
  
  if [ -z "$category" ]; then
    return
  fi
  
  local catalog=""
  mapfile -t images < <(get_images_by_category "$category")
  
  for img in "${images[@]}"; do
    local description=$(get_image_property "$img" "description" "")
    local image_name=$(get_image_property "$img" "image" "")
    local is_running=""
    if is_container_running "$img"; then
      is_running="[RUNNING]"
    fi
    catalog+="$img\n  Image: $image_name\n  Description: $description $is_running\n\n"
  done
  
  whiptail --msgbox "Category: $category\n\n$catalog" 22 80 --scrolltext
}

show_system_info_ui() {
  local info=""
  info+="Docker Version:\n"
  info+="$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo 'N/A')\n\n"
  info+="Docker Compose Version:\n"
  info+="$(docker compose version 2>/dev/null || echo 'N/A')\n\n"
  info+="Disk Usage:\n"
  info+="$(docker system df 2>/dev/null || echo 'N/A')\n\n"
  info+="Network:\n"
  info+="$(docker network ls --filter name=$NETWORK_NAME 2>/dev/null || echo 'N/A')\n"
  
  whiptail --msgbox "System Information\n\n$info" 22 80 --scrolltext
}

show_help_ui() {
  local help_text=""
  help_text+="Docker Playground Manager v3.0\n"
  help_text+="================================\n\n"
  help_text+="FEATURES:\n"
  help_text+="• Start/Stop multiple containers\n"
  help_text+="• Browse by category\n"
  help_text+="• Interactive shell access\n"
  help_text+="• MOTD (Message of the Day) support\n"
  help_text+="• Pre/Post scripts support\n"
  help_text+="• Shared volume at /shared\n\n"
  help_text+="SHARED VOLUME:\n"
  help_text+="Host: $SHARED_DIR\n"
  help_text+="Container: /shared\n\n"
  help_text+="CONFIGURATION:\n"
  help_text+="Edit config.yml to add/modify images\n"
  help_text+="Add scripts to scripts/ directory\n"
  help_text+="Customize MOTD in config or motd/ files\n"
  
  whiptail --msgbox "$help_text" 22 70 --scrolltext
}

cleanup_all_ui() {
  if whiptail --yesno "This will stop and remove ALL playground containers.\n\nAre you sure?" 12 60; then
    if whiptail --yesno "Really remove ALL containers? This cannot be undone!" 10 60; then
      docker ps -a --filter "label=playground.managed=true" -q | xargs -r docker stop 2>/dev/null || true
      docker ps -a --filter "label=playground.managed=true" -q | xargs -r docker rm 2>/dev/null || true
      log_success "All playground containers removed"
      whiptail --msgbox "✓ All playground containers have been removed" 8 55
    fi
  fi
}

main_menu() {
  while true; do
    print_header
    
    local running=$(docker ps --filter "label=playground.managed=true" -q | wc -l)
    local total=$(get_total_image_count)
    echo -e "${CYAN}Status:${NC} ${GREEN}$running${NC} running / ${YELLOW}$total${NC} available\n"
    
    local choice
    choice=$(whiptail --title "Docker Playground Manager v3.0" \
      --menu "Choose an action:" 25 75 17 \
      "1" "▶️  Start containers              [Container]" \
      "2" "🎯 Start by category             [Container]" \
      "3" "⏹️  Stop containers               [Container]" \
      "4" "💻 Enter a container             [Container]" \
      "5" "📋 List active containers        [Monitor]" \
      "6" "📊 View container logs           [Monitor]" \
      "7" "🔄 Restart container             [Monitor]" \
      "8" "📈 Container statistics          [Monitor]" \
      "9" "📺 Dashboard                     [Monitor]" \
      "10" "🔍 Search images                 [Tools]" \
      "11" "📚 Browse catalog                [Tools]" \
      "12" "⚙  System information            [Tools]" \
      "13" "❓ Help                          [Tools]" \
      "14" "🐛 Debug config                  [Tools]" \
      "15" "📤 Export logs                   [Maintenance]" \
      "16" "🧹 Cleanup (remove all)          [Maintenance]" \
      "17" "❌ Exit                          " 3>&1 1>&2 2>&3) || continue
    
    case $choice in
      1) start_containers_ui ;;
      2) 
        local category
        category=$(select_category_menu)
        [ -n "$category" ] && start_containers_ui "$category"
        ;;
      3) stop_containers_ui ;;
      4) enter_container_ui ;;
      5) 
        local output
        output=$(docker ps --filter "label=playground.managed=true" --filter "status=running" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" 2>/dev/null)
        [ -n "$output" ] && whiptail --title "Active Containers" --msgbox "$output" 22 80 --scrolltext || whiptail --msgbox "No active containers." 8 40
        ;;
      6) show_container_logs_ui ;;
      7) restart_container_ui ;;
      8) show_container_stats_ui ;;
      9) show_dashboard ;;
      10) search_images_ui ;;
      11) browse_catalog_ui ;;
      12) show_system_info_ui ;;
      13) show_help_ui ;;
      14) 
        clear
        debug_config
        read -p "Press Enter to continue..." -r
        ;;
      15) export_logs ;;
      16) cleanup_all_ui ;;
      17)
        clear
        echo -e "${GREEN}Thank you for using Docker Playground! 🐳${NC}"
        exit 0
        ;;
    esac
  done
}