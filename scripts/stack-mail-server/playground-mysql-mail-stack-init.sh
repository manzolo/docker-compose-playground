#!/bin/bash
set -e

MAX_WAIT=60
COUNT=0
while [ $COUNT -lt $MAX_WAIT ]; do
if mysqladmin ping -u root -pmail_root_pass --silent 2>/dev/null; then
    echo "✓ MySQL is ready!"
    break
fi
sleep 2
COUNT=$((COUNT + 2))
done
sleep 5

mysql -u root -pmail_root_pass mailserver << 'MYSQLEOF'
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    domain VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    quota_bytes BIGINT DEFAULT 10737418240,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_domain (username, domain)
);

CREATE TABLE IF NOT EXISTS virtual_domains (
    id INT AUTO_INCREMENT PRIMARY KEY,
    domain_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS virtual_aliases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_email VARCHAR(255) NOT NULL,
    target_email VARCHAR(255) NOT NULL,
    domain_id INT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_id) REFERENCES virtual_domains(id)
);

CREATE TABLE IF NOT EXISTS mail_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    direction ENUM('inbound', 'outbound') NOT NULL,
    from_addr VARCHAR(255),
    to_addr VARCHAR(255),
    subject VARCHAR(255),
    status ENUM('delivered', 'failed', 'spam', 'bounced') NOT NULL,
    message_size INT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_timestamp (timestamp),
    INDEX idx_status (status)
);

CREATE TABLE IF NOT EXISTS spam_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email_address VARCHAR(255),
    spam_score FLOAT,
    is_spam BOOLEAN,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT IGNORE INTO users (username, domain, email, password, enabled) VALUES
('admin', 'localhost', 'admin@localhost', SHA2('admin123', 256), TRUE),
('user1', 'localhost', 'user1@localhost', SHA2('user123', 256), TRUE);

INSERT IGNORE INTO virtual_domains (domain_name, description, enabled) VALUES
('localhost', 'Local mail domain', TRUE),
('example.com', 'Example domain', TRUE);

INSERT IGNORE INTO virtual_aliases (source_email, target_email, enabled) VALUES
('postmaster@localhost', 'admin@localhost', TRUE),
('webmaster@localhost', 'admin@localhost', TRUE);

MYSQLEOF

echo "✓ MySQL initialized successfully"
exit 0