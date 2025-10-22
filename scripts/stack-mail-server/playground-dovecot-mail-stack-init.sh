#!/bin/bash
set -e
echo "Installing and configuring Dovecot IMAP/POP3..."
apt-get update -qq
apt-get install -y -qq dovecot-core dovecot-imapd dovecot-pop3d dovecot-mysql mysql-client ssl-cert 2>/dev/null

useradd -m -d /var/mail/virtual -s /usr/sbin/nologin -u 5000 vmail 2>/dev/null || true
useradd -r -s /usr/sbin/nologin -u 10000 postfix 2>/dev/null || true

mkdir -p /var/spool/postfix/private
touch /var/spool/postfix/private/auth
chown postfix:postfix /var/spool/postfix/private/auth

mkdir -p /etc/dovecot/conf.d
cat > /etc/dovecot/dovecot.conf << 'DOVECOTEOF'
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
DOVECOTEOF

cat > /etc/dovecot/dovecot-sql.conf.ext << 'SQLEOF'
driver = mysql
connect = host=mysql-mail-stack dbname=mailserver user=mailuser password=mail_secure_pass
default_pass_scheme = SHA256
password_query = SELECT email as user, password FROM users WHERE email = '%u@%d' AND enabled = TRUE
user_query = SELECT 5000 as uid, 5000 as gid, '/var/mail/virtual/%d/%n' as home FROM users WHERE email = '%u@%d' AND enabled = TRUE
SQLEOF
chmod 600 /etc/dovecot/dovecot-sql.conf.ext

mkdir -p /etc/dovecot/certs
openssl req -new -x509 -days 3650 -nodes \
-out /etc/dovecot/certs/cert.pem \
-keyout /etc/dovecot/certs/key.pem \
-subj "/C=IT/ST=Tuscany/L=Prato/O=Mail/CN=mail.example.com" 2>/dev/null
chmod 600 /etc/dovecot/certs/key.pem

mkdir -p /var/mail/virtual/localhost/admin /var/mail/virtual/localhost/user1
mkdir -p /var/mail/virtual/example.com/admin
chown -R vmail:vmail /var/mail/virtual
chmod -R 770 /var/mail/virtual

service dovecot start
sleep 2
