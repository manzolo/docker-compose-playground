#!/bin/bash

#############################################
# Docker Playground Manager
# A professional tool for managing Docker development environments
# Version: 2.4
#############################################

set -euo pipefail

# Configuration
CONFIG_FILE="config.yml"
COMPOSE_FILE="docker-compose.yml"
SHARED_DIR="$(pwd)/shared-volumes"
LOG_FILE="$(pwd)/playground.log"
NETWORK_NAME="playground-network"
PLAYGROUND_LABEL="playground.managed=true"
MOTD_DIR="$(pwd)/motd"

# Colors for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

#############################################
# Utility Functions
#############################################

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

print_header() {
  clear
  echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
  echo -e "${BLUE}║       🐳 Docker Playground Manager v2.4           ║${NC}"
  echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
  echo ""
}

check_dependencies() {
  local missing_deps=()
  
  if ! command -v docker &>/dev/null; then
    missing_deps+=("docker")
  fi
  
  if ! command -v docker compose &>/dev/null && ! command -v docker-compose &>/dev/null; then
    missing_deps+=("docker-compose")
  fi
  
  if ! command -v yq &>/dev/null; then
    if whiptail --yesno "yq is not installed. Install it via snap?" 10 60; then
      sudo snap install yq || {
        whiptail --msgbox "Failed to install yq. Please install it manually." 10 60
        exit 1
      }
    else
      missing_deps+=("yq")
    fi
  fi
  
  if [ ${#missing_deps[@]} -gt 0 ]; then
    whiptail --msgbox "Missing dependencies: ${missing_deps[*]}\nPlease install them and try again." 12 60
    exit 1
  fi
}

initialize_environment() {
  mkdir -p "$SHARED_DIR" "$MOTD_DIR"
  
  # Set permissions only if directory is empty or just created
  if [ ! -f "$SHARED_DIR/.initialized" ]; then
    chmod 777 "$SHARED_DIR" 2>/dev/null || true
    touch "$SHARED_DIR/.initialized"
  fi
  
  touch "$LOG_FILE"
  
  if [ ! -f "$SHARED_DIR/README.txt" ]; then
    cat > "$SHARED_DIR/README.txt" <<EOF
Docker Playground - Shared Volume
==================================

This directory is shared across all playground containers.
You can use it to:
- Exchange files between containers
- Test scripts across different environments
- Share configuration files

Mounted at: /shared (inside containers)
Host path: $SHARED_DIR
EOF
  fi
  
  # Create MOTD files
  create_motd_files
  
  if [ -d "$SHARED_DIR" ] && [ -w "$SHARED_DIR" ]; then
    echo "Test" > "$SHARED_DIR/test-write.txt" && rm "$SHARED_DIR/test-write.txt"
    log "Environment initialized successfully"
  else
    log "ERROR: Shared directory $SHARED_DIR is not writable"
    whiptail --msgbox "ERROR: Shared directory $SHARED_DIR is not writable. Check permissions." 10 60
    exit 1
  fi
}

#############################################
# MOTD (Message of the Day) Files
#############################################

create_motd_files() {
  # MySQL MOTD
  cat > "$MOTD_DIR/mysql.txt" <<'EOF'
╔══════════════════════════════════════════════════════════════╗
║                    MySQL Quick Reference                      ║
╚══════════════════════════════════════════════════════════════╝

🔐 Connection Info:
   Host: localhost / Container IP
   Port: 3306
   User: playground / root
   Password: playground

📊 Basic Commands:
   mysql -u root -pplayground                    # Connect to MySQL
   mysql -u playground -pplayground playground   # Connect to playground DB

📁 Database Operations:
   SHOW DATABASES;                               # List all databases
   CREATE DATABASE mydb;                         # Create database
   USE mydb;                                     # Switch to database
   SHOW TABLES;                                  # List tables
   DESCRIBE tablename;                           # Show table structure

💾 Backup & Restore:
   # Backup single database
   mysqldump -u root -pplayground playground > /shared/backup.sql
   
   # Backup all databases
   mysqldump -u root -pplayground --all-databases > /shared/full_backup.sql
   
   # Restore database
   mysql -u root -pplayground playground < /shared/backup.sql
   
   # Restore with creation
   mysql -u root -pplayground < /shared/backup.sql

🔍 Useful Queries:
   SELECT USER(), DATABASE();                    # Current user & DB
   SHOW PROCESSLIST;                            # Active connections
   SHOW VARIABLES LIKE '%version%';             # MySQL version info
   SELECT * FROM information_schema.tables;     # All tables info

📝 Quick Table Example:
   CREATE TABLE users (
     id INT AUTO_INCREMENT PRIMARY KEY,
     name VARCHAR(100),
     email VARCHAR(100)
   );
   INSERT INTO users (name, email) VALUES ('Test', 'test@example.com');
   SELECT * FROM users;

Press Enter to continue...
EOF

  # PostgreSQL MOTD
  cat > "$MOTD_DIR/postgres.txt" <<'EOF'
╔══════════════════════════════════════════════════════════════╗
║                 PostgreSQL Quick Reference                    ║
╚══════════════════════════════════════════════════════════════╝

🔐 Connection Info:
   Host: localhost / Container IP
   Port: 5432
   User: playground
   Password: playground
   Database: playground

📊 Basic Commands:
   psql -U playground                            # Connect to PostgreSQL
   \l                                            # List databases
   \c database_name                              # Connect to database
   \dt                                           # List tables
   \d table_name                                 # Describe table
   \q                                            # Quit

💾 Backup & Restore:
   # Backup database
   pg_dump -U playground playground > /shared/backup.sql
   
   # Backup in custom format (compressed)
   pg_dump -U playground -Fc playground > /shared/backup.dump
   
   # Backup specific table
   pg_dump -U playground -t users playground > /shared/users_backup.sql
   
   # Restore from SQL
   psql -U playground playground < /shared/backup.sql
   
   # Restore from custom format
   pg_restore -U playground -d playground /shared/backup.dump

🔍 Useful Queries:
   SELECT version();                             # PostgreSQL version
   SELECT current_database();                    # Current database
   SELECT current_user;                          # Current user
   \du                                           # List users
   \timing on                                    # Enable query timing
   
   # List all tables with sizes
   SELECT schemaname, tablename, 
          pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
   FROM pg_tables WHERE schemaname = 'public';

📝 Quick Table Example:
   CREATE TABLE users (
     id SERIAL PRIMARY KEY,
     name VARCHAR(100),
     email VARCHAR(100) UNIQUE,
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   INSERT INTO users (name, email) VALUES ('Test', 'test@example.com');
   SELECT * FROM users;

Press Enter to continue...
EOF

  # MongoDB MOTD
  cat > "$MOTD_DIR/mongodb.txt" <<'EOF'
╔══════════════════════════════════════════════════════════════╗
║                  MongoDB Quick Reference                      ║
╚══════════════════════════════════════════════════════════════╝

🔐 Connection Info:
   Host: localhost / Container IP
   Port: 27017
   No authentication required (default)

📊 Basic Commands:
   mongosh                                       # Connect to MongoDB
   show dbs                                      # List databases
   use mydb                                      # Switch/create database
   show collections                              # List collections
   db.collection.find()                          # Show all documents

💾 Backup & Restore:
   # Backup entire database
   mongodump --db playground --out /shared/backup
   
   # Backup specific collection
   mongodump --db playground --collection users --out /shared/backup
   
   # Restore database
   mongorestore --db playground /shared/backup/playground
   
   # Export to JSON
   mongoexport --db playground --collection users --out /shared/users.json
   
   # Import from JSON
   mongoimport --db playground --collection users --file /shared/users.json

🔍 CRUD Operations:
   # Insert
   db.users.insertOne({name: "John", age: 30})
   db.users.insertMany([{name: "Jane"}, {name: "Bob"}])
   
   # Find
   db.users.find()                               # Find all
   db.users.find({name: "John"})                 # Find with filter
   db.users.findOne({name: "John"})              # Find one
   
   # Update
   db.users.updateOne({name: "John"}, {$set: {age: 31}})
   db.users.updateMany({}, {$inc: {age: 1}})
   
   # Delete
   db.users.deleteOne({name: "John"})
   db.users.deleteMany({age: {$lt: 18}})

📈 Aggregation Example:
   db.users.aggregate([
     {$match: {age: {$gte: 18}}},
     {$group: {_id: "$city", count: {$sum: 1}}},
     {$sort: {count: -1}}
   ])

Press Enter to continue...
EOF

  # Redis MOTD
  cat > "$MOTD_DIR/redis.txt" <<'EOF'
╔══════════════════════════════════════════════════════════════╗
║                   Redis Quick Reference                       ║
╚══════════════════════════════════════════════════════════════╝

🔐 Connection Info:
   Host: localhost / Container IP
   Port: 6379
   No authentication required (default)

📊 Basic Commands:
   redis-cli                                     # Connect to Redis
   PING                                          # Test connection
   INFO                                          # Server information
   DBSIZE                                        # Number of keys
   FLUSHDB                                       # Clear current database
   FLUSHALL                                      # Clear all databases

💾 Backup & Restore:
   # Trigger manual save
   SAVE                                          # Synchronous save
   BGSAVE                                        # Background save
   
   # Backup file location: /data/dump.rdb
   # Copy backup
   docker cp playground-redis:/data/dump.rdb /shared/redis_backup.rdb
   
   # Restore (stop Redis, replace dump.rdb, start Redis)
   docker cp /shared/redis_backup.rdb playground-redis:/data/dump.rdb

🔑 String Operations:
   SET key "value"                               # Set string
   GET key                                       # Get string
   MSET key1 "val1" key2 "val2"                 # Set multiple
   INCR counter                                  # Increment
   EXPIRE key 3600                               # Set expiry (seconds)
   TTL key                                       # Time to live

📝 List Operations:
   LPUSH mylist "item1"                          # Push to left
   RPUSH mylist "item2"                          # Push to right
   LRANGE mylist 0 -1                            # Get all items
   LPOP mylist                                   # Pop from left

🗂️ Hash Operations:
   HSET user:1 name "John" age 30               # Set hash fields
   HGET user:1 name                             # Get field
   HGETALL user:1                               # Get all fields
   HINCRBY user:1 age 1                         # Increment field

📊 Set Operations:
   SADD myset "item1" "item2"                   # Add to set
   SMEMBERS myset                               # Get all members
   SISMEMBER myset "item1"                      # Check membership

Press Enter to continue...
EOF

  # Docker MOTD
  cat > "$MOTD_DIR/docker.txt" <<'EOF'
╔══════════════════════════════════════════════════════════════╗
║              Docker in Docker Quick Reference                 ║
╚══════════════════════════════════════════════════════════════╝

⚠️  This is Docker in Docker (DinD) - you can run Docker inside!

📊 Basic Docker Commands:
   docker ps                                     # List running containers
   docker ps -a                                  # List all containers
   docker images                                 # List images
   docker pull ubuntu:latest                     # Pull an image
   docker run -it ubuntu bash                    # Run interactive container

🏗️ Building Images:
   # Create Dockerfile in /shared
   cat > /shared/Dockerfile <<EOF2
   FROM alpine:latest
   RUN apk add --no-cache curl
   CMD ["sh"]
   EOF2
   
   # Build image
   cd /shared && docker build -t myimage:latest .
   
   # Run your image
   docker run -it myimage:latest

💾 Container Management:
   docker start container_name                   # Start container
   docker stop container_name                    # Stop container
   docker restart container_name                 # Restart container
   docker rm container_name                      # Remove container
   docker exec -it container_name sh             # Execute command

🔍 Inspect & Logs:
   docker inspect container_name                 # Detailed info
   docker logs container_name                    # View logs
   docker logs -f container_name                 # Follow logs
   docker stats                                  # Resource usage

🌐 Networking:
   docker network ls                             # List networks
   docker network create mynet                   # Create network
   docker network connect mynet container        # Connect container

📦 Volumes:
   docker volume ls                              # List volumes
   docker volume create myvol                    # Create volume
   docker run -v myvol:/data ubuntu             # Mount volume

Press Enter to continue...
EOF

  # Python MOTD
  cat > "$MOTD_DIR/python.txt" <<'EOF'
╔══════════════════════════════════════════════════════════════╗
║                  Python Quick Reference                       ║
╚══════════════════════════════════════════════════════════════╝

🐍 Python Environment:
   python --version                              # Check version
   pip --version                                 # Check pip version
   pip list                                      # List installed packages

📦 Package Management:
   pip install requests                          # Install package
   pip install -r requirements.txt               # Install from file
   pip freeze > /shared/requirements.txt         # Export packages
   pip uninstall package_name                    # Uninstall package

🧪 Quick Testing:
   # Create test script
   cat > /shared/test.py <<EOF2
   import sys
   print(f"Python {sys.version}")
   print("Hello from Python!")
   
   # Test basic functionality
   numbers = [1, 2, 3, 4, 5]
   squared = [x**2 for x in numbers]
   print(f"Squared: {squared}")
   EOF2
   
   python /shared/test.py

🌐 Web Server:
   # Quick HTTP server
   cd /shared && python -m http.server 8000
   
   # Create simple Flask app
   pip install flask
   cat > /shared/app.py <<EOF2
   from flask import Flask
   app = Flask(__name__)
   
   @app.route('/')
   def hello():
       return 'Hello from Python Flask!'
   
   if __name__ == '__main__':
       app.run(host='0.0.0.0', port=5000)
   EOF2
   
   python /shared/app.py

📊 Data Science Quick Start:
   pip install numpy pandas matplotlib
   
   python <<EOF2
   import numpy as np
   import pandas as pd
   
   # Create sample data
   data = pd.DataFrame({
       'name': ['Alice', 'Bob', 'Charlie'],
       'age': [25, 30, 35]
   })
   print(data)
   data.to_csv('/shared/data.csv', index=False)
   EOF2

Press Enter to continue...
EOF

  # Node.js MOTD
  cat > "$MOTD_DIR/node.txt" <<'EOF'
╔══════════════════════════════════════════════════════════════╗
║                 Node.js Quick Reference                       ║
╚══════════════════════════════════════════════════════════════╝

🟢 Node.js Environment:
   node --version                                # Check Node version
   npm --version                                 # Check npm version
   npm list -g --depth=0                        # List global packages

📦 Package Management:
   npm init -y                                   # Initialize package.json
   npm install express                           # Install package
   npm install --save-dev jest                   # Install dev dependency
   npm install                                   # Install from package.json
   npm uninstall package_name                    # Uninstall package

🚀 Quick Web Server:
   # Create Express app
   cd /shared
   npm init -y
   npm install express
   
   cat > /shared/server.js <<EOF2
   const express = require('express');
   const app = express();
   
   app.get('/', (req, res) => {
       res.json({ message: 'Hello from Node.js!' });
   });
   
   app.listen(3000, () => {
       console.log('Server running on port 3000');
   });
   EOF2
   
   node /shared/server.js

🧪 Quick Script:
   cat > /shared/test.js <<EOF2
   console.log('Node.js version:', process.version);
   console.log('Platform:', process.platform);
   
   // Test async/await
   async function test() {
       const result = await Promise.resolve('Success!');
       console.log(result);
   }
   test();
   EOF2
   
   node /shared/test.js

🔧 Useful npm Commands:
   npm run script_name                           # Run script from package.json
   npm outdated                                  # Check outdated packages
   npm update                                    # Update packages
   npm audit                                     # Check for vulnerabilities
   npm audit fix                                 # Fix vulnerabilities

Press Enter to continue...
EOF

# Go MOTD
  cat > "$MOTD_DIR/golang.txt" <<'EOF'
╔══════════════════════════════════════════════════════════════╗
║                    Go Quick Reference                         ║
╚══════════════════════════════════════════════════════════════╝

🔵 Go Environment:
   go version                                    # Check Go version
   go env                                        # Show environment

📦 Module Management:
   go mod init myapp                             # Initialize module
   go mod tidy                                   # Add missing and remove unused modules
   go get package@version                        # Add dependency
   go mod download                               # Download dependencies

🚀 Build & Run:
   go run main.go                                # Run directly
   go build -o myapp                             # Build executable
   go build -o /shared/myapp                     # Build to shared folder
   
   # Cross-compile
   GOOS=linux GOARCH=amd64 go build -o myapp
   GOOS=windows GOARCH=amd64 go build -o myapp.exe

🧪 Testing:
   go test                                       # Run tests
   go test -v                                    # Verbose output
   go test -cover                                # With coverage
   go test -bench=.                              # Run benchmarks

📝 Quick HTTP Server:
   cat > /shared/server.go <<'EOF2'
   package main
   
   import (
       "fmt"
       "net/http"
   )
   
   func main() {
       http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
           fmt.Fprintf(w, "Hello from Go!")
       })
       http.ListenAndServe(":8080", nil)
   }
   EOF2
   
   go run /shared/server.go

🔧 Useful Commands:
   go fmt ./...                                  # Format code
   go vet ./...                                  # Examine code
   go doc package                                # View documentation
   gofmt -w file.go                              # Format file

Press Enter to continue...
EOF

  # Nginx MOTD
  cat > "$MOTD_DIR/nginx.txt" <<'EOF'
╔══════════════════════════════════════════════════════════════╗
║                   Nginx Quick Reference                       ║
╚══════════════════════════════════════════════════════════════╝

🌐 Nginx Info:
   nginx -v                                      # Version
   nginx -t                                      # Test configuration
   nginx -T                                      # Test and dump config

📁 Important Paths:
   Config: /etc/nginx/nginx.conf
   Sites: /etc/nginx/conf.d/
   HTML: /usr/share/nginx/html/
   Logs: /var/log/nginx/

🔧 Basic Commands:
   nginx -s reload                               # Reload config
   nginx -s stop                                 # Stop nginx
   nginx -s quit                                 # Graceful shutdown

📝 Simple Site Setup:
   # Create HTML file
   cat > /shared/index.html <<'EOF2'
   <!DOCTYPE html>
   <html>
   <head><title>My Site</title></head>
   <body>
       <h1>Hello from Nginx!</h1>
       <p>This is served from the shared volume</p>
   </body>
   </html>
   EOF2
   
   # Create nginx config
   cat > /etc/nginx/conf.d/mysite.conf <<'EOF2'
   server {
       listen 80;
       server_name localhost;
       root /shared;
       index index.html;
       
       location / {
           try_files $uri $uri/ =404;
       }
   }
   EOF2
   
   nginx -s reload

📊 Check Status:
   ps aux | grep nginx                           # Check processes
   netstat -tlnp | grep :80                      # Check port
   curl localhost                                # Test locally

🔍 View Logs:
   tail -f /var/log/nginx/access.log             # Access log
   tail -f /var/log/nginx/error.log              # Error log

Press Enter to continue...
EOF

  # Rust MOTD
  cat > "$MOTD_DIR/rust.txt" <<'EOF'
╔══════════════════════════════════════════════════════════════╗
║                   Rust Quick Reference                        ║
╚══════════════════════════════════════════════════════════════╝

🦀 Rust Environment:
   rustc --version                               # Compiler version
   cargo --version                               # Cargo version
   rustup update                                 # Update Rust

📦 Cargo Commands:
   cargo new myapp                               # Create new project
   cargo init                                    # Initialize in current dir
   cargo build                                   # Build debug
   cargo build --release                         # Build optimized
   cargo run                                     # Build and run
   cargo test                                    # Run tests
   cargo check                                   # Check without building

🚀 Quick Program:
   cat > /shared/hello.rs <<'EOF2'
   fn main() {
       println!("Hello from Rust!");
       
       let numbers = vec![1, 2, 3, 4, 5];
       let sum: i32 = numbers.iter().sum();
       println!("Sum: {}", sum);
   }
   EOF2
   
   rustc /shared/hello.rs -o /shared/hello
   /shared/hello

📝 Simple Web Server (Actix):
   cargo new webserver --bin
   cd webserver
   
   # Add to Cargo.toml:
   # [dependencies]
   # actix-web = "4"
   
   # Then:
   cargo build
   cargo run

🔧 Useful Commands:
   cargo fmt                                     # Format code
   cargo clippy                                  # Lint code
   cargo doc --open                              # Generate docs
   cargo clean                                   # Clean build

📊 Dependencies:
   cargo add serde                               # Add dependency
   cargo update                                  # Update dependencies
   cargo tree                                    # Show dependency tree

Press Enter to continue...
EOF

  # Elasticsearch MOTD
  cat > "$MOTD_DIR/elasticsearch.txt" <<'EOF'
╔══════════════════════════════════════════════════════════════╗
║               Elasticsearch Quick Reference                   ║
╚══════════════════════════════════════════════════════════════╝

🔍 Connection:
   URL: http://localhost:9200
   Health: curl localhost:9200/_cluster/health

📊 Basic Operations:
   # Check cluster info
   curl localhost:9200
   
   # List indices
   curl localhost:9200/_cat/indices?v
   
   # Create index
   curl -X PUT localhost:9200/myindex
   
   # Delete index
   curl -X DELETE localhost:9200/myindex

📝 Document Operations:
   # Index document
   curl -X POST localhost:9200/myindex/_doc/1 -H 'Content-Type: application/json' -d '
   {
     "title": "First Document",
     "content": "Hello Elasticsearch"
   }'
   
   # Get document
   curl localhost:9200/myindex/_doc/1
   
   # Update document
   curl -X POST localhost:9200/myindex/_update/1 -H 'Content-Type: application/json' -d '
   {
     "doc": {"content": "Updated content"}
   }'
   
   # Delete document
   curl -X DELETE localhost:9200/myindex/_doc/1

🔎 Search:
   # Match all
   curl localhost:9200/myindex/_search?q=*
   
   # Search with query
   curl -X GET localhost:9200/myindex/_search -H 'Content-Type: application/json' -d '
   {
     "query": {
       "match": {
         "title": "First"
       }
     }
   }'

💾 Backup (Snapshot):
   # Register repository
   curl -X PUT localhost:9200/_snapshot/my_backup -H 'Content-Type: application/json' -d '
   {
     "type": "fs",
     "settings": {
       "location": "/shared/elasticsearch_backup"
     }
   }'
   
   # Create snapshot
   curl -X PUT localhost:9200/_snapshot/my_backup/snapshot_1?wait_for_completion=true

Press Enter to continue...
EOF

  chmod 644 "$MOTD_DIR"/*.txt
}

show_motd() {
  local service="$1"
  local motd_file=""
  
  # Map service to MOTD file
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

#############################################
# Docker Compose Generation
#############################################

generate_compose() {
  local selected=("$@")
  
  cat <<EOF > "$COMPOSE_FILE"
networks:
  $NETWORK_NAME:
    driver: bridge

services:
EOF

  for img in "${selected[@]}"; do
    img="${img//\"/}"
    image_name=$(yq ".images.\"$img\".image" "$CONFIG_FILE")
    keep_alive_cmd=$(yq ".images.\"$img\".keep_alive_cmd // \"sleep infinity\"" "$CONFIG_FILE")
    shell_cmd=$(yq ".images.\"$img\".shell // \"/bin/bash\"" "$CONFIG_FILE")
    privileged=$(yq ".images.\"$img\".privileged // false" "$CONFIG_FILE")
    
    cat <<EOF >> "$COMPOSE_FILE"
  $img:
    image: $image_name
    container_name: playground-$img
    hostname: $img
    networks:
      - $NETWORK_NAME
    volumes:
      - $SHARED_DIR:/shared
    command: $keep_alive_cmd
    stdin_open: true
    tty: true
    restart: unless-stopped
    labels:
      - "playground.managed=true"
      - "playground.image=$img"
EOF

    if [ "$privileged" = "true" ]; then
      echo "    privileged: true" >> "$COMPOSE_FILE"
    fi
    
    env_keys=$(yq ".images.\"$img\".environment // {} | keys | .[]" "$CONFIG_FILE" 2>/dev/null || echo "")
    if [ -n "$env_keys" ]; then
      echo "    environment:" >> "$COMPOSE_FILE"
      while IFS= read -r key; do
        value=$(yq ".images.\"$img\".environment.\"$key\"" "$CONFIG_FILE")
        echo "      $key: $value" >> "$COMPOSE_FILE"
      done <<< "$env_keys"
    fi
    
    port_count=$(yq ".images.\"$img\".ports | length" "$CONFIG_FILE" 2>/dev/null || echo "0")
    if [ "$port_count" -gt 0 ]; then
      echo "    ports:" >> "$COMPOSE_FILE"
      for ((i=0; i<port_count; i++)); do
        port=$(yq ".images.\"$img\".ports[$i]" "$CONFIG_FILE")
        echo "      - \"$port\"" >> "$COMPOSE_FILE"
      done
    fi
    
    echo "" >> "$COMPOSE_FILE"
  done
  
  log "Generated docker-compose.yml with services: ${selected[*]}"
}

#############################################
# Selection Functions
#############################################

select_instances() {
  local action="$1"
  local category_filter="${2:-}"
  local selected=()
  local options=()
  
  mapfile -t images < <(yq '.images | keys | .[]' "$CONFIG_FILE")
  
  local running=()
  if [ "$action" = "stop" ]; then
    mapfile -t running < <(docker ps --filter "label=playground.managed=true" --format "{{.Labels}}" | grep -oP 'playground.image=\K[^,]+' | sort -u 2>/dev/null || echo "")
  fi
  
  for img in "${images[@]}"; do
    description=$(yq ".images.\"$img\".description // \"No description\"" "$CONFIG_FILE")
    category=$(yq ".images.\"$img\".category // \"other\"" "$CONFIG_FILE")
    
    # Apply category filter if specified
    if [ -n "$category_filter" ] && [ "$category" != "$category_filter" ]; then
      continue
    fi
    
    # Check if running
    is_running=$(docker ps -q --filter "name=playground-$img" --filter "label=playground.managed=true" 2>/dev/null)
    
    if [ "$action" = "start" ] && [ -n "$is_running" ]; then
      continue  # Skip already running containers for start
    fi
    
    if [ "$action" = "stop" ] && [[ " ${running[*]} " =~ " $img " ]]; then
      options+=("$img" "[$category] $description" on)
    else
      options+=("$img" "[$category] $description" off)
    fi
  done
  
  if [ ${#options[@]} -eq 0 ]; then
    echo ""
    return
  fi
  
  local title="Select Container Instances"
  if [ -n "$category_filter" ]; then
    title="Select Containers - Category: $category_filter"
  fi
  
  selected=$(whiptail --title "$title" \
    --checklist "Choose one or more containers to $action:\n(Use SPACE to select, ENTER to confirm)" \
    22 85 14 "${options[@]}" 3>&1 1>&2 2>&3)
  
  echo "$selected"
}

select_single_instance() {
  local title="$1"
  local message="$2"
  
  # Get ONLY running containers - direct approach
  local running_containers=$(docker ps --filter "label=playground.managed=true" --filter "status=running" --format "{{.Names}}" 2>/dev/null | sed 's/playground-//' | sort -u)
  
  if [ -z "$running_containers" ]; then
    echo ""
    return
  fi
  
  local options=()
  while IFS= read -r service; do
    # Skip empty lines
    [ -z "$service" ] && continue
    
    # Verify the service exists in config
    if yq ".images.\"$service\"" "$CONFIG_FILE" &>/dev/null; then
      description=$(yq ".images.\"$service\".description // \"No description\"" "$CONFIG_FILE" 2>/dev/null)
      category=$(yq ".images.\"$service\".category // \"other\"" "$CONFIG_FILE" 2>/dev/null)
      options+=("$service" "[$category] $description")
    fi
  done <<< "$running_containers"
  
  # Check if we have any valid options
  if [ ${#options[@]} -eq 0 ]; then
    echo ""
    return
  fi
  
  selected=$(whiptail --title "$title" --menu "$message" 22 75 14 "${options[@]}" 3>&1 1>&2 2>&3)
  echo "$selected"
}

cleanup_dead_containers() {
  # Remove any stopped/dead containers with playground label
  docker ps -a --filter "label=playground.managed=true" --filter "status=exited" -q | xargs -r docker rm 2>/dev/null || true
  docker ps -a --filter "label=playground.managed=true" --filter "status=dead" -q | xargs -r docker rm 2>/dev/null || true
}

select_category() {
  local categories=("linux" "programming" "database" "messaging" "webserver" "devops" "monitoring" "ml" "utility")
  local options=()
  
  for cat in "${categories[@]}"; do
    count=$(yq ".images | to_entries[] | select(.value.category == \"$cat\") | .key" "$CONFIG_FILE" 2>/dev/null | wc -l)
    if [ "$count" -gt 0 ]; then
      options+=("$cat" "$count images")
    fi
  done
  
  selected=$(whiptail --title "Select Category" --menu "Choose a category:" 20 60 12 "${options[@]}" 3>&1 1>&2 2>&3)
  echo "$selected"
}

#############################################
# Container Management Functions
#############################################

start_containers() {
  selected=$(select_instances "start")
  
  if [ -z "$selected" ]; then
    whiptail --msgbox "No instances selected or all are already running." 10 55
    return
  fi
  
  read -r -a selected_array <<< "$selected"
  generate_compose "${selected_array[@]}"
  
  if docker compose -f "$COMPOSE_FILE" up -d; then
    log "Started containers: ${selected_array[*]}"
    whiptail --msgbox "✓ Successfully started:\n\n${selected_array[*]}\n\nUse 'Enter container' to interact." 14 65
  else
    log "ERROR: Failed to start containers"
    whiptail --msgbox "✗ Failed to start containers. Check docker logs." 10 60
  fi
}

start_by_category() {
  category=$(select_category)
  
  if [ -z "$category" ]; then
    return
  fi
  
  selected=$(select_instances "start" "$category")
  
  if [ -z "$selected" ]; then
    whiptail --msgbox "No instances selected." 10 50
    return
  fi
  
  read -r -a selected_array <<< "$selected"
  generate_compose "${selected_array[@]}"
  
  if docker compose -f "$COMPOSE_FILE" up -d; then
    log "Started containers from category $category: ${selected_array[*]}"
    whiptail --msgbox "✓ Successfully started from category '$category':\n\n${selected_array[*]}" 14 65
  else
    log "ERROR: Failed to start containers"
    whiptail --msgbox "✗ Failed to start containers." 10 60
  fi
}

stop_containers() {
  selected=$(select_instances "stop")
  
  if [ -z "$selected" ]; then
    whiptail --msgbox "No running instances to stop." 8 40
    return
  fi
  
  read -r -a selected_array <<< "$selected"
  generate_compose "${selected_array[@]}"
  
  if docker compose -f "$COMPOSE_FILE" down; then
    log "Stopped containers: ${selected_array[*]}"
    whiptail --msgbox "✓ Successfully stopped:\n\n${selected_array[*]}" 12 65
  else
    log "ERROR: Failed to stop containers"
    whiptail --msgbox "✗ Failed to stop containers." 10 60
  fi
}

list_containers() {
  # Show ONLY running containers
  output=$(docker ps --filter "label=playground.managed=true" --filter "status=running" \
    --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" 2>/dev/null || echo "")
  
  if [ -z "$output" ] || [ "$(echo "$output" | wc -l)" -eq 1 ]; then
    whiptail --msgbox "No active containers found." 8 40
  else
    whiptail --title "Active Playground Containers" --msgbox "$output" 22 80 --scrolltext
  fi
}

enter_container() {
  # Clean up any dead containers first
  cleanup_dead_containers
  
  service=$(select_single_instance "Enter Container" "Choose a container to enter:")
  
  if [ -z "$service" ]; then
    whiptail --msgbox "No running containers available." 8 50
    return
  fi
  
  # Double check container is actually running
  is_running=$(docker ps -q --filter "name=playground-$service" --filter "status=running" 2>/dev/null)
  
  if [ -z "$is_running" ]; then
    whiptail --msgbox "Container $service is not running.\n\nPlease start it first." 10 50
    return
  fi
  
  # Show MOTD if available
  show_motd "$service"
  
  shell_cmd=$(yq ".images.\"$service\".shell // \"/bin/bash\"" "$CONFIG_FILE")
  
  clear
  echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║  Entering container: playground-$service"
  echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
  echo -e "${YELLOW}Type 'exit' to return to the menu${NC}"
  echo ""
  log "Entering container: $service"
  
  # Generate compose for this specific container if needed
  if [ ! -f "$COMPOSE_FILE" ]; then
    generate_compose "$service"
  fi
  
  docker compose -f "$COMPOSE_FILE" exec -it "$service" "$shell_cmd" || {
    log "ERROR: Failed to enter $service"
    whiptail --msgbox "Failed to enter $service.\n\nThe container may have stopped." 10 60
  }
  
  log "Exited container: $service"
}

container_logs() {
  service=$(select_single_instance "View Container Logs" "Choose a container:")
  
  if [ -z "$service" ]; then
    whiptail --msgbox "No container selected." 8 40
    return
  fi
  
  clear
  echo -e "${GREEN}Logs for: playground-$service${NC}"
  echo -e "${YELLOW}Press Ctrl+C to return to menu${NC}"
  echo ""
  
  # Create a subshell that handles the logs
  (
    # This subshell will be killed on Ctrl+C
    docker compose -f "$COMPOSE_FILE" logs -f "$service" 2>&1
  ) &
  
  local log_pid=$!
  
  # Wait for Ctrl+C in the parent shell
  trap "kill $log_pid 2>/dev/null; trap - INT; echo -e '\n${GREEN}Returning to menu...${NC}'; sleep 1; return 0" INT
  
  # Wait for the background process
  wait $log_pid 2>/dev/null
  
  # Clean up trap
  trap - INT
  
  echo -e "\n${GREEN}Returning to menu...${NC}"
  sleep 1
}

restart_container() {
  service=$(select_single_instance "Restart Container" "Choose a container to restart:")
  
  if [ -z "$service" ]; then
    whiptail --msgbox "No container selected." 8 40
    return
  fi
  
  if docker compose -f "$COMPOSE_FILE" restart "$service"; then
    log "Restarted container: $service"
    whiptail --msgbox "✓ Container $service restarted successfully." 8 50
  else
    log "ERROR: Failed to restart $service"
    whiptail --msgbox "✗ Failed to restart $service." 8 50
  fi
}

container_stats() {
  clear
  echo -e "${GREEN}Container Statistics${NC}"
  echo -e "${YELLOW}Press Enter to refresh, Ctrl+C to return to menu${NC}"
  echo ""
  
  # Get ONLY running containers
  containers=$(docker ps --filter "label=playground.managed=true" --filter "status=running" --format "{{.Names}}" | sort)
  
  if [ -z "$containers" ]; then
    echo "No active containers found."
    read -r -s -n 1
    return
  fi
  
  trap 'echo -e "\n${GREEN}Returning to menu...${NC}"; sleep 1; return' INT
  
  while true; do
    clear
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              Container Statistics                          ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo -e "${YELLOW}Press Enter to refresh, Ctrl+C to return to menu${NC}"
    echo ""
    echo -e "${CYAN}NAME\t\t\tIMAGE\t\t\tSTATUS${NC}"
    echo -e "────────────────────────────────────────────────────────────"
    
    # Re-check running containers on each refresh
    containers=$(docker ps --filter "label=playground.managed=true" --filter "status=running" --format "{{.Names}}" | sort)
    
    if [ -z "$containers" ]; then
      echo -e "${RED}No running containers found.${NC}"
      echo ""
      read -r -s -n 1
      break
    fi
    
    while IFS= read -r container; do
      image=$(docker inspect --format '{{.Config.Image}}' "$container" 2>/dev/null | cut -d':' -f1 || echo "N/A")
      status=$(docker inspect --format '{{.State.Status}}' "$container" 2>/dev/null || echo "N/A")
      
      if [ "$status" = "running" ]; then
        status_color="${GREEN}"
      else
        status_color="${RED}"
      fi
      
      echo -e "${container}\t${image}\t${status_color}${status}${NC}"
    done <<< "$containers"
    
    echo ""
    read -r -s -n 1 input
    if [ -z "$input" ]; then
      continue
    fi
    break
  done
  
  trap - INT
}

#############################################
# Dashboard & Information
#############################################

show_dashboard() {
  clear
  print_header
  
  running=$(docker ps --filter "label=playground.managed=true" -q | wc -l)
  total=$(yq '.images | length' "$CONFIG_FILE")
  
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
  
  # Category breakdown
  echo -e "${BLUE}📦 Images by Category:${NC}"
  categories=("linux" "programming" "database" "messaging" "webserver" "devops" "monitoring" "ml" "utility")
  for cat in "${categories[@]}"; do
    count=$(yq ".images | to_entries[] | select(.value.category == \"$cat\") | .key" "$CONFIG_FILE" 2>/dev/null | wc -l)
    if [ "$count" -gt 0 ]; then
      printf "   ${YELLOW}%-15s${NC}: %2d images\n" "$cat" "$count"
    fi
  done
  
  echo ""
  echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  read -p "Press Enter to continue..." -r
}

quick_search() {
  search_term=$(whiptail --inputbox "Search images by name or description:" 10 60 3>&1 1>&2 2>&3) || return 0
  
  # Check if empty
  if [ -z "$search_term" ]; then
    return 0
  fi
  
  # Search in both keys and descriptions
  results=""
  
  # Search by key name
  while IFS= read -r img; do
    if echo "$img" | grep -qi "$search_term"; then
      desc=$(yq ".images.\"$img\".description" "$CONFIG_FILE" 2>/dev/null || echo "No description")
      results+="$img - $desc"$'\n'
    fi
  done < <(yq '.images | keys | .[]' "$CONFIG_FILE" 2>/dev/null || true)
  
  # Search by description
  while IFS= read -r img; do
    desc=$(yq ".images.\"$img\".description" "$CONFIG_FILE" 2>/dev/null || echo "")
    if [ -n "$desc" ] && echo "$desc" | grep -qi "$search_term"; then
      if ! echo "$results" | grep -q "^$img -"; then
        results+="$img - $desc"$'\n'
      fi
    fi
  done < <(yq '.images | keys | .[]' "$CONFIG_FILE" 2>/dev/null || true)
  
  # Remove empty lines and sort
  all_results=$(echo "$results" | grep -v '^$' | sort -u || true)
  
  if [ -z "$all_results" ]; then
    whiptail --msgbox "No images found matching: $search_term" 8 50 || true
  else
    whiptail --title "Search Results for: $search_term" --msgbox "$all_results" 22 90 --scrolltext || true
  fi
  
  return 0
}

#############################################
# Utility Functions
#############################################

browse_catalog() {
  local categories=("linux" "programming" "database" "messaging" "webserver" "devops" "monitoring" "ml" "utility")
  local catalog_text="╔══════════════════════════════════════════════════════════════╗\n"
  catalog_text+="║          Docker Playground - Complete Image Catalog          ║\n"
  catalog_text+="╚══════════════════════════════════════════════════════════════╝\n\n"
  
  for category in "${categories[@]}"; do
    images=$(yq ".images | to_entries[] | select(.value.category == \"$category\") | .key" "$CONFIG_FILE" 2>/dev/null || echo "")
    
    if [ -n "$images" ]; then
      catalog_text+="$(echo "$category" | tr '[:lower:]' '[:upper:]')\n"
      catalog_text+="══════════════════════════════════════════════════════════════\n"
      
      while IFS= read -r img; do
        desc=$(yq ".images.\"$img\".description" "$CONFIG_FILE")
        image_name=$(yq ".images.\"$img\".image" "$CONFIG_FILE")
        catalog_text+="  • $img\n"
        catalog_text+="    $desc\n"
        catalog_text+="    Image: $image_name\n\n"
      done <<< "$images"
    fi
  done
  
  whiptail --title "Image Catalog (${total} total)" --msgbox "$catalog_text" 30 85 --scrolltext
}

cleanup_all() {
  if whiptail --yesno "⚠️  WARNING ⚠️\n\nThis will:\n• Stop all playground containers\n• Remove all containers\n• Delete shared volume data\n• Remove docker-compose.yml\n\nAre you absolutely sure?" 16 65; then
    
    docker ps -q --filter "label=playground.managed=true" | xargs -r docker stop 2>/dev/null
    docker ps -aq --filter "label=playground.managed=true" | xargs -r docker rm 2>/dev/null
    
    docker network rm "$NETWORK_NAME" 2>/dev/null || true
    
    rm -rf "$SHARED_DIR"
    mkdir -p "$SHARED_DIR"
    
    rm -f "$COMPOSE_FILE"
    
    log "Full cleanup performed"
    whiptail --msgbox "✓ Cleanup completed successfully.\n\nAll playground containers and data removed." 10 60
  fi
}

export_logs() {
  export_file="playground-logs-$(date +%Y%m%d-%H%M%S).txt"
  cp "$LOG_FILE" "$export_file"
  log "Logs exported to $export_file"
  whiptail --msgbox "✓ Logs exported to:\n\n$export_file" 10 60
}

show_info() {
  local info_text="╔══════════════════════════════════════════════════════════════╗\n"
  info_text+="║          Docker Playground Manager v2.4 - Info              ║\n"
  info_text+="╚══════════════════════════════════════════════════════════════╝\n\n"
  
  info_text+="📁 Configuration:\n"
  info_text+="   Config File: $CONFIG_FILE\n"
  info_text+="   Shared Volume: $SHARED_DIR\n"
  info_text+="   Log File: $LOG_FILE\n"
  info_text+="   MOTD Directory: $MOTD_DIR\n"
  info_text+="   Network: $NETWORK_NAME\n\n"
  
  total_images=$(yq '.images | length' "$CONFIG_FILE")
  info_text+="📦 Images:\n"
  info_text+="   Total Available: $total_images\n\n"
  
  running=$(docker ps --filter "label=playground.managed=true" -q | wc -l)
  info_text+="🚀 Containers:\n"
  info_text+="   Currently Running: $running\n\n"
  
  if [ $running -gt 0 ]; then
    info_text+="Active Containers:\n"
    while IFS= read -r container; do
      info_text+="   • $container\n"
    done < <(docker ps --filter "label=playground.managed=true" --format "{{.Names}}")
  fi
  
  whiptail --title "System Information" --msgbox "$info_text" 24 75 --scrolltext
}

show_help() {
  local help_text="╔══════════════════════════════════════════════════════════════╗\n"
  help_text+="║              Docker Playground Manager - Help                ║\n"
  help_text+="╚══════════════════════════════════════════════════════════════╝\n\n"
  
  help_text+="🚀 Quick Start:\n"
  help_text+="   1. Select 'Start containers' or 'Start by category'\n"
  help_text+="   2. Choose your desired images\n"
  help_text+="   3. Use 'Enter container' to access them\n\n"
  
  help_text+="📁 Shared Volume:\n"
  help_text+="   Files in $SHARED_DIR are accessible\n"
  help_text+="   from all containers at /shared\n\n"
  
  help_text+="💡 Tips:\n"
  help_text+="   • Some containers show helpful guides (MOTD) on entry\n"
  help_text+="   • Use 'Search images' to quickly find what you need\n"
  help_text+="   • 'Dashboard' shows an overview of your environment\n"
  help_text+="   • Containers persist between script restarts\n"
  help_text+="   • Use 'Cleanup' to remove everything and start fresh\n\n"
  
  help_text+="🔧 Container Management:\n"
  help_text+="   • Start: Launch new containers\n"
  help_text+="   • Stop: Shutdown and remove containers\n"
  help_text+="   • Enter: Get an interactive shell\n"
  help_text+="   • Logs: View container output\n"
  help_text+="   • Stats: Monitor resource usage\n\n"
  
  help_text+="📝 Categories:\n"
  help_text+="   linux, programming, database, messaging,\n"
  help_text+="   webserver, devops, monitoring, ml, utility\n"
  
  whiptail --title "Help & Documentation" --msgbox "$help_text" 30 70 --scrolltext
}

#############################################
# Main Menu
#############################################
main_menu() {
  while true; do
    print_header
    
    # Show quick stats
    running=$(docker ps --filter "label=playground.managed=true" -q | wc -l)
    total=$(yq '.images | length' "$CONFIG_FILE")
    echo -e "${CYAN}Status:${NC} ${GREEN}$running${NC} running / ${YELLOW}$total${NC} available\n"
    
    choice=$(whiptail --title "Docker Playground Manager v2.4" \
      --menu "Choose an action:" 24 75 16 \
      "1" "▶️  Start containers                [Container]" \
      "2" "🎯 Start by category              [Container]" \
      "3" "⏹️  Stop containers                 [Container]" \
      "4" "💻 Enter a container              [Container]" \
      "5" "📋 List active containers         [Monitor]" \
      "6" "📊 View container logs            [Monitor]" \
      "7" "🔄 Restart container              [Monitor]" \
      "8" "📈 Container statistics           [Monitor]" \
      "9" "📺 Dashboard                      [Monitor]" \
      "10" "🔍 Search images                  [Tools]" \
      "11" "📚 Browse catalog                 [Tools]" \
      "12" "⚙  System information             [Tools]" \
      "13" "❓ Help                           [Tools]" \
      "14" "📤 Export logs                    [Maintenance]" \
      "15" "🧹 Cleanup (remove all)           [Maintenance]" \
      "16" "❌ Exit                           " 3>&1 1>&2 2>&3)
    
    case $choice in
      1) start_containers ;;
      2) start_by_category ;;
      3) stop_containers ;;
      4) enter_container ;;
      5) list_containers ;;
      6) container_logs ;;
      7) restart_container ;;
      8) container_stats ;;
      9) show_dashboard ;;
      10) quick_search ;;
      11) browse_catalog ;;
      12) show_info ;;
      13) show_help ;;
      14) export_logs ;;
      15) cleanup_all ;;
      16)
        log "Playground manager exited"
        clear
        echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  Thank you for using Docker Playground! 🐳     ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
        echo ""
        exit 0
        ;;
      *)
        exit 0
        ;;
    esac
  done
}

#############################################
# Main Execution
#############################################

check_dependencies
initialize_environment
main_menu