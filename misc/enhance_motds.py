#!/usr/bin/env python3
"""
Script to enhance MOTDs with specific, practical commands
"""

import re
from pathlib import Path

CONFIG_DIR = Path("config.d")

# Enhanced MOTD templates with specific commands
ENHANCED_MOTDS = {
    # Databases
    "mysql-5.7": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                   MySQL 5.7 Quick Reference                   ║
      ╚══════════════════════════════════════════════════════════════╝

      🔐 Connection Info:
         Port: 3305
         User: root / Password: playground

      📊 Quick Connect:
         mysql -u root -pplayground                    # Connect as root

      🔍 Quick Commands:
         mysql -u root -pplayground -e "SELECT version();"  # Check version
         mysql -u root -pplayground -e "SHOW DATABASES;"    # List databases

      💾 Backup:
         mysqldump -u root -pplayground --all-databases > /shared/backup.sql

      📁 Useful Directories:
         /shared                                   # Shared with host""",

    "redis-alpine": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                   Redis Alpine Quick Reference                ║
      ╚══════════════════════════════════════════════════════════════╝

      🔐 Connection Info:
         Port: 6380

      📊 Quick Connect:
         redis-cli                                 # Connect to Redis

      🔍 Quick Commands:
         redis-cli INFO server                     # Server info
         redis-cli SET mykey "Hello"               # Set value
         redis-cli GET mykey                       # Get value
         redis-cli KEYS "*"                        # List all keys

      💡 Tips:
         • Lightweight Alpine variant
         • In-memory data structure store
         • Use /shared for RDB/AOF backups""",

    "neo4j": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                   Neo4j Quick Reference                       ║
      ╚══════════════════════════════════════════════════════════════╝

      🔐 Connection Info:
         HTTP: http://localhost:7474
         Bolt: bolt://localhost:7687
         User: neo4j / Password: (check env)

      📊 Quick Cypher Commands:
         cypher-shell                              # Connect to Neo4j shell

         # Create node
         CREATE (n:Person {name: 'Alice', age: 30})

         # Find nodes
         MATCH (n:Person) RETURN n

         # Check version
         CALL dbms.components() YIELD name, versions

      💡 Tips:
         • Graph database for connected data
         • Access web UI at http://localhost:7474""",

    "cassandra": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                   Cassandra Quick Reference                   ║
      ╚══════════════════════════════════════════════════════════════╝

      📊 Quick Connect:
         cqlsh                                     # Connect to Cassandra

      🔍 Quick CQL Commands:
         SELECT release_version FROM system.local;  # Check version
         DESCRIBE KEYSPACES;                        # List keyspaces
         CREATE KEYSPACE myks WITH replication = {'class':'SimpleStrategy', 'replication_factor':1};

      🔧 Cluster Management:
         nodetool status                           # Check cluster status
         nodetool info                             # Node information

      💡 Tips:
         • Distributed NoSQL database
         • CQL is similar to SQL""",

    "elasticsearch": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                Elasticsearch Quick Reference                  ║
      ╚══════════════════════════════════════════════════════════════╝

      🔐 Connection Info:
         HTTP: http://localhost:9200

      🔍 Quick Commands:
         # Check cluster health
         curl http://localhost:9200/_cluster/health

         # Check version
         curl http://localhost:9200

         # List indices
         curl http://localhost:9200/_cat/indices

         # Create index
         curl -X PUT http://localhost:9200/myindex

         # Search
         curl http://localhost:9200/myindex/_search

      💡 Tips:
         • Full-text search engine
         • REST API based""",

    "influxdb": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  InfluxDB Quick Reference                     ║
      ╚══════════════════════════════════════════════════════════════╝

      🔐 Connection Info:
         HTTP: http://localhost:8086

      📊 Quick Commands:
         influx                                    # Connect to CLI

         # Check version
         influx version

         # Create database
         CREATE DATABASE mydb

         # Write data
         INSERT cpu,host=server01 value=0.64

         # Query data
         SELECT * FROM cpu

      💡 Tips:
         • Time series database
         • Perfect for metrics and monitoring""",

    "couchdb": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  CouchDB Quick Reference                      ║
      ╚══════════════════════════════════════════════════════════════╝

      🔐 Connection Info:
         HTTP: http://localhost:5984
         Web UI (Fauxton): http://localhost:5984/_utils

      🔍 Quick Commands:
         # Check version
         curl http://localhost:5984

         # List databases
         curl http://localhost:5984/_all_dbs

         # Create database
         curl -X PUT http://localhost:5984/mydb

         # Create document
         curl -X POST http://localhost:5984/mydb -H "Content-Type: application/json" -d '{"name":"Alice"}'

      💡 Tips:
         • Document-oriented NoSQL database
         • Access Fauxton web UI for management""",

    # Programming Languages
    "php-5.6": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                    PHP 5.6 Quick Reference                    ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         php -v                                    # Check PHP version
         php -i | head -20                         # PHP info
         php -r "echo 'Hello!';"                   # Run code directly
         php -S 0.0.0.0:8000 -t /shared            # Start dev server

      📝 Quick Test:
         echo '<?php phpinfo(); ?>' > /shared/info.php
         php /shared/info.php | head -20

      💡 Tips:
         • Legacy PHP version for older projects
         • Keep projects in /shared""",

    "php-7.2": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                    PHP 7.2 Quick Reference                    ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         php -v                                    # Check PHP version
         php -i | head -20                         # PHP info
         php -r "echo 'Hello!';"                   # Run code directly
         php -S 0.0.0.0:8000 -t /shared            # Start dev server

      💡 Tips:
         • PHP 7.2 with performance improvements
         • Keep projects in /shared""",

    "php-7.4": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                    PHP 7.4 Quick Reference                    ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         php -v                                    # Check PHP version
         php -i | head -20                         # PHP info
         php -r "echo 'Hello!';"                   # Run code directly
         php -S 0.0.0.0:8000 -t /shared            # Start dev server

      💡 Tips:
         • PHP 7.4 with typed properties
         • Keep projects in /shared""",

    "php-fpm": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  PHP-FPM Quick Reference                      ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         php -v                                    # Check PHP version
         php-fpm -v                                # Check FPM version
         php -i | head -20                         # PHP info

      💡 Tips:
         • FastCGI Process Manager for high performance
         • Use with Nginx for production
         • Keep projects in /shared""",

    "ruby-3.3": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                   Ruby 3.3 Quick Reference                    ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         ruby --version                            # Check Ruby version
         irb                                       # Interactive Ruby
         ruby -e "puts 'Hello World!'"             # Run Ruby code

      📦 Gem Management:
         gem --version                             # Gem version
         gem install rails                         # Install gem
         gem list                                  # List installed gems

      📝 Quick Script:
         echo "puts 'Ruby ' + RUBY_VERSION" > /shared/test.rb
         ruby /shared/test.rb

      💡 Tips:
         • Ruby 3.3 with YJIT improvements
         • Use /shared for your projects""",

    "ruby-alpine": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                Ruby Alpine Quick Reference                    ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         ruby --version                            # Check Ruby version
         irb                                       # Interactive Ruby
         ruby -e "puts 'Hello!'"                   # Run Ruby code
         gem install package_name                  # Install gem

      💡 Tips:
         • Lightweight Alpine variant
         • Perfect for production deployments""",

    "deno": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                   Deno Quick Reference                        ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         deno --version                            # Check Deno version
         deno repl                                 # Interactive REPL
         deno run script.ts                        # Run TypeScript file
         deno run --allow-net script.ts            # Run with permissions

      📝 Quick Test:
         echo 'console.log("Hello from Deno!")' > /shared/test.ts
         deno run /shared/test.ts

      🔧 Useful Commands:
         deno info                                 # Show environment info
         deno fmt script.ts                        # Format code
         deno lint script.ts                       # Lint code

      💡 Tips:
         • Secure by default (requires explicit permissions)
         • Built-in TypeScript support
         • No package.json or node_modules needed""",

    "elixir": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  Elixir Quick Reference                       ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         elixir --version                          # Check Elixir version
         iex                                       # Interactive Elixir
         elixir -e "IO.puts('Hello!')"             # Run Elixir code

      📦 Mix (Build Tool):
         mix new myapp                             # Create new project
         mix deps.get                              # Install dependencies
         mix test                                  # Run tests

      💡 Tips:
         • Functional language built on Erlang VM
         • Great for concurrent applications""",

    "erlang": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  Erlang Quick Reference                       ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         erl                                       # Erlang shell
         erl -eval 'erlang:display(erlang:system_info(otp_release)), halt().' -noshell  # Version

      📝 In Erlang shell:
         1> io:format("Hello World~n").            # Print Hello World
         2> q().                                   # Quit shell

      💡 Tips:
         • Designed for concurrent, distributed systems
         • Powers many telecom systems""",

    "dotnet-8": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  .NET 8 Quick Reference                       ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         dotnet --version                          # Check .NET version
         dotnet --info                             # Detailed info
         dotnet new console -o /shared/myapp       # Create console app
         dotnet run                                # Run application

      📦 Package Management:
         dotnet add package Newtonsoft.Json        # Add NuGet package
         dotnet restore                            # Restore dependencies
         dotnet build                              # Build project

      💡 Tips:
         • .NET 8 LTS with C# 12
         • Cross-platform development""",

    "haskell": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  Haskell Quick Reference                      ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         ghci                                      # GHC interactive
         ghc --version                             # Check version
         runhaskell script.hs                      # Run Haskell script

      📝 In GHCi:
         Prelude> 2 + 2                            # Simple calculation
         Prelude> :type (+)                        # Check type
         Prelude> :quit                            # Exit

      💡 Tips:
         • Purely functional programming language
         • Strong static typing""",

    "kotlin": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  Kotlin Quick Reference                       ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         kotlinc -version                          # Check Kotlin version
         kotlinc script.kt -include-runtime -d app.jar  # Compile
         java -jar app.jar                         # Run compiled jar
         kotlinc-jvm -script script.kts            # Run as script

      📝 Quick Script:
         echo 'println("Hello from Kotlin!")' > /shared/hello.kts
         kotlinc-jvm -script /shared/hello.kts

      💡 Tips:
         • Modern JVM language
         • Fully interoperable with Java""",

    "lua": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                   Lua Quick Reference                         ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         lua -v                                    # Check Lua version
         lua                                       # Interactive mode
         lua script.lua                            # Run Lua script
         lua -e "print('Hello!')"                  # Run code directly

      📦 LuaRocks (Package Manager):
         luarocks install package_name             # Install package
         luarocks list                             # List packages

      💡 Tips:
         • Lightweight scripting language
         • Embedded in many applications""",

    "clang": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  Clang/LLVM Quick Reference                   ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         clang --version                           # Check Clang version
         clang hello.c -o hello                    # Compile C program
         clang++ hello.cpp -o hello                # Compile C++ program
         ./hello                                   # Run compiled program

      📝 Quick Test:
         echo 'int main() { printf("Hello!\\n"); return 0; }' > /shared/test.c
         clang /shared/test.c -o /shared/test && /shared/test

      💡 Tips:
         • LLVM-based C/C++ compiler
         • Modern alternative to GCC""",

    "gcc": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                   GCC Quick Reference                         ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         gcc --version                             # Check GCC version
         gcc hello.c -o hello                      # Compile C program
         g++ hello.cpp -o hello                    # Compile C++ program
         ./hello                                   # Run compiled program

      📝 Quick Test:
         echo 'int main() { printf("Hello!\\n"); return 0; }' > /shared/test.c
         gcc /shared/test.c -o /shared/test && /shared/test

      💡 Tips:
         • GNU Compiler Collection
         • Industry standard C/C++ compiler""",

    "perl": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                   Perl Quick Reference                        ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         perl -v                                   # Check Perl version
         perl -e "print 'Hello World!\\n'"         # Run Perl code
         perl script.pl                            # Run Perl script

      📦 CPAN (Package Manager):
         cpan Module::Name                         # Install module
         cpan -l                                   # List installed modules

      💡 Tips:
         • Practical Extraction and Report Language
         • Great for text processing""",

    # Web Servers
    "apache-alpine": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                Apache Alpine Web Server                       ║
      ╚══════════════════════════════════════════════════════════════╝

      🌐 Server Info:
         Port: 8082
         Access: http://localhost:8082
         Document Root: /usr/local/apache2/htdocs

      🔧 Configuration:
         apachectl -v                              # Check Apache version
         apachectl -t                              # Test configuration
         apachectl -k graceful                     # Graceful reload

      📁 Content Directories:
         /usr/local/apache2/htdocs                 # Web root
         /usr/local/apache2/conf/httpd.conf        # Main config

      💡 Tips:
         • Lightweight Alpine variant
         • Place files in /shared for persistence""",

    "apache-latest": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                 Apache Web Server (Latest)                    ║
      ╚══════════════════════════════════════════════════════════════╝

      🌐 Server Info:
         Port: 8083
         Access: http://localhost:8083
         Document Root: /usr/local/apache2/htdocs

      🔧 Configuration:
         apachectl -v                              # Check Apache version
         apachectl -t                              # Test configuration
         apachectl -k graceful                     # Graceful reload

      📁 Content Directories:
         /usr/local/apache2/htdocs                 # Web root
         /usr/local/apache2/conf/httpd.conf        # Main config

      💡 Tips:
         • Full Apache httpd server
         • Place files in /shared for persistence""",

    "caddy": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  Caddy Web Server                             ║
      ╚══════════════════════════════════════════════════════════════╝

      🌐 Server Info:
         Port: 80 (default)
         Automatic HTTPS with Let's Encrypt

      🔧 Quick Commands:
         caddy version                             # Check Caddy version
         caddy reload --config /etc/caddy/Caddyfile  # Reload config
         caddy fmt /etc/caddy/Caddyfile            # Format Caddyfile

      📁 Configuration:
         /etc/caddy/Caddyfile                      # Main config file

      💡 Tips:
         • Automatic HTTPS
         • Modern, easy-to-configure web server""",

    "traefik": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                 Traefik Reverse Proxy                         ║
      ╚══════════════════════════════════════════════════════════════╝

      🌐 Dashboard:
         Access: http://localhost:8080

      🔧 Quick Commands:
         traefik version                           # Check Traefik version

      💡 Tips:
         • Modern reverse proxy and load balancer
         • Automatic service discovery
         • Built for microservices and containers""",

    # DevOps Tools
    "ansible": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                 Ansible Quick Reference                       ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         ansible --version                         # Check Ansible version
         ansible localhost -m ping                 # Test Ansible
         ansible-playbook /shared/playbook.yml     # Run playbook

      📝 Create Sample Playbook:
         cat > /shared/test.yml <<'EOF'
         - hosts: localhost
           tasks:
             - debug: msg="Hello from Ansible"
         EOF
         ansible-playbook /shared/test.yml

      💡 Tips:
         • Agentless automation tool
         • YAML-based playbooks
         • Keep playbooks in /shared""",

    "consul": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  Consul Quick Reference                       ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         consul --version                          # Check Consul version
         consul members                            # List cluster members
         consul catalog services                   # List services

      🌐 Web UI:
         Access: http://localhost:8500

      💡 Tips:
         • Service mesh and service discovery
         • Key/value store
         • Health checking""",

    "vault": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  Vault Quick Reference                        ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         vault --version                           # Check Vault version
         vault status                              # Check seal status
         vault secrets list                        # List secret engines

      🌐 Web UI:
         Access: http://localhost:8200

      💡 Tips:
         • Secrets management platform
         • Encryption as a service
         • Dynamic secrets generation""",

    "gradle": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  Gradle Quick Reference                       ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         gradle --version                          # Check Gradle version
         gradle init                               # Initialize new project
         gradle build                              # Build project
         gradle tasks                              # List available tasks

      📝 Quick Test:
         cd /shared && gradle init --type basic

      💡 Tips:
         • Build automation tool for JVM
         • Groovy or Kotlin DSL
         • Keep projects in /shared""",

    "maven": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  Maven Quick Reference                        ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         mvn --version                             # Check Maven version
         mvn archetype:generate                    # Create new project
         mvn clean install                         # Build project
         mvn test                                  # Run tests

      💡 Tips:
         • Java build and dependency management
         • XML-based configuration (pom.xml)
         • Keep projects in /shared""",

    "packer": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  Packer Quick Reference                       ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         packer --version                          # Check Packer version
         packer init template.pkr.hcl              # Initialize config
         packer validate template.pkr.hcl          # Validate template
         packer build template.pkr.hcl             # Build image

      💡 Tips:
         • Automates machine image creation
         • Supports multiple platforms
         • Keep templates in /shared""",

    # Utilities
    "curl": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                   cURL Quick Reference                        ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         curl --version                            # Check cURL version
         curl https://example.com                  # Fetch URL
         curl -X POST -d 'data' https://api.com    # POST request
         curl -H "Content-Type: application/json" -d '{"key":"value"}' https://api.com

      📝 Useful Options:
         -I                                        # Headers only
         -o file.txt                               # Save to file
         -L                                        # Follow redirects
         -v                                        # Verbose output

      💡 Tips:
         • Command-line tool for transferring data
         • Supports HTTP, FTP, and many protocols""",

    "alpine-tools": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                Alpine Tools Quick Reference                   ║
      ╚══════════════════════════════════════════════════════════════╝

      📦 Package Management:
         apk update                                # Update package list
         apk add package_name                      # Install package
         apk search keyword                        # Search packages
         apk info package_name                     # Package info

      🔧 Common Tools:
         # Network tools
         apk add curl wget netcat-openbsd

         # Development tools
         apk add git vim nano

      💡 Tips:
         • Minimal Alpine Linux with tools
         • Perfect for debugging and testing""",

    # Messaging
    "activemq": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║               Apache ActiveMQ Quick Reference                 ║
      ╚══════════════════════════════════════════════════════════════╝

      🔐 Connection Info:
         Broker URL: tcp://localhost:61616
         Admin Console: http://localhost:8161
         Default: admin / admin

      💡 Tips:
         • JMS message broker
         • Access web console for management
         • Supports multiple protocols""",

    "rabbitmq": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                 RabbitMQ Quick Reference                      ║
      ╚══════════════════════════════════════════════════════════════╝

      🔐 Connection Info:
         AMQP Port: 5672
         Management UI: http://localhost:15672
         Default: guest / guest

      🚀 Quick Commands:
         rabbitmqctl status                        # Check status
         rabbitmqctl list_queues                   # List queues
         rabbitmqctl list_exchanges                # List exchanges

      💡 Tips:
         • Message broker implementing AMQP
         • Access management UI for monitoring""",

    # Monitoring
    "prometheus": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                Prometheus Quick Reference                     ║
      ╚══════════════════════════════════════════════════════════════╗

      🌐 Web UI:
         Access: http://localhost:9090

      🔍 Quick Queries:
         up                                        # Check targets
         rate(metric_name[5m])                     # Rate over 5 minutes
         sum(metric_name)                          # Sum of metric

      💡 Tips:
         • Monitoring and alerting toolkit
         • PromQL query language
         • Time series database""",

    "grafana": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  Grafana Quick Reference                      ║
      ╚══════════════════════════════════════════════════════════════╝

      🌐 Web UI:
         Access: http://localhost:3000
         Default: admin / admin

      💡 Tips:
         • Visualization and analytics platform
         • Create dashboards for metrics
         • Supports multiple data sources""",

    "jupyter": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  Jupyter Quick Reference                      ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Start:
         jupyter notebook --ip=0.0.0.0 --allow-root  # Start Jupyter
         # Access: http://localhost:8888

      📝 JupyterLab:
         jupyter lab --ip=0.0.0.0 --allow-root

      💡 Tips:
         • Interactive computational notebooks
         • Supports Python, R, Julia, and more
         • Keep notebooks in /shared""",

    # Others
    "memcached": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                Memcached Quick Reference                      ║
      ╚══════════════════════════════════════════════════════════════╝

      🔐 Connection Info:
         Port: 11211

      🔍 Quick Test:
         telnet localhost 11211                    # Connect
         stats                                     # Show statistics
         set mykey 0 0 5                           # Set value
         hello
         get mykey                                 # Get value

      💡 Tips:
         • High-performance distributed memory caching
         • Simple key-value store""",

    "zipkin": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  Zipkin Quick Reference                       ║
      ╚══════════════════════════════════════════════════════════════╝

      🌐 Web UI:
         Access: http://localhost:9411

      💡 Tips:
         • Distributed tracing system
         • Helps troubleshoot latency problems
         • Collect timing data for microservices""",

    "netshoot": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                Netshoot Quick Reference                       ║
      ╚══════════════════════════════════════════════════════════════╝

      🔧 Network Troubleshooting Tools:
         # DNS
         nslookup google.com
         dig google.com

         # Connectivity
         ping google.com
         curl -I https://google.com
         wget https://google.com

         # Network info
         netstat -tuln
         ss -tuln
         ip addr
         ifconfig

      💡 Tips:
         • Network troubleshooting Swiss Army knife
         • Contains most network diagnostic tools""",

    "anaconda": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                 Anaconda Quick Reference                      ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         conda --version                           # Check Conda version
         conda create -n myenv python=3.9          # Create environment
         conda activate myenv                      # Activate environment
         conda install numpy pandas                # Install packages

      📦 Environment Management:
         conda env list                            # List environments
         conda list                                # List installed packages
         conda deactivate                          # Deactivate environment

      💡 Tips:
         • Data science platform with 1500+ packages
         • Python and R distribution
         • Keep environments in /shared""",

    "miniconda": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                Miniconda Quick Reference                      ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         conda --version                           # Check Conda version
         conda create -n myenv python=3.9          # Create environment
         conda activate myenv                      # Activate environment
         conda install package_name                # Install package

      💡 Tips:
         • Minimal Anaconda distribution
         • Lighter alternative to full Anaconda
         • Keep environments in /shared""",

    "pytorch": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  PyTorch Quick Reference                      ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Test:
         python -c "import torch; print(torch.__version__)"
         python -c "import torch; print(torch.cuda.is_available())"

      📝 Quick Example:
         python <<EOF
         import torch
         x = torch.rand(5, 3)
         print(x)
         EOF

      💡 Tips:
         • Deep learning framework
         • GPU acceleration support
         • Keep models in /shared""",

    "tensorflow": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                TensorFlow Quick Reference                     ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Test:
         python -c "import tensorflow as tf; print(tf.__version__)"
         python -c "import tensorflow as tf; print(tf.config.list_physical_devices())"

      💡 Tips:
         • Machine learning framework
         • Created by Google Brain team
         • Keep models in /shared""",

    "selenium-chrome": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║              Selenium Chrome Quick Reference                  ║
      ╚══════════════════════════════════════════════════════════════╝

      🔧 Selenium Server:
         Use with Selenium WebDriver for Chrome browser automation

      🌐 VNC Access:
         Port: 5900 (if VNC enabled)

      💡 Tips:
         • Browser automation with Chrome
         • Headless browser testing
         • Use for automated testing""",

    "selenium-firefox": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║             Selenium Firefox Quick Reference                  ║
      ╚══════════════════════════════════════════════════════════════╝

      🔧 Selenium Server:
         Use with Selenium WebDriver for Firefox browser automation

      🌐 VNC Access:
         Port: 5900 (if VNC enabled)

      💡 Tips:
         • Browser automation with Firefox
         • Headless browser testing
         • Use for automated testing""",

    "swift": """    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║                  Swift Quick Reference                        ║
      ╚══════════════════════════════════════════════════════════════╝

      🚀 Quick Commands:
         swift --version                           # Check Swift version
         swift                                     # Interactive REPL
         swift script.swift                        # Run Swift file
         swift build                               # Build project

      📝 Quick Test:
         echo 'print("Hello from Swift!")' > /shared/test.swift
         swift /shared/test.swift

      💡 Tips:
         • Modern programming language by Apple
         • Safe, fast, and expressive
         • Keep projects in /shared""",
}


def enhance_motd(filepath, container_name):
    """Replace basic MOTD with enhanced version if available"""

    if container_name not in ENHANCED_MOTDS:
        return False

    with open(filepath, 'r') as f:
        content = f.read()

    # Check if it has a basic MOTD (contains "Category:" marker)
    if 'Category: ' not in content:
        return False

    # Find and replace the MOTD section
    # Match from "motd: |" to the end of the MOTD (next top-level key or end of file)
    pattern = r'(    motd: \|.*?)(?=\n\w|\Z)'

    new_content = re.sub(
        pattern,
        ENHANCED_MOTDS[container_name],
        content,
        flags=re.DOTALL
    )

    if new_content != content:
        with open(filepath, 'w') as f:
            f.write(new_content)
        return True

    return False


def main():
    print("🚀 Enhancing MOTDs with practical commands...\n")

    enhanced = 0
    skipped = 0

    for filepath in sorted(CONFIG_DIR.glob("*.yml")):
        container_name = filepath.stem

        if enhance_motd(filepath, container_name):
            print(f"✅ Enhanced {filepath.name}")
            enhanced += 1
        else:
            skipped += 1

    print(f"\n{'='*70}")
    print(f"✨ Complete!")
    print(f"   Enhanced: {enhanced} files")
    print(f"   Skipped: {skipped} files (no template or already enhanced)")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
