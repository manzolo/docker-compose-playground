#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive
echo "Installing and configuring Roundcube Webmail..."

echo "→ Installing system dependencies..."
apt update -qq
apt install -y -qq wget unzip curl git default-mysql-client gnupg 2> /dev/null || true

echo "→ Installing PHP extensions..."
apt install -y libzip-dev libpng-dev libjpeg-dev libfreetype6-dev && \
          docker-php-ext-configure gd --with-freetype --with-jpeg && \
          docker-php-ext-install -j$(nproc) gd zip mysqli pdo_mysql && \
          docker-php-ext-enable gd zip mysqli pdo_mysql 2> /dev/null || true

echo "→ Creating application directories..."
mkdir -p /var/www/html/roundcube
mkdir -p /var/www/html/roundcube/config
mkdir -p /var/www/html/roundcube/temp
mkdir -p /var/www/html/roundcube/logs

echo "→ Downloading Roundcube 1.6.4..."
cd /tmp
if [ ! -f roundcubemail-1.6.4.tar.gz ]; then
    wget -q https://github.com/roundcube/roundcubemail/releases/download/1.6.4/roundcubemail-1.6.4.tar.gz 2>/dev/null || \
    curl -L -o roundcubemail-1.6.4.tar.gz https://github.com/roundcube/roundcubemail/releases/download/1.6.4/roundcubemail-1.6.4.tar.gz 2>/dev/null
fi

if [ -f roundcubemail-1.6.4.tar.gz ]; then
    echo "→ Extracting Roundcube..."
    tar xzf roundcubemail-1.6.4.tar.gz
    cp -r roundcubemail-1.6.4/* /var/www/html/roundcube/
    rm -rf roundcubemail-1.6.4 roundcubemail-1.6.4.tar.gz
else
    echo "⚠ Failed to download, creating minimal setup..."
    touch /var/www/html/roundcube/index.php
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

echo "→ Initializing Roundcube database..."
if [ -f /var/www/html/roundcube/bin/initdb.sh ]; then
    bash /var/www/html/roundcube/bin/initdb.sh 2>/dev/null || true
fi

echo "→ Creating web redirector..."
cat > /var/www/html/index.php << 'INDEXEOF'
<?php header('Location: /roundcube/'); exit; ?>
INDEXEOF

echo "→ Creating dashboard..."
cat > /var/www/html/info.php << 'INFOEOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mail Stack Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); padding: 40px; }
        h1 { color: #333; margin-bottom: 10px; font-size: 2.5em; }
        .services { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 30px 0; }
        .service { border-left: 4px solid #667eea; padding: 20px; border-radius: 5px; background: #f8f9fa; }
        .service h3 { color: #667eea; margin-bottom: 10px; }
        a { color: #667eea; text-decoration: none; font-weight: 600; }
        code { background: #f0f0f0; padding: 3px 6px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📧 Mail Stack Dashboard</h1>
        <div class="services">
            <div class="service">
                <h3>📬 Webmail (Roundcube)</h3>
                <p><a href="/roundcube/">🔗 Access Roundcube →</a></p>
                <p>📧 admin@localhost / 🔑 admin123</p>
            </div>
            <div class="service">
                <h3>📧 Postfix SMTP</h3>
                <p>Ports: 25, 587, 465</p>
            </div>
            <div class="service">
                <h3>📬 Dovecot IMAP/POP3</h3>
                <p>IMAP: 143/993 | POP3: 110/995</p>
            </div>
            <div class="service">
                <h3>🛡️ SpamAssassin</h3>
                <p>Active - Threshold: 5.0</p>
            </div>
        </div>
    </div>
    <div><?php /*phpinfo() */ ?></div>
</body>
</html>
INFOEOF

echo "→ Setting file permissions..."
chown -R www-data:www-data /var/www/html
chmod -R 755 /var/www/html
chmod -R 775 /var/www/html/roundcube/temp 2>/dev/null || true
chmod -R 775 /var/www/html/roundcube/logs 2>/dev/null || true

echo "→ Enabling Apache modules..."
a2enmod rewrite 2>/dev/null || true
a2enmod headers 2>/dev/null || true
sleep 2

exit 0