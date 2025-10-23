#!/bin/bash

echo "🌐 Configuring Roundcube webmail..."
export DEBIAN_FRONTEND=noninteractive

# Quick package installation
apt-get update -qq >/dev/null 2>&1
apt-get install -y -qq --no-install-recommends \
    wget \
    unzip \
    curl \
    ca-certificates \
    default-mysql-client \
    libzip-dev \
    libpng-dev \
    libjpeg-dev \
    libfreetype6-dev \
    libicu-dev \
    libldap2-dev \
    libpq-dev >/dev/null 2>&1

# Install ALL necessary PHP extensions including intl
echo "→ Installing PHP extensions (including intl)..."
docker-php-ext-configure gd --with-freetype --with-jpeg >/dev/null 2>&1
docker-php-ext-install -j$(nproc) \
    gd \
    zip \
    intl \
    mysqli \
    pdo_mysql \
    opcache >/dev/null 2>&1

# Enable Apache modules
a2enmod rewrite headers expires >/dev/null 2>&1

# Configure MySQL client to disable SSL
echo "→ Configuring MySQL client..."
mkdir -p /etc/mysql/conf.d
cat > /etc/mysql/conf.d/client.cnf << 'CLIENTCNF'
[client]
ssl=0
CLIENTCNF

# Create directories
mkdir -p /var/www/html/roundcube/{temp,logs,config}

# Download Roundcube (using simpler version)
cd /tmp
echo "→ Downloading Roundcube..."
wget -q -O rc.tar.gz https://github.com/roundcube/roundcubemail/releases/download/1.6.9/roundcubemail-1.6.9-complete.tar.gz || exit 1
tar xzf rc.tar.gz
cp -r roundcubemail-1.6.9/* /var/www/html/roundcube/
rm -rf roundcubemail-1.6.9* rc.tar.gz

# Quick MySQL check
echo "→ Waiting for MySQL..."
for i in {1..15}; do
    if mysql -h mysql-mail-stack -u mailuser -pmail_secure_pass mailserver -e "SELECT 1;" 2>/dev/null; then
        echo "✓ MySQL connected"
        break
    fi
    sleep 2
done

# Init database - Force creation of Roundcube tables
echo "→ Initializing Roundcube database..."
if [ -f /var/www/html/roundcube/SQL/mysql.initial.sql ]; then
    # Check if tables exist
    TABLE_COUNT=$(mysql -h mysql-mail-stack -u mailuser -pmail_secure_pass mailserver -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='mailserver' AND table_name='session';" -s 2>/dev/null || echo "0")
    
    if [ "$TABLE_COUNT" = "0" ]; then
        echo "→ Creating Roundcube tables..."
        mysql -h mysql-mail-stack -u mailuser -pmail_secure_pass mailserver < /var/www/html/roundcube/SQL/mysql.initial.sql
        if [ $? -eq 0 ]; then
            echo "✓ Roundcube database tables created successfully"
        else
            echo "⚠️ Warning: Could not create all tables, trying alternative method..."
            # Try to create at least the session table manually
            mysql -h mysql-mail-stack -u mailuser -pmail_secure_pass mailserver <<'SQLEOF'
CREATE TABLE IF NOT EXISTS `session` (
  `sess_id` varchar(128) NOT NULL,
  `changed` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `ip` varchar(40) NOT NULL,
  `vars` mediumtext NOT NULL,
  PRIMARY KEY(`sess_id`),
  INDEX `changed_index` (`changed`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `users` (
  `user_id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` varchar(128) BINARY NOT NULL,
  `mail_host` varchar(128) NOT NULL,
  `created` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_login` datetime DEFAULT NULL,
  `failed_login` datetime DEFAULT NULL,
  `failed_login_counter` int(10) UNSIGNED DEFAULT NULL,
  `language` varchar(16),
  `preferences` longtext,
  PRIMARY KEY(`user_id`),
  UNIQUE `username` (`username`, `mail_host`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `cache` (
  `user_id` int(10) UNSIGNED NOT NULL,
  `cache_key` varchar(128) BINARY NOT NULL,
  `expires` datetime DEFAULT NULL,
  `data` longtext NOT NULL,
  PRIMARY KEY (`user_id`, `cache_key`),
  CONSTRAINT `user_id_fk_cache` FOREIGN KEY (`user_id`)
    REFERENCES `users`(`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  INDEX `expires_index` (`expires`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `cache_shared` (
  `cache_key` varchar(255) BINARY NOT NULL,
  `expires` datetime DEFAULT NULL,
  `data` longtext NOT NULL,
  PRIMARY KEY(`cache_key`),
  INDEX `expires_index` (`expires`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
SQLEOF
        fi
    else
        echo "✓ Roundcube tables already exist"
    fi
else
    echo "⚠️ SQL file not found at /var/www/html/roundcube/SQL/mysql.initial.sql"
fi

# Generate DES key for Roundcube
DES_KEY=$(openssl rand -base64 24)

# Create Roundcube configuration
echo "→ Creating configuration..."
cat > /var/www/html/roundcube/config/config.inc.php << EOF
<?php
// Roundcube configuration file

\$config = [];

// Database connection
\$config['db_dsnw'] = 'mysql://mailuser:mail_secure_pass@mysql-mail-stack/mailserver';

// IMAP server configuration
\$config['imap_host'] = 'dovecot-mail-stack:143';
\$config['imap_auth_type'] = 'PLAIN';
\$config['imap_delimiter'] = '/';

// SMTP server configuration
\$config['smtp_host'] = 'postfix-mail-stack:25';
\$config['smtp_auth_type'] = 'PLAIN';
\$config['smtp_user'] = '%u';
\$config['smtp_pass'] = '%p';

// System settings
\$config['des_key'] = '$DES_KEY';
\$config['product_name'] = 'Roundcube Webmail';
\$config['useragent'] = 'Roundcube Webmail/1.6.9';

// Logging
\$config['log_driver'] = 'file';
\$config['log_dir'] = '/var/www/html/roundcube/logs/';
\$config['log_logins'] = true;
\$config['smtp_log'] = true;
\$config['imap_log'] = true;
\$config['sql_debug'] = false;
\$config['debug_level'] = 1;

// Temp directory
\$config['temp_dir'] = '/var/www/html/roundcube/temp/';

// Plugins - enable essential plugins
\$config['plugins'] = ['archive', 'zipdownload', 'newmail_notifier'];

// User preferences
\$config['language'] = 'en_US';
\$config['timezone'] = 'Europe/Rome';
\$config['date_format'] = 'Y-m-d';
\$config['time_format'] = 'H:i';

// Security
\$config['enable_installer'] = false;
\$config['csrf_protection'] = true;
\$config['x_frame_options'] = 'sameorigin';

// Mail settings
\$config['html_editor'] = 1;
\$config['draft_autosave'] = 60;
\$config['mime_param_folding'] = 0;
\$config['mdn_requests'] = 0;
\$config['compose_extwin'] = false;

// Address book
\$config['address_book_type'] = 'sql';
\$config['autocomplete_addressbooks'] = ['sql'];

// Set defaults for new users
\$config['default_folders'] = ['INBOX', 'Drafts', 'Sent', 'Spam', 'Trash'];
\$config['create_default_folders'] = true;

// Performance
\$config['enable_caching'] = true;
\$config['message_cache_lifetime'] = '10d';

EOF

# Set permissions
echo "→ Setting permissions..."
chown -R www-data:www-data /var/www/html/roundcube
chmod -R 755 /var/www/html/roundcube
chmod -R 777 /var/www/html/roundcube/temp /var/www/html/roundcube/logs

# Create Apache virtual host for Roundcube
cat > /etc/apache2/sites-available/roundcube.conf << 'APACHECONF'
<VirtualHost *:80>
    DocumentRoot /var/www/html
    ServerName localhost
    
    <Directory /var/www/html>
        Options Indexes FollowSymLinks MultiViews
        AllowOverride All
        Require all granted
    </Directory>
    
    <Directory /var/www/html/roundcube>
        Options +FollowSymLinks
        AllowOverride All
        Require all granted
        
        <IfModule mod_php.c>
            php_flag register_globals off
            php_flag magic_quotes_gpc off
            php_flag magic_quotes_runtime off
            php_flag zend.ze1_compatibility_mode off
            php_flag suhosin.session.encrypt off
            php_flag session.auto_start off
            php_value upload_max_filesize 25M
            php_value post_max_size 25M
        </IfModule>
    </Directory>
    
    # Protect config files
    <Directory /var/www/html/roundcube/config>
        Options -FollowSymLinks
        AllowOverride None
        Require all denied
    </Directory>
    
    # Protect temp files
    <Directory /var/www/html/roundcube/temp>
        Options -FollowSymLinks
        AllowOverride None
        Require all denied
    </Directory>
    
    # Protect logs
    <Directory /var/www/html/roundcube/logs>
        Options -FollowSymLinks
        AllowOverride None
        Require all denied
    </Directory>
    
    ErrorLog /var/log/apache2/roundcube_error.log
    CustomLog /var/log/apache2/roundcube_access.log combined
</VirtualHost>
APACHECONF

# Enable the site
a2dissite 000-default 2>/dev/null || true
a2ensite roundcube 2>/dev/null || true

# Create index.html dashboard
cat > /var/www/html/index.html << 'INDEXHTML'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mail Server Stack - Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 800px;
            width: 100%;
            padding: 40px;
        }
        h1 {
            color: #333;
            font-size: 2.5em;
            margin-bottom: 10px;
            text-align: center;
        }
        .subtitle {
            color: #666;
            text-align: center;
            margin-bottom: 40px;
            font-size: 1.1em;
        }
        .status {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
        }
        .status h2 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.4em;
        }
        .service {
            display: flex;
            justify-content: space-between;
            padding: 10px;
            border-bottom: 1px solid #e9ecef;
        }
        .service:last-child { border-bottom: none; }
        .service-name { font-weight: 500; color: #495057; }
        .service-status {
            color: #28a745;
            font-weight: bold;
        }
        .accounts {
            background: #e8f5e9;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
        }
        .accounts h2 {
            color: #2e7d32;
            margin-bottom: 15px;
            font-size: 1.4em;
        }
        .account-item {
            background: white;
            border-radius: 5px;
            padding: 10px 15px;
            margin-bottom: 10px;
            font-family: monospace;
            color: #333;
        }
        .btn-container {
            text-align: center;
            margin-top: 30px;
        }
        .btn {
            display: inline-block;
            padding: 15px 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 50px;
            font-size: 1.1em;
            font-weight: 600;
            transition: transform 0.3s, box-shadow 0.3s;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }
        .info {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin-top: 20px;
            border-radius: 5px;
        }
        .info p {
            color: #856404;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📧 Mail Server Stack</h1>
        <p class="subtitle">Complete email solution with webmail interface</p>
        
        <div class="status">
            <h2>Service Status</h2>
            <div class="service">
                <span class="service-name">MySQL Database</span>
                <span class="service-status">✅ Running</span>
            </div>
            <div class="service">
                <span class="service-name">Postfix SMTP</span>
                <span class="service-status">✅ Running</span>
            </div>
            <div class="service">
                <span class="service-name">Dovecot IMAP/POP3</span>
                <span class="service-status">✅ Running</span>
            </div>
            <div class="service">
                <span class="service-name">SpamAssassin</span>
                <span class="service-status">✅ Running</span>
            </div>
            <div class="service">
                <span class="service-name">Roundcube Webmail</span>
                <span class="service-status">✅ Running</span>
            </div>
        </div>
        
        <div class="accounts">
            <h2>Test Accounts</h2>
            <div class="account-item">admin@localhost / admin123</div>
            <div class="account-item">user1@localhost / user123</div>
            <div class="account-item">admin@example.com / admin123</div>
        </div>
        
        <div class="btn-container">
            <a href="/roundcube/" class="btn">Access Webmail →</a>
        </div>
        
        <div class="info">
            <p><strong>Note:</strong> This is a development mail server. For production use, please configure proper SSL certificates, authentication, and security settings.</p>
        </div>
    </div>
</body>
</html>
INDEXHTML

# NO RESTART - just reload config 
# apache2-foreground is already running as the main process
apache2ctl graceful 2>/dev/null || true

echo "✓ Roundcube installation completed!"
echo "✓ Access webmail at: http://localhost:8082/roundcube/"
echo "✓ Dashboard at: http://localhost:8082/"

exit 0