#!/bin/bash
set -e

echo "→ Initializing MySQL database for Mail Stack..." | tee -a /tmp/mysql-init.log

# Wait for MySQL to be ready
MAX_WAIT=60
COUNT=0
while [ $COUNT -lt $MAX_WAIT ]; do
    if mysqladmin ping -h localhost --silent 2>/dev/null; then
        echo "✓ MySQL is ready!" | tee -a /tmp/mysql-init.log
        break
    fi
    echo "→ MySQL not ready, retrying ($COUNT/$MAX_WAIT)..." | tee -a /tmp/mysql-init.log
    sleep 2
    COUNT=$((COUNT + 2))
done

if [ $COUNT -ge $MAX_WAIT ]; then
    echo "⚠️ MySQL service not available after $MAX_WAIT seconds" | tee -a /tmp/mysql-init.log
    exit 1
fi

# Try different authentication methods
echo "→ Setting up database and users..." | tee -a /tmp/mysql-init.log

# First try without password (default for many MySQL Docker images)
if mysql -h localhost -u root <<EOF 2>/dev/null
SELECT 1;
EOF
then
    echo "→ Using root without password" | tee -a /tmp/mysql-init.log
    MYSQL_CMD="mysql -h localhost -u root"
# Then try with the expected password
elif mysql -h localhost -u root -pmail_root_pass -e "SELECT 1;" 2>/dev/null; then
    echo "→ Using root with password" | tee -a /tmp/mysql-init.log
    MYSQL_CMD="mysql -h localhost -u root -pmail_root_pass"
# Try with MYSQL_ROOT_PASSWORD environment variable
elif [ ! -z "$MYSQL_ROOT_PASSWORD" ] && mysql -h localhost -u root -p"$MYSQL_ROOT_PASSWORD" -e "SELECT 1;" 2>/dev/null; then
    echo "→ Using root with env password" | tee -a /tmp/mysql-init.log
    MYSQL_CMD="mysql -h localhost -u root -p$MYSQL_ROOT_PASSWORD"
else
    echo "⚠️ Could not connect to MySQL with any method" | tee -a /tmp/mysql-init.log
    echo "→ Trying to set root password..." | tee -a /tmp/mysql-init.log
    mysqladmin -u root password 'mail_root_pass' 2>/dev/null || true
    MYSQL_CMD="mysql -h localhost -u root -pmail_root_pass"
fi

# Create database and user if not exists
$MYSQL_CMD <<EOF 2>&1 | tee -a /tmp/mysql-init.log || true
-- Create database if not exists
CREATE DATABASE IF NOT EXISTS mailserver DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create mail user if not exists
CREATE USER IF NOT EXISTS 'mailuser'@'%' IDENTIFIED BY 'mail_secure_pass';
GRANT ALL PRIVILEGES ON mailserver.* TO 'mailuser'@'%';
FLUSH PRIVILEGES;

-- Use mailserver database
USE mailserver;

-- Create virtual domains table
CREATE TABLE IF NOT EXISTS virtual_domains (
  id INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create virtual users table
CREATE TABLE IF NOT EXISTS virtual_users (
  id INT NOT NULL AUTO_INCREMENT,
  domain_id INT NOT NULL,
  email VARCHAR(255) NOT NULL,
  password VARCHAR(255) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY email (email),
  FOREIGN KEY (domain_id) REFERENCES virtual_domains(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create virtual aliases table
CREATE TABLE IF NOT EXISTS virtual_aliases (
  id INT NOT NULL AUTO_INCREMENT,
  domain_id INT NOT NULL,
  source VARCHAR(255) NOT NULL,
  destination VARCHAR(255) NOT NULL,
  PRIMARY KEY (id),
  FOREIGN KEY (domain_id) REFERENCES virtual_domains(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default domains (use REPLACE to update if exists)
REPLACE INTO virtual_domains (id, name) VALUES (1, 'localhost.local');
REPLACE INTO virtual_domains (id, name) VALUES (2, 'example.com');

-- Delete existing users to avoid conflicts
DELETE FROM virtual_users WHERE email IN ('admin@localhost.local', 'user1@localhost.local', 'admin@example.com');

-- Insert users with correct PLAIN-MD5 passwords that Dovecot recognizes
-- Password for admin@localhost.local is 'admin123' → MD5: 0e81823a7bbd732151176f069df18b500
INSERT INTO virtual_users (domain_id, email, password) VALUES 
  (1, 'admin@localhost.local', '{PLAIN-MD5}AZICOnu9cyUFFvBp3xi1AA==');

-- Password for user1@localhost.local is 'user123' → MD5: 6ed14ba9986e3615423dfc a255b04e3f
INSERT INTO virtual_users (domain_id, email, password) VALUES 
  (1, 'user1@localhost.local', '{PLAIN-MD5}atFLqZhuNhVCPfyiVtBOPw==');

-- Password for admin@example.com is 'admin123'
INSERT INTO virtual_users (domain_id, email, password) VALUES 
  (2, 'admin@example.com', '{PLAIN-MD5}AZICOnu9cyUFFvBp3xi1AA==');

-- Insert default aliases
INSERT IGNORE INTO virtual_aliases (domain_id, source, destination) VALUES 
  (1, 'postmaster@localhost.local', 'admin@localhost.local'),
  (1, 'webmaster@localhost.local', 'admin@localhost.local'),
  (2, 'postmaster@example.com', 'admin@example.com'),
  (2, 'webmaster@example.com', 'admin@example.com');

EOF

echo "✓ Mail server database structure created" | tee -a /tmp/mysql-init.log

# Check if Roundcube schema needs to be loaded
echo "→ Checking Roundcube schema..." | tee -a /tmp/mysql-init.log
TABLES_COUNT=$(mysql -h localhost -u mailuser -pmail_secure_pass mailserver -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='mailserver' AND table_name LIKE 'rc_%';" -s 2>/dev/null || echo "0")

if [ "$TABLES_COUNT" -eq "0" ]; then
    echo "→ Roundcube tables not found. Will be created when Roundcube container starts." | tee -a /tmp/mysql-init.log
else
    echo "✓ Roundcube tables already exist ($TABLES_COUNT tables found)" | tee -a /tmp/mysql-init.log
fi

echo "✓ MySQL initialization completed successfully" | tee -a /tmp/mysql-init.log
exit 0

