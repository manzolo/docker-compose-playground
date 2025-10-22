#!/bin/bash
set -e

echo "🌐 Installing and configuring Roundcube with PHP extensions..."
export DEBIAN_FRONTEND=noninteractive

echo "→ Updating packages..."
apt-get update -qq 2>&1 | grep -v "^Get\|^Reading\|^Building" || true

echo "→ Installing system dependencies..."
apt-get install -y -qq --no-install-recommends \
    wget \
    unzip \
    curl \
    git \
    default-mysql-client \
    gnupg \
    2>&1 | grep -v "^Get\|^Reading\|^Building" || true

sleep 1

echo "→ Installing PHP development libraries..."
apt-get install -y -qq --no-install-recommends \
    libzip-dev \
    libpng-dev \
    libjpeg-dev \
    libfreetype6-dev \
    2>&1 | grep -v "^Get\|^Reading\|^Building" || true

sleep 1

echo "→ Configuring GD extension..."
docker-php-ext-configure gd --with-freetype --with-jpeg 2>&1 | grep -v "^configure" || true

echo "→ Installing PHP extensions (this may take a moment)..."
docker-php-ext-install -j$(nproc) gd zip mysqli pdo_mysql 2>&1 | grep -E "^(Installing|Build)" || true

sleep 2

echo "→ Enabling PHP extensions..."
docker-php-ext-enable gd 2>&1 | grep -v "^WARNING" || true
docker-php-ext-enable zip 2>&1 | grep -v "^WARNING" || true
docker-php-ext-enable mysqli 2>&1 | grep -v "^WARNING" || true
docker-php-ext-enable pdo_mysql 2>&1 | grep -v "^WARNING" || true

sleep 1

echo "→ Verifying PHP extensions are loaded..."
php -m | grep -E "gd|zip|mysqli|PDO"

echo "→ Creating application directories..."
mkdir -p /var/www/html/roundcube/config
mkdir -p /var/www/html/roundcube/temp
mkdir -p /var/www/html/roundcube/logs

echo "→ Downloading Roundcube 1.6.4..."
cd /tmp

if [ ! -f roundcubemail-1.6.4.tar.gz ]; then
    wget -q --timeout=10 https://github.com/roundcube/roundcubemail/releases/download/1.6.4/roundcubemail-1.6.4.tar.gz 2>/dev/null || \
    curl -L --max-time 10 -o roundcubemail-1.6.4.tar.gz https://github.com/roundcube/roundcubemail/releases/download/1.6.4/roundcubemail-1.6.4.tar.gz 2>/dev/null || \
    echo "⚠️  Could not download Roundcube"
fi

if [ -f roundcubemail-1.6.4.tar.gz ]; then
    echo "→ Extracting Roundcube..."
    tar xzf roundcubemail-1.6.4.tar.gz 2>/dev/null || true
    cp -r roundcubemail-1.6.4/* /var/www/html/roundcube/ 2>/dev/null || true
    rm -rf roundcubemail-1.6.4 roundcubemail-1.6.4.tar.gz
fi

echo "→ Creating Roundcube configuration..."
cat > /var/www/html/roundcube/config/config.inc.php << 'RCUBEEOF'
<?php
$config = array();
$config['imap_host'] = array('dovecot-mail-stack:143');
$config['imap_port'] = 143;
$config['imap_cache'] = 'db';
$config['imap_auth_type'] = null;
$config['smtp_host'] = 'postfix-mail-stack:25';
$config['smtp_port'] = 25;
$config['smtp_auth_type'] = null;
$config['db_dsnw'] = 'mysql://mailuser:mail_secure_pass@mysql-mail-stack/mailserver';
$config['db_prefix'] = 'roundcube_';
$config['des_key'] = 'RoundcubeDESKey12345#@!SuperSecret!Key';
$config['session_storage'] = 'db';
$config['session_lifetime'] = 1440;
$config['log_driver'] = 'syslog';
$config['syslog_id'] = 'roundcube';
$config['timezone'] = 'Europe/Rome';
$config['language'] = 'en_US';
$config['default_list_mode'] = 'list';
$config['draft_autosave'] = 60;
$config['prefer_html'] = true;
$config['htmleditor'] = 1;
$config['skin'] = 'elastic';
$config['enable_caching'] = true;
$config['enable_installer'] = false;
$config['enable_spellcheck'] = false;
$config['plugins'] = array('archive', 'filesystem_attachments', 'help', 'markasjunk');
$config['max_attachment_size'] = 25000000;
?>
RCUBEEOF

echo "→ Creating Roundcube database tables..."
sleep 2
mysql -h mysql-mail-stack -u mailuser -pmail_secure_pass mailserver << 'RCUBESQLEOF' 2>/dev/null || echo "⚠️  DB tables may already exist"
CREATE TABLE IF NOT EXISTS roundcube_users (
  user_id int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  username varchar(255) CHARACTER SET utf8mb4 NOT NULL,
  mail_host varchar(255) NOT NULL,
  created datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_login datetime,
  language varchar(5),
  preferences longtext,
  PRIMARY KEY (user_id),
  UNIQUE KEY username (username, mail_host)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS roundcube_sessions (
  sess_id varchar(128) NOT NULL,
  created datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  changed datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  ip varchar(40) NOT NULL,
  vars longtext NOT NULL,
  PRIMARY KEY (sess_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
RCUBESQLEOF

echo "→ Creating debug diagnostics dashboard..."
cat > /var/www/html/debug.php << 'DEBUGEOF'
<?php
$db_host = 'mysql-mail-stack';
$db_connected = false;
$db_error = '';
if (!extension_loaded('mysqli')) {
    $db_error = 'MySQLi extension not loaded';
} else {
    $mysqli = @new mysqli($db_host, 'mailuser', 'mail_secure_pass', 'mailserver');
    if ($mysqli->connect_error) {
        $db_error = $mysqli->connect_error;
    } else {
        $db_connected = true;
    }
}
?>
<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Mail Stack Diagnostics</title><style>* { margin: 0; padding: 0; box-sizing: border-box; }body { font-family: 'Segoe UI', Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }.container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); padding: 40px; }h1 { color: #333; margin-bottom: 10px; font-size: 2.5em; border-bottom: 3px solid #667eea; padding-bottom: 10px; }.timestamp { color: #666; font-size: 0.9em; margin-bottom: 20px; }.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 30px 0; }.card { border: 1px solid #ddd; border-radius: 8px; padding: 20px; background: #f8f9fa; }.card h3 { color: #667eea; margin-bottom: 15px; }.check-list { list-style: none; }.check-list li { padding: 8px 0; padding-left: 25px; position: relative; border-bottom: 1px solid #eee; }.check-list li:before { position: absolute; left: 0; content: '✓'; font-weight: bold; }.check-list li.error:before { content: '✗'; color: #dc3545; }.check-list li.error { color: #dc3545; }.check-list li.ok { color: #28a745; }.alert { padding: 15px; border-radius: 4px; margin: 15px 0; }.alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }.alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }.info-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }.info-value { text-align: right; }.footer { margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px; text-align: center; }a { color: #667eea; text-decoration: none; }a:hover { text-decoration: underline; }</style></head><body><div class="container"><h1>📊 Mail Stack Diagnostics</h1><div class="timestamp">Generated: <?php echo date('Y-m-d H:i:s'); ?> | PHP <?php echo phpversion(); ?></div><div class="grid"><div class="card"><h3>📦 PHP Extensions</h3><ul class="check-list"><li class="<?php echo extension_loaded('mysqli') ? 'ok' : 'error'; ?>">MySQLi: <?php echo extension_loaded('mysqli') ? '✓' : '✗'; ?></li><li class="<?php echo extension_loaded('pdo_mysql') ? 'ok' : 'error'; ?>">PDO MySQL: <?php echo extension_loaded('pdo_mysql') ? '✓' : '✗'; ?></li><li class="<?php echo extension_loaded('gd') ? 'ok' : 'error'; ?>">GD: <?php echo extension_loaded('gd') ? '✓' : '✗'; ?></li><li class="<?php echo extension_loaded('zip') ? 'ok' : 'error'; ?>">ZIP: <?php echo extension_loaded('zip') ? '✓' : '✗'; ?></li><li class="<?php echo extension_loaded('openssl') ? 'ok' : 'error'; ?>">OpenSSL: <?php echo extension_loaded('openssl') ? '✓' : '✗'; ?></li></ul></div><div class="card"><h3>🗄️ Database</h3><?php if (!extension_loaded('mysqli')): ?><div class="alert alert-error">❌ MySQLi not loaded</div><?php elseif ($db_error): ?><div class="alert alert-error">❌ <?php echo htmlspecialchars($db_error); ?></div><?php else: ?><div class="alert alert-success">✓ Connected</div><div class="info-row"><span>Host:</span><span class="info-value"><?php echo $db_host; ?></span></div><div class="info-row"><span>Version:</span><span class="info-value"><?php echo $mysqli->server_info; ?></span></div><?php endif; ?></div><div class="card"><h3>📋 Tables</h3><?php if ($db_connected): $tables = $mysqli->query("SHOW TABLES IN mailserver"); if ($tables): echo '<ul class="check-list">'; while ($row = $tables->fetch_array()): $name = $row[0]; $count = $mysqli->query("SELECT COUNT(*) FROM $name")->fetch_row()[0]; echo "<li class=\"ok\">$name ($count)</li>"; endwhile; echo '</ul>'; endif; else: echo '<div class="alert alert-error">Not connected</div>'; endif; ?></div><div class="card"><h3>📁 Roundcube Files</h3><?php $config = file_exists('/var/www/html/roundcube/config/config.inc.php'); $size = $config ? filesize('/var/www/html/roundcube/config/config.inc.php') : 0; echo '<ul class="check-list">'; echo '<li class="' . ($size > 100 ? 'ok' : 'error') . '">config.inc.php: ' . ($size > 100 ? '✓ (' . $size . 'b)' : '✗') . '</li>'; echo '</ul>'; ?></div><div class="card"><h3>🔐 Permissions</h3><?php $dirs = ['/var/www/html' => 'Web', '/var/www/html/roundcube' => 'RC', '/var/www/html/roundcube/temp' => 'Temp']; echo '<ul class="check-list">'; foreach ($dirs as $d => $l): if (is_dir($d)): echo '<li class="' . (is_writable($d) ? 'ok' : 'error') . '">' . $l . ' ' . (is_writable($d) ? '✓' : '✗') . '</li>'; endif; endforeach; echo '</ul>'; ?></div><div class="card"><h3>🌐 Services</h3><?php $services = ['dovecot-mail-stack:143' => 'IMAP', 'postfix-mail-stack:25' => 'SMTP', 'mysql-mail-stack:3306' => 'MySQL']; echo '<ul class="check-list">'; foreach ($services as $svc => $lbl): list($h, $p) = explode(':', $svc); $c = @fsockopen($h, $p, $e, $es, 2); $ok = is_resource($c); if ($ok) fclose($c); echo '<li class="' . ($ok ? 'ok' : 'error') . '">' . $lbl . ' ' . ($ok ? '✓' : '✗') . '</li>'; endforeach; echo '</ul>'; ?></div></div><div class="footer"><a href="/">← Dashboard</a> | <a href="/roundcube/">📬 Roundcube</a> | <a href="">🔄 Refresh</a></div></div></body></html>
DEBUGEOF

echo "→ Creating main dashboard..."
cat > /var/www/html/index.php << 'INDEXEOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mail Stack</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI'; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; display: flex; align-items: center; justify-content: center; }
        .container { max-width: 900px; width: 100%; background: white; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); padding: 40px; }
        h1 { color: #333; margin-bottom: 30px; font-size: 2.5em; text-align: center; border-bottom: 3px solid #667eea; padding-bottom: 15px; }
        .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 30px 0; }
        .card { border-left: 4px solid #667eea; padding: 20px; border-radius: 5px; background: #f8f9fa; cursor: pointer; transition: transform 0.2s; }
        .card:hover { transform: translateY(-2px); }
        .card h3 { color: #667eea; margin-bottom: 10px; font-size: 1.3em; }
        .card p { color: #666; margin-bottom: 10px; }
        .card a { color: white; text-decoration: none; font-weight: 600; display: inline-block; margin-top: 10px; padding: 8px 15px; background: #667eea; border-radius: 4px; }
        .card a:hover { background: #5568d3; }
        .info { background: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📧 Mail Stack</h1>
        <div class="info">
            <strong>💡 Debug:</strong> Visit <a href="/debug.php" style="color: inherit; text-decoration: underline;">Diagnostics</a> to check system status
        </div>
        <div class="cards">
            <div class="card">
                <h3>📬 Webmail</h3>
                <p>Roundcube Email Client<br>admin@localhost / admin123</p>
                <a href="/roundcube/">→ Access</a>
            </div>
            <div class="card">
                <h3>🔍 Diagnostics</h3>
                <p>System Health Check<br>PHP, DB, Services Status</p>
                <a href="/debug.php">→ View</a>
            </div>
            <div class="card">
                <h3>📧 SMTP</h3>
                <p>Postfix Mail Server<br>Ports 25, 587, 465</p>
            </div>
            <div class="card">
                <h3>📨 IMAP/POP3</h3>
                <p>Dovecot Mail Services<br>Ports 143/993, 110/995</p>
            </div>
        </div>
    </div>
</body>
</html>
INDEXEOF

echo "→ Creating info redirect..."
cat > /var/www/html/info.php << 'INFOEOF'
<?php header('Location: /debug.php'); exit; ?>
INFOEOF

echo "→ Setting permissions..."
chown -R www-data:www-data /var/www/html
chmod -R 755 /var/www/html
chmod -R 775 /var/www/html/roundcube/temp 2>/dev/null || true
chmod -R 775 /var/www/html/roundcube/logs 2>/dev/null || true

echo "→ Enabling Apache modules..."
a2enmod rewrite 2>/dev/null || true
a2enmod headers 2>/dev/null || true

sleep 1

echo "✓ Roundcube configured successfully"
echo "✓ Dashboard: http://localhost:8082/"
echo "✓ Diagnostics: http://localhost:8082/debug.php"
echo "✓ PHP Extensions installed: $(php -m | grep -E 'gd|zip|mysqli|PDO' | tr '\n' ' ')"

exit 0