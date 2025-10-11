#!/bin/bash

#############################################
# MOTD Management Module
#############################################

show_motd() {
  local service="$1"
  
  # First check if there's inline MOTD in config
  local inline_motd
  inline_motd=$(get_image_motd "$service")
  
  if [ -n "$inline_motd" ]; then
    clear
    echo "$inline_motd"
    echo ""
    read -r -p "Press Enter to continue..."
    return
  fi
  
  # Otherwise check for MOTD file
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
  
  if [ -n "$motd_file" ] && [ -f "$motd_file" ]; then
    clear
    cat "$motd_file"
    read -r -p ""
  fi
}
