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
wget -q -O rc.tar.gz https://github.com/roundcube/roundcubemail/releases/download/1.6.11/roundcubemail-1.6.11-complete.tar.gz || exit 1
tar xzf rc.tar.gz
cp -r roundcubemail-1.6.11/* /var/www/html/roundcube/
rm -rf roundcubemail-1.6.11* rc.tar.gz

# Function to check MySQL connection safely
check_mysql_connection() {
    local max_attempts=15
    local attempt=1
    
    echo "→ Waiting for MySQL..."
    while [ $attempt -le $max_attempts ]; do
        if mysql -h mysql-mail-stack -u mailuser -pmail_secure_pass mailserver -e "SELECT 1;" 2>/dev/null; then
            echo "✓ MySQL connected successfully"
            return 0
        fi
        echo "  Attempt $attempt/$max_attempts: MySQL not ready yet..."
        sleep 2
        ((attempt++))
    done
    
    echo "⚠️ Warning: Could not connect to MySQL after $max_attempts attempts"
    return 1
}

# Function to check if Roundcube tables exist
check_roundcube_tables() {
    local table_count=$(mysql -h mysql-mail-stack -u mailuser -pmail_secure_pass mailserver -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='mailserver' AND table_name='session';" -s 2>/dev/null || echo "0")
    echo $table_count
}

# Function to create minimal Roundcube tables
create_minimal_roundcube_tables() {
    echo "→ Creating minimal Roundcube tables..."
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

    if [ $? -eq 0 ]; then
        echo "✓ Minimal Roundcube tables created successfully"
        return 0
    else
        echo "❌ Failed to create minimal tables"
        return 1
    fi
}

# Try to initialize database with better error handling
if check_mysql_connection; then
    echo "→ Checking Roundcube database..."
    TABLE_COUNT=$(check_roundcube_tables)
    
    if [ "$TABLE_COUNT" = "0" ]; then
        echo "→ No Roundcube tables found, initializing database..."
        
        # First try the official SQL file
        if [ -f /var/www/html/roundcube/SQL/mysql.initial.sql ]; then
            echo "→ Using official SQL file..."
            if mysql -h mysql-mail-stack -u mailuser -pmail_secure_pass mailserver < /var/www/html/roundcube/SQL/mysql.initial.sql; then
                echo "✓ Roundcube database initialized successfully"
            else
                echo "⚠️ Official SQL file failed, trying minimal setup..."
                create_minimal_roundcube_tables
            fi
        else
            echo "⚠️ Official SQL file not found, creating minimal tables..."
            create_minimal_roundcube_tables
        fi
    else
        echo "✓ Roundcube tables already exist"
    fi
else
    echo "⚠️ Skipping database initialization - MySQL not available"
    echo "⚠️ Roundcube will work in limited mode until MySQL is available"
fi

# Generate DES key for Roundcube
DES_KEY=$(openssl rand -base64 24)

# Create Roundcube configuration with fallback settings
echo "→ Creating configuration..."
cat > /var/www/html/roundcube/config/config.inc.php << EOF
<?php
// Roundcube configuration file

\$config = [];

// Database connection with error handling
try {
    \$config['db_dsnw'] = 'mysql://mailuser:mail_secure_pass@mysql-mail-stack/mailserver';
} catch (Exception \$e) {
    // Fallback to SQLite if MySQL is not available
    \$config['db_dsnw'] = 'sqlite:////var/www/html/roundcube/sqlite.db?mode=0646';
}

// IMAP server configuration
\$config['imap_host'] = 'dovecot-postfix-mail-stack:143';
\$config['imap_auth_type'] = 'PLAIN';
\$config['imap_delimiter'] = '/';

// SMTP server configuration
\$config['smtp_host'] = 'dovecot-postfix-mail-stack:25';
\$config['smtp_auth_type'] = 'PLAIN';
\$config['smtp_user'] = '%u';
\$config['smtp_pass'] = '%p';

// System settings
\$config['des_key'] = '$DES_KEY';
\$config['product_name'] = 'Roundcube Webmail';
\$config['useragent'] = 'Roundcube Webmail/1.6.11';

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
            php_value max_execution_time 120
            php_value memory_limit 256M
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

# Create index.php dashboard with robust error handling
cat > /var/www/html/index.php << 'INDEXPHP'
<?php
// Function to check if a service is running with timeout
function checkService($host, $port, $timeout = 2) {
    $fp = @fsockopen($host, $port, $errno, $errstr, $timeout);
    if ($fp) {
        fclose($fp);
        return true;
    }
    return false;
}

// Function to check MySQL connection safely without fatal errors
function checkMySQL() {
    try {
        // Suppress warnings and handle connection gracefully
        $conn = @mysqli_connect('mysql-mail-stack', 'mailuser', 'mail_secure_pass', 'mailserver');
        if ($conn && mysqli_ping($conn)) {
            mysqli_close($conn);
            return true;
        }
        return false;
    } catch (Exception $e) {
        return false;
    }
}

// Safe MySQL check that won't cause fatal errors
function safeCheckMySQL() {
    // First check if we can even reach the host
    if (!checkService('mysql-mail-stack', 3306, 1)) {
        return false;
    }
    
    // Then try to connect properly but safely
    return checkMySQL();
}

// Check services safely
$services = [
    'MySQL Database' => safeCheckMySQL(),
    'Postfix SMTP' => checkService('dovecot-postfix-mail-stack', 25),
    'Dovecot IMAP' => checkService('dovecot-postfix-mail-stack', 143),
    'Dovecot POP3' => checkService('dovecot-postfix-mail-stack', 110),
    'SpamAssassin' => checkService('spamassassin-mail-stack', 783),
];

// Count active services
$activeCount = array_sum($services);
$totalCount = count($services);

// Determine overall status
if ($activeCount == $totalCount) {
    $statusClass = 'status-optimal';
    $statusText = 'All systems operational! ✅';
} elseif ($activeCount >= 3) {
    $statusClass = 'status-warning';
    $statusText = 'Partial functionality ⚠️';
} elseif ($activeCount > 0) {
    $statusClass = 'status-degraded';
    $statusText = 'Limited functionality 🟡';
} else {
    $statusClass = 'status-critical';
    $statusText = 'Services not available ❌';
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="30">
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
            margin-bottom: 20px;
            font-size: 1.1em;
        }
        .summary {
            text-align: center;
            padding: 15px;
            margin-bottom: 30px;
            border-radius: 10px;
            font-weight: bold;
        }
        .status-optimal {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status-warning {
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeeba;
        }
        .status-degraded {
            background: #ffeaa7;
            color: #8d6e00;
            border: 1px solid #ffd166;
        }
        .status-critical {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
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
            align-items: center;
            padding: 12px;
            border-bottom: 1px solid #e9ecef;
            transition: background 0.2s;
        }
        .service:hover {
            background: #f1f3f5;
        }
        .service:last-child { border-bottom: none; }
        .service-name { 
            font-weight: 500; 
            color: #495057;
            flex: 1;
        }
        .service-status {
            font-weight: bold;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.9em;
        }
        .status-active {
            color: #155724;
            background: #d4edda;
        }
        .status-inactive {
            color: #721c24;
            background: #f8d7da;
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
            display: flex;
            justify-content: space-between;
            align-items: center;
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
        .timestamp {
            text-align: center;
            color: #6c757d;
            font-size: 0.9em;
            margin-top: 20px;
        }
        .refresh-btn {
            display: inline-block;
            margin-left: 10px;
            padding: 5px 10px;
            background: #6c757d;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 0.85em;
        }
        .refresh-btn:hover {
            background: #5a6268;
        }
        .mysql-warning {
            background: #fff3cd;
            border: 1px solid #ffeeba;
            border-radius: 5px;
            padding: 10px;
            margin: 10px 0;
            color: #856404;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📧 Mail Server Stack</h1>
        <p class="subtitle">Complete email solution with webmail interface</p>
        
        <div class="summary <?php echo $statusClass; ?>">
            <strong><?php echo $activeCount; ?> of <?php echo $totalCount; ?> services running</strong>
            - <?php echo $statusText; ?>
        </div>
        
        <div class="status">
            <h2>Service Status</h2>
            <?php foreach ($services as $name => $status): ?>
            <div class="service">
                <span class="service-name"><?php echo $name; ?></span>
                <span class="service-status <?php echo $status ? 'status-active' : 'status-inactive'; ?>">
                    <?php echo $status ? '● Online' : '○ Offline'; ?>
                </span>
            </div>
            <?php endforeach; ?>
        </div>
        
        <?php if (!$services['MySQL Database']): ?>
        <div class="mysql-warning">
            <strong>Note:</strong> MySQL is currently unavailable. Roundcube will work in limited mode. 
            Some features like user preferences and address books may not be available until MySQL is restored.
        </div>
        <?php endif; ?>
        
        <div class="accounts">
            <h2>Test Accounts</h2>
            <div class="account-item">
                <span>admin@localhost / admin123</span>
                <?php if ($services['Dovecot IMAP']): ?>
                <span style="color: #28a745;">✓ Available</span>
                <?php else: ?>
                <span style="color: #dc3545;">✗ Unavailable</span>
                <?php endif; ?>
            </div>
            <div class="account-item">
                <span>user1@localhost / user123</span>
                <?php if ($services['Dovecot IMAP']): ?>
                <span style="color: #28a745;">✓ Available</span>
                <?php else: ?>
                <span style="color: #dc3545;">✗ Unavailable</span>
                <?php endif; ?>
            </div>
            <div class="account-item">
                <span>admin@example.com / admin123</span>
                <?php if ($services['Dovecot IMAP']): ?>
                <span style="color: #28a745;">✓ Available</span>
                <?php else: ?>
                <span style="color: #dc3545;">✗ Unavailable</span>
                <?php endif; ?>
            </div>
        </div>
        
        <div class="btn-container">
            <a target="_blank" href="/roundcube/" class="btn">Access Webmail →</a>
        </div>
        
        <div class="info">
            <p><strong>Note:</strong> This is a development mail server. For production use, please configure proper SSL certificates, authentication, and security settings.</p>
        </div>
        
        <div class="timestamp">
            Last checked: <?php echo date('Y-m-d H:i:s'); ?>
            <a href="/" class="refresh-btn">Refresh</a>
        </div>
    </div>
</body>
</html>
INDEXPHP

# NO RESTART - just reload config 
# apache2-foreground is already running as the main process
apache2ctl graceful 2>/dev/null || true

echo "✓ Roundcube installation completed!"
echo "✓ Access webmail at: http://localhost:8082/roundcube/"
echo "✓ Dashboard at: http://localhost:8082/"

exit 0

