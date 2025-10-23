#!/bin/bash

echo "📬 Installing and configuring Dovecot IMAP/POP3..."

# Install packages quietly
apt-get update -qq >/dev/null 2>&1
apt-get install -y -qq --no-install-recommends \
    dovecot-imapd \
    dovecot-pop3d \
    dovecot-mysql \
    dovecot-lmtpd \
    mysql-client >/dev/null 2>&1

# Create mail user and directories
useradd -m -d /var/mail/virtual -s /usr/sbin/nologin -u 5000 vmail 2>/dev/null || true
mkdir -p /var/mail/virtual/{admin,user1}
chown -R vmail:vmail /var/mail/virtual
chmod -R 770 /var/mail/virtual

# Wait for MySQL
for i in {1..15}; do
    mysql -h mysql-mail-stack -u mailuser -pmail_secure_pass -e "SELECT 1;" 2>/dev/null && break
    sleep 2
done

# Configure Dovecot main settings
cat > /etc/dovecot/dovecot.conf << 'EOF'
protocols = imap pop3 lmtp
listen = *
mail_location = maildir:/var/mail/virtual/%u/

# Authentication
disable_plaintext_auth = no
auth_mechanisms = plain login

# Mail user settings
mail_uid = vmail
mail_gid = vmail
first_valid_uid = 5000
first_valid_gid = 5000

# Logging
log_path = /var/log/dovecot.log
info_log_path = /var/log/dovecot-info.log

# SSL settings (disabled for development)
ssl = no

# Protocol specific settings
protocol imap {
  mail_plugins = 
}

protocol pop3 {
  mail_plugins =
}

protocol lmtp {
  mail_plugins =
}

# Include auth configuration
!include auth-sql.conf.ext
EOF

# Configure SQL authentication
cat > /etc/dovecot/auth-sql.conf.ext << 'EOF'
passdb {
  driver = sql
  args = /etc/dovecot/dovecot-sql.conf.ext
}

userdb {
  driver = static
  args = uid=vmail gid=vmail home=/var/mail/virtual/%u
}
EOF

# Configure SQL connection
cat > /etc/dovecot/dovecot-sql.conf.ext << 'EOF'
driver = mysql
connect = host=mysql-mail-stack dbname=mailserver user=mailuser password=mail_secure_pass

# Password query (using virtual_users table)
password_query = \
  SELECT email as user, password \
  FROM virtual_users WHERE email = '%u'

# User query
user_query = \
  SELECT 'vmail' as uid, 'vmail' as gid, \
  '/var/mail/virtual/%u' as home \
  FROM virtual_users WHERE email = '%u'

# Iterate query (for doveadm)
iterate_query = SELECT email as user FROM virtual_users
EOF

# Set permissions
chmod 600 /etc/dovecot/dovecot-sql.conf.ext
chown dovecot:dovecot /etc/dovecot/dovecot-sql.conf.ext

# Create service configuration
cat > /etc/dovecot/conf.d/10-master.conf << 'EOF'
service imap-login {
  inet_listener imap {
    port = 143
  }
  inet_listener imaps {
    port = 993
    ssl = no
  }
}

service pop3-login {
  inet_listener pop3 {
    port = 110
  }
  inet_listener pop3s {
    port = 995
    ssl = no
  }
}

service lmtp {
  unix_listener /var/spool/postfix/private/dovecot-lmtp {
    mode = 0600
    user = postfix
    group = postfix
  }
}

service auth {
  unix_listener /var/spool/postfix/private/auth {
    mode = 0660
    user = postfix
    group = postfix
  }
  
  unix_listener auth-userdb {
    mode = 0600
    user = vmail
  }
}

service auth-worker {
  user = vmail
}

service dict {
  unix_listener dict {
    mode = 0600
    user = vmail
  }
}
EOF

# Create mailbox structure for users
mkdir -p /var/mail/virtual/admin@localhost/{cur,new,tmp}
mkdir -p /var/mail/virtual/user1@localhost/{cur,new,tmp}
mkdir -p /var/mail/virtual/admin@example.com/{cur,new,tmp}
chown -R vmail:vmail /var/mail/virtual
chmod -R 700 /var/mail/virtual/*

# Start Dovecot
echo "→ Starting Dovecot..."
service dovecot stop 2>/dev/null || true
dovecot -F &

sleep 3

# Verify service
if ps aux | grep -v grep | grep -q dovecot; then
    echo "✓ Dovecot IMAP/POP3 server configured and running"
    echo "  - IMAP: Port 143"
    echo "  - IMAPS: Port 993 (disabled in dev)"
    echo "  - POP3: Port 110"
    echo "  - POP3S: Port 995 (disabled in dev)"
    echo ""
    echo "Test with: telnet localhost 143"
else
    echo "⚠️ Dovecot might not be running properly"
fi

# Keep container alive and show logs
echo "Monitoring Dovecot..."
#tail -f /var/log/dovecot.log /var/log/dovecot-info.log 2>/dev/null || \
#while true; do sleep 3600; done

exit 0