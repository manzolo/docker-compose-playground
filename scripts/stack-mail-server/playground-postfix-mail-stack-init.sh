#!/bin/bash

echo "📧 Installing and configuring Postfix SMTP..."

apt-get update -qq 2>&1 | grep -v "^Get\|^Reading\|^Building" || true
apt-get install -y -qq --no-install-recommends postfix mailutils mysql-client curl 2>&1 | grep -v "^Get\|^Reading\|^Building" || true

mkdir -p /etc/postfix

cat > /etc/postfix/main.cf << 'POSTFIXEOF'
myhostname = mail.example.com
mydomain = example.com
myorigin = $mydomain
inet_interfaces = all
inet_protocols = ipv4
mydestination = localhost
mynetworks = 127.0.0.0/8 [::1]/128 172.16.0.0/12 192.168.0.0/16 10.0.0.0/8
virtual_mailbox_domains = localhost, example.com
virtual_mailbox_base = /var/mail/virtual
virtual_mailbox_maps = hash:/etc/postfix/virtual_mailbox
virtual_uid_maps = static:5000
virtual_gid_maps = static:5000
virtual_alias_maps = hash:/etc/postfix/virtual_alias
smtpd_banner = $myhostname ESMTP
smtpd_sasl_auth_enable = yes
smtpd_sasl_security_options = noanonymous
smtpd_recipient_restrictions = permit_mynetworks, permit_sasl_authenticated, reject_unauth_destination
smtpd_use_tls = yes
smtpd_tls_cert_file = /etc/postfix/certs/cert.pem
smtpd_tls_key_file = /etc/postfix/certs/key.pem
smtpd_tls_security_level = may
submission_syslog_name = postfix/submission
submission_smtpd_restrictions = permit_sasl_authenticated,reject_unauth_destination
message_size_limit = 52428800
mailbox_size_limit = 0
maximal_queue_lifetime = 5d
bounce_queue_lifetime = 1d
POSTFIXEOF

cat > /etc/postfix/virtual_mailbox << 'VMAILEOF'
admin@localhost admin/
user1@localhost user1/
admin@example.com admin/
VMAILEOF

postmap /etc/postfix/virtual_mailbox 2>/dev/null || true

cat > /etc/postfix/virtual_alias << 'VALIASEOF'
postmaster@localhost admin@localhost
webmaster@localhost admin@localhost
VALIASEOF

postmap /etc/postfix/virtual_alias 2>/dev/null || true

mkdir -p /var/mail/virtual/admin /var/mail/virtual/user1
useradd -m -d /var/mail/virtual -s /usr/sbin/nologin -u 5000 vmail 2>/dev/null || echo "vmail user exists"
chown -R vmail:vmail /var/mail/virtual
chmod -R 770 /var/mail/virtual

mkdir -p /etc/postfix/certs
if [ ! -f /etc/postfix/certs/cert.pem ]; then
    openssl req -new -x509 -days 3650 -nodes \
    -out /etc/postfix/certs/cert.pem \
    -keyout /etc/postfix/certs/key.pem \
    -subj "/C=IT/ST=Tuscany/L=Prato/O=Mail/CN=mail.example.com" 2>/dev/null
    chmod 600 /etc/postfix/certs/key.pem
fi

if ! grep -q "^submission" /etc/postfix/master.cf; then
    cat >> /etc/postfix/master.cf << 'MASTEREOF'
submission inet n       -       y       -       -       smtpd
465       inet  n       -       y       -       -       smtpd
MASTEREOF
fi

echo "→ Starting Postfix..."
service postfix start 2>&1 | head -5

sleep 2

if ps aux | grep -v grep | grep -q "postfix"; then
    echo "✓ Postfix started successfully"
else
    echo "⚠️ Postfix may not have started"
    postfix start || true
    sleep 2
fi

if ps aux | grep -v grep | grep -q "postfix"; then
    echo "✓ Postfix confirmed running"
else
    echo "❌ Postfix failed to start"
fi

exit 0