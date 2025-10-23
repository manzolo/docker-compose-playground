#!/bin/bash
set -e

echo "📬 Installing and configuring Dovecot IMAP/POP3..." | tee -a /tmp/dovecot-init.log

echo "→ Updating package index..." | tee -a /tmp/dovecot-init.log
apt-get update -qq 2>&1 | grep -v "^Get\|^Reading\|^Building" | tee -a /tmp/dovecot-init.log || true

echo "→ Installing Dovecot and dependencies..." | tee -a /tmp/dovecot-init.log
apt-get install -y -qq --no-install-recommends dovecot-core dovecot-imapd dovecot-pop3d dovecot-mysql mysql-client ssl-cert 2>&1 | grep -v "^Get\|^Reading\|^Building" | tee -a /tmp/dovecot-init.log || { echo "⚠️ Failed to install Dovecot packages" | tee -a /tmp/dovecot-init.log; exit 1; }

echo "→ Creating vmail and postfix users..." | tee -a /tmp/dovecot-init.log
useradd -m -d /var/mail/virtual -s /usr/sbin/nologin -u 5000 vmail 2>/dev/null || echo "vmail user exists" | tee -a /tmp/dovecot-init.log
useradd -r -s /usr/sbin/nologin -u 10000 postfix 2>/dev/null || echo "postfix user exists" | tee -a /tmp/dovecot-init.log

echo "→ Setting up Postfix auth socket..." | tee -a /tmp/dovecot-init.log
mkdir -p /var/spool/postfix/private
touch /var/spool/postfix/private/auth
chown postfix:postfix /var/spool/postfix/private/auth 2>/dev/null | tee -a /tmp/dovecot-init.log || true
chmod 660 /var/spool/postfix/private/auth 2>/dev/null | tee -a /tmp/dovecot-init.log || true

echo "→ Creating Dovecot configuration..." | tee -a /tmp/dovecot-init.log
mkdir -p /etc/dovecot/conf.d

cat > /etc/dovecot/dovecot.conf << 'DOVECOTEOF' 2>&1 | tee -a /tmp/dovecot-init.log
protocols = imap pop3
listen = *, [::]
mail_location = maildir:/var/mail/virtual/%d/%n
mail_privileged_group = vmail

passdb {
    driver = sql
    args = /etc/dovecot/dovecot-sql.conf.ext
}

userdb {
    driver = static
    args = uid=vmail gid=vmail home=/var/mail/virtual/%d/%n
}

service imap-login {
    inet_listener imap {
        port = 143
    }
    inet_listener imaps {
        port = 993
        ssl = yes
    }
}

service pop3-login {
    inet_listener pop3 {
        port = 110
    }
    inet_listener pop3s {
        port = 995
        ssl = yes
    }
}

ssl = yes
ssl_cert = </etc/dovecot/certs/cert.pem
ssl_key = </etc/dovecot/certs/key.pem
ssl_prefer_server_ciphers = yes
disable_plaintext_auth = no

service auth {
    unix_listener /var/spool/postfix/private/auth {
        mode = 0666
        user = postfix
        group = postfix
    }
}

log_path = /var/log/dovecot.log
info_log_path = /var/log/dovecot-info.log
debug_log_path = /var/log/dovecot-debug.log
auth_verbose = yes
auth_debug = yes
DOVECOTEOF

cat > /etc/dovecot/dovecot-sql.conf.ext << 'SQLEOF' 2>&1 | tee -a /tmp/dovecot-init.log
driver = mysql
connect = host=mysql-mail-stack dbname=mailserver user=mailuser password=mail_secure_pass
default_pass_scheme = SHA256-CRYPT
password_query = SELECT email AS user, password FROM virtual_users WHERE email = '%u'
user_query = SELECT 5000 AS uid, 5000 AS gid, '/var/mail/virtual/%d/%n' AS home FROM virtual_users WHERE email = '%u'
SQLEOF

chmod 600 /etc/dovecot/dovecot-sql.conf.ext 2>&1 | tee -a /tmp/dovecot-init.log

echo "→ Generating SSL certificates..." | tee -a /tmp/dovecot-init.log
mkdir -p /etc/dovecot/certs
if [ ! -f /etc/dovecot/certs/cert.pem ]; then
    openssl req -new -x509 -days 3650 -nodes \
    -out /etc/dovecot/certs/cert.pem \
    -keyout /etc/dovecot/certs/key.pem \
    -subj "/C=IT/ST=Tuscany/L=Prato/O=Mail/CN=mail.example.com" 2>/dev/null | tee -a /tmp/dovecot-init.log
    chmod 600 /etc/dovecot/certs/key.pem 2>&1 | tee -a /tmp/dovecot-init.log
fi

echo "→ Creating mail directories..." | tee -a /tmp/dovecot-init.log
mkdir -p /var/mail/virtual/localhost/admin /var/mail/virtual/localhost/user1 /var/mail/virtual/example.com/admin
chown -R vmail:vmail /var/mail/virtual 2>&1 | tee -a /tmp/dovecot-init.log
chmod -R 770 /var/mail/virtual 2>&1 | tee -a /tmp/dovecot-init.log

echo "→ Waiting for MySQL service..." | tee -a /tmp/dovecot-init.log
COUNT=0
MAX_WAIT=30
while [ $COUNT -lt $MAX_WAIT ]; do
    if mysqladmin ping -h mysql-mail-stack -u mailuser -pmail_secure_pass --silent 2>/dev/null; then
        echo "✓ MySQL is ready!" | tee -a /tmp/dovecot-init.log
        break
    fi
    echo "→ MySQL not ready, retrying ($COUNT/$MAX_WAIT)..." | tee -a /tmp/dovecot-init.log
    sleep 1
    COUNT=$((COUNT + 1))
done
if ! mysqladmin ping -h mysql-mail-stack -u mailuser -pmail_secure_pass --silent 2>/dev/null; then
    echo "⚠️ MySQL service not available" | tee -a /tmp/dovecot-init.log
    exit 1
fi

echo "→ Starting Dovecot..." | tee -a /tmp/dovecot-init.log
if ps aux | grep -v grep | grep -q "[d]ovecot"; then
    echo "→ Dovecot already running, reloading configuration..." | tee -a /tmp/dovecot-init.log
    doveadm reload 2>&1 | tee -a /tmp/dovecot-init.log || { echo "⚠️ Failed to reload Dovecot" | tee -a /tmp/dovecot-init.log; exit 1; }
else
    echo "→ Starting Dovecot in foreground..." | tee -a /tmp/dovecot-init.log
    exec /usr/sbin/dovecot -F 2>&1 | tee -a /tmp/dovecot-init.log || { echo "⚠️ Failed to start Dovecot" | tee -a /tmp/dovecot-init.log; exit 1; }
fi

echo "✓ Dovecot configured successfully" | tee -a /tmp/dovecot-init.log

service dovecot start

exit 0