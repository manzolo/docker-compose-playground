#!/bin/bash
set -e

echo "📬 Installing Postfix + Dovecot (unified mail server)..."

# ===== Install =====
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
    postfix postfix-mysql dovecot-core dovecot-imapd dovecot-pop3d dovecot-lmtpd dovecot-mysql \
    mysql-client libsasl2-modules >/dev/null

# ===== Common mail setup =====
MAIL_DIR=/var/mail/virtual
id -u vmail >/dev/null 2>&1 || useradd -m -d "$MAIL_DIR" -s /usr/sbin/nologin -u 5000 vmail
mkdir -p "$MAIL_DIR" && chown -R vmail:vmail "$MAIL_DIR" && chmod -R 770 "$MAIL_DIR"

# ===== Postfix configuration =====
echo "→ Configuring Postfix..."

postconf -e "myhostname = ${MAIL_HOSTNAME:-mail.local}"
postconf -e "mydestination = localhost"
postconf -e "virtual_mailbox_domains = mysql:/etc/postfix/mysql-virtual-mailbox-domains.cf"
postconf -e "virtual_mailbox_maps = mysql:/etc/postfix/mysql-virtual-mailbox-maps.cf"
postconf -e "virtual_alias_maps = mysql:/etc/postfix/mysql-virtual-alias-maps.cf"
postconf -e "virtual_transport = lmtp:unix:private/dovecot-lmtp"
postconf -e "smtpd_sasl_type = dovecot"
postconf -e "smtpd_sasl_path = private/auth"
postconf -e "smtpd_sasl_auth_enable = yes"
postconf -e "smtpd_recipient_restrictions = permit_sasl_authenticated,permit_mynetworks,reject_unauth_destination"
postconf -e "inet_interfaces = all"
postconf -e "mynetworks = 127.0.0.0/8"
postconf -e "smtpd_banner = \$myhostname ESMTP Mailserver"

# --- MySQL maps ---
cat >/etc/postfix/mysql-virtual-mailbox-domains.cf <<EOF
user = ${MYSQL_USER}
password = ${MYSQL_PASSWORD}
hosts = ${MYSQL_HOST}
dbname = ${MYSQL_DATABASE}
query = SELECT 1 FROM virtual_domains WHERE name='%s'
EOF

cat >/etc/postfix/mysql-virtual-mailbox-maps.cf <<EOF
user = ${MYSQL_USER}
password = ${MYSQL_PASSWORD}
hosts = ${MYSQL_HOST}
dbname = ${MYSQL_DATABASE}
query = SELECT 1 FROM virtual_users WHERE email='%s'
EOF

cat >/etc/postfix/mysql-virtual-alias-maps.cf <<EOF
user = ${MYSQL_USER}
password = ${MYSQL_PASSWORD}
hosts = ${MYSQL_HOST}
dbname = ${MYSQL_DATABASE}
query = SELECT destination FROM virtual_aliases WHERE source='%s'
EOF

# ===== Dovecot configuration =====
echo "→ Configuring Dovecot..."

# Main config
cat >/etc/dovecot/dovecot.conf <<'EOF'
protocols = imap pop3 lmtp
listen = *
auth_mechanisms = plain login
mail_location = maildir:/var/mail/virtual/%u/
mail_uid = vmail
mail_gid = vmail
disable_plaintext_auth = no
ssl = no
!include auth-sql.conf.ext
!include conf.d/*.conf
EOF

# SQL auth
cat >/etc/dovecot/auth-sql.conf.ext <<'EOF'
passdb {
  driver = sql
  args = /etc/dovecot/dovecot-sql.conf.ext
}
userdb {
  driver = static
  args = uid=vmail gid=vmail home=/var/mail/virtual/%u
}
EOF

# MySQL connection
cat >/etc/dovecot/dovecot-sql.conf.ext <<EOF
driver = mysql
connect = host=${MYSQL_HOST} dbname=${MYSQL_DATABASE} user=${MYSQL_USER} password=${MYSQL_PASSWORD}
default_pass_scheme = SHA512-CRYPT
password_query = SELECT email as user, password FROM virtual_users WHERE email='%u';
EOF

# Services (imap, pop3, lmtp, auth)
cat >/etc/dovecot/conf.d/10-master.conf <<'EOF'
service imap-login {
  inet_listener imap {
    port = 143
  }
}

service pop3-login {
  inet_listener pop3 {
    port = 110
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
}
EOF

# Allow plaintext authentication (needed for Roundcube)
sed -i 's/^#disable_plaintext_auth.*/disable_plaintext_auth = no/' /etc/dovecot/conf.d/10-auth.conf

# ===== Startup =====
echo "→ Starting services..."
service dovecot restart || systemctl restart dovecot || true
service postfix restart || systemctl restart postfix || true

sleep 2

pgrep dovecot >/dev/null && echo "✓ Dovecot running" || echo "⚠️  Dovecot not running!"
pgrep master >/dev/null && echo "✓ Postfix running" || echo "⚠️  Postfix not running!"

echo
echo "✅ Mailserver ready"
echo "Test locally with:"
echo "  telnet localhost 25   # SMTP"
echo "  telnet localhost 143  # IMAP"
echo

