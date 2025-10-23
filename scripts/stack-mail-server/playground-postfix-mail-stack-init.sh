#!/bin/bash

echo "📧 Installing and configuring Postfix SMTP..."

# Install packages quietly
apt-get update -qq >/dev/null 2>&1
apt-get install -y -qq --no-install-recommends \
    postfix \
    postfix-mysql \
    mailutils \
    mysql-client \
    curl \
    openssl \
    ca-certificates >/dev/null 2>&1

# Configure MySQL client to disable SSL
mkdir -p /etc/mysql/conf.d
cat > /etc/mysql/conf.d/client.cnf << 'CLIENTCNF'
[client]
ssl=0
CLIENTCNF

# Wait for MySQL
echo "→ Waiting for MySQL..."
for i in {1..15}; do
    if mysql -h mysql-mail-stack -u mailuser -pmail_secure_pass mailserver -e "SELECT 1;" 2>/dev/null; then
        echo "✓ MySQL connected"
        break
    fi
    sleep 2
done

# Create mail user and directories
useradd -m -d /var/mail/virtual -s /usr/sbin/nologin -u 5000 vmail 2>/dev/null || true
mkdir -p /var/mail/virtual/{admin,user1}
mkdir -p /var/spool/postfix/private
chown -R vmail:vmail /var/mail/virtual
chmod -R 770 /var/mail/virtual

# Create SSL certificates
mkdir -p /etc/postfix/certs
if [ ! -f /etc/postfix/certs/cert.pem ]; then
    echo "→ Generating SSL certificates..."
    openssl req -new -x509 -days 3650 -nodes \
        -out /etc/postfix/certs/cert.pem \
        -keyout /etc/postfix/certs/key.pem \
        -subj "/C=IT/ST=Tuscany/L=Prato/O=MailStack/CN=mail.example.com" 2>/dev/null
    chmod 600 /etc/postfix/certs/key.pem
    chmod 644 /etc/postfix/certs/cert.pem
fi

# Configure Postfix main.cf
echo "→ Configuring Postfix..."
cat > /etc/postfix/main.cf << 'EOF'
# Basic configuration
myhostname = mail.example.com
mydomain = example.com
myorigin = $mydomain
inet_interfaces = all
inet_protocols = ipv4
mydestination = localhost.$mydomain, localhost

# Network settings
mynetworks = 127.0.0.0/8 [::1]/128 172.16.0.0/12 192.168.0.0/16 10.0.0.0/8

# Virtual mailbox settings with MySQL
virtual_mailbox_domains = mysql:/etc/postfix/mysql-virtual-domains.cf
virtual_mailbox_maps = mysql:/etc/postfix/mysql-virtual-mailboxes.cf
virtual_alias_maps = mysql:/etc/postfix/mysql-virtual-aliases.cf
virtual_mailbox_base = /var/mail/virtual
virtual_uid_maps = static:5000
virtual_gid_maps = static:5000

# SASL Authentication
smtpd_sasl_type = dovecot
smtpd_sasl_path = private/auth
smtpd_sasl_auth_enable = yes
smtpd_sasl_security_options = noanonymous
smtpd_sasl_local_domain = $myhostname

# TLS settings
smtpd_use_tls = yes
smtpd_tls_cert_file = /etc/postfix/certs/cert.pem
smtpd_tls_key_file = /etc/postfix/certs/key.pem
smtpd_tls_security_level = may
smtp_tls_security_level = may

# Restrictions
smtpd_recipient_restrictions = 
    permit_mynetworks,
    permit_sasl_authenticated,
    reject_unauth_destination,
    reject_invalid_hostname,
    reject_unknown_recipient_domain

smtpd_sender_restrictions = 
    permit_mynetworks,
    permit_sasl_authenticated,
    reject_unknown_sender_domain

# Message size and queue settings
message_size_limit = 52428800
mailbox_size_limit = 0
maximal_queue_lifetime = 5d
bounce_queue_lifetime = 1d

# Logging
maillog_file = /var/log/postfix.log

# Local delivery to Dovecot
virtual_transport = lmtp:unix:private/dovecot-lmtp

# Additional settings
smtpd_banner = $myhostname ESMTP
disable_vrfy_command = yes
strict_rfc821_envelopes = yes
EOF

# Create MySQL configuration files
echo "→ Creating MySQL maps..."

cat > /etc/postfix/mysql-virtual-domains.cf << 'EOF'
hosts = mysql-mail-stack
dbname = mailserver
user = mailuser
password = mail_secure_pass
query = SELECT 1 FROM virtual_domains WHERE name='%s'
EOF

cat > /etc/postfix/mysql-virtual-mailboxes.cf << 'EOF'
hosts = mysql-mail-stack
dbname = mailserver
user = mailuser
password = mail_secure_pass
query = SELECT CONCAT(email, '/') FROM virtual_users WHERE email='%s'
EOF

cat > /etc/postfix/mysql-virtual-aliases.cf << 'EOF'
hosts = mysql-mail-stack
dbname = mailserver
user = mailuser
password = mail_secure_pass
query = SELECT destination FROM virtual_aliases WHERE source='%s'
EOF

# Set permissions
chmod 640 /etc/postfix/mysql-*.cf
chown root:postfix /etc/postfix/mysql-*.cf

# Configure master.cf for submission and smtps
cat > /etc/postfix/master.cf << 'EOF'
# ==========================================================================
# service type  private unpriv  chroot  wakeup  maxproc command + args
# ==========================================================================
smtp      inet  n       -       y       -       -       smtpd
pickup    unix  n       -       y       60      1       pickup
cleanup   unix  n       -       y       -       0       cleanup
qmgr      unix  n       -       n       300     1       qmgr
tlsmgr    unix  -       -       y       1000?   1       tlsmgr
rewrite   unix  -       -       y       -       -       trivial-rewrite
bounce    unix  -       -       y       -       0       bounce
defer     unix  -       -       y       -       0       bounce
trace     unix  -       -       y       -       0       bounce
verify    unix  -       -       y       -       1       verify
flush     unix  n       -       y       1000?   0       flush
proxymap  unix  -       -       n       -       -       proxymap
proxywrite unix -       -       n       -       1       proxymap
smtp      unix  -       -       y       -       -       smtp
relay     unix  -       -       y       -       -       smtp
showq     unix  n       -       y       -       -       showq
error     unix  -       -       y       -       -       error
retry     unix  -       -       y       -       -       error
discard   unix  -       -       y       -       -       discard
local     unix  -       n       n       -       -       local
virtual   unix  -       n       n       -       -       virtual
lmtp      unix  -       -       y       -       -       lmtp
anvil     unix  -       -       y       -       1       anvil
scache    unix  -       -       y       -       1       scache

# Submission port 587
submission inet n       -       y       -       -       smtpd
  -o syslog_name=postfix/submission
  -o smtpd_tls_security_level=encrypt
  -o smtpd_sasl_auth_enable=yes
  -o smtpd_client_restrictions=permit_sasl_authenticated,reject
  -o smtpd_reject_unlisted_recipient=no
  -o smtpd_recipient_restrictions=permit_sasl_authenticated,reject
  -o milter_macro_daemon_name=ORIGINATING

# SMTPS port 465
smtps     inet  n       -       y       -       -       smtpd
  -o syslog_name=postfix/smtps
  -o smtpd_tls_wrappermode=yes
  -o smtpd_sasl_auth_enable=yes
  -o smtpd_client_restrictions=permit_sasl_authenticated,reject
  -o smtpd_reject_unlisted_recipient=no
  -o milter_macro_daemon_name=ORIGINATING
EOF

# Create aliases
echo "→ Setting up aliases..."
cat > /etc/aliases << 'EOF'
postmaster: root
webmaster: root
root: admin@localhost
EOF
newaliases 2>/dev/null || true

# Create mailbox structure for users
mkdir -p /var/mail/virtual/admin@localhost/{new,cur,tmp}
mkdir -p /var/mail/virtual/user1@localhost/{new,cur,tmp}
mkdir -p /var/mail/virtual/admin@example.com/{new,cur,tmp}
chown -R vmail:vmail /var/mail/virtual
chmod -R 700 /var/mail/virtual/*

# Start Postfix
echo "→ Starting Postfix..."

postfix upgrade-configuration

service postfix restart

#postfix stop 2>/dev/null || true
#postfix start 2>/dev/null || true

# Keep container running and monitor Postfix
echo "✓ Postfix SMTP server configured and running"
echo "  - SMTP: Port 25"
echo "  - Submission: Port 587 (STARTTLS)"
echo "  - SMTPS: Port 465 (SSL/TLS)"
echo ""
echo "Monitoring Postfix (tail -f /var/log/mail.log)..."

# Keep the container alive by tailing the log
touch /var/log/mail.log



#tail -f /var/log/mail.log