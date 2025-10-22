#!/bin/bash

set -e
echo "Installing and configuring SpamAssassin..."

# Crea l'utente spamd prima di qualsiasi operazione
echo "→ Creating spamd user..."
useradd -m -s /usr/sbin/nologin -u 5001 spamd || { echo "useradd failed: $?"; exit 1; }

# Crea la directory per sa-update-keys e imposta i permessi
echo "→ Setting up directories and permissions..."
mkdir -p /var/lib/spamassassin/sa-update-keys
chown -R spamd:spamd /var/lib/spamassassin || { echo "chown /var/lib/spamassassin failed: $?"; exit 1; }
chmod 700 /var/lib/spamassassin/sa-update-keys || { echo "chmod sa-update-keys failed: $?"; exit 1; }

echo "→ Installing dependencies..."
apt-get update -qq || { echo "apt-get update failed: $?"; exit 1; }
apt-get install -y -qq spamassassin spamc libmail-dkim-perl pyzor razor mysql-client || { echo "apt-get install failed: $?"; exit 1; }

echo "→ Creating SpamAssassin configuration..."
cat > /etc/spamassassin/local.cf << SPAMEOF
required_score 5.0
use_bayes 1
use_bayes_rules 1
bayes_auto_learn 1
bayes_auto_learn_threshold_spam 12
bayes_auto_learn_threshold_ham 0
use_awl 1
use_auto_whitelist 1
skip_rbl_checks 0
rbl_timeout 15
use_dcc 1
use_pyzor 1
trusted_networks 127.0.0.0/8 172.16.0.0/12 192.168.0.0/16
SPAMEOF

echo "→ Setting up additional directories..."
mkdir -p /var/lib/spamassassin/.spamassassin
chown -R spamd:spamd /var/lib/spamassassin || { echo "chown /var/lib/spamassassin failed: $?"; exit 1; }

echo "→ Configuring Pyzor and Razor..."
pyzor --homedir /var/lib/spamassassin/.spamassassin discover || { echo "pyzor discover failed: $?"; exit 1; }
razor-admin -home=/var/lib/spamassassin/.spamassassin -register || { echo "razor-admin register failed: $?"; exit 1; }

echo "→ Setting up spamd runtime directory..."
mkdir -p /var/run/spamd
chown spamd:spamd /var/run/spamd || { echo "chown /var/run/spamd failed: $?"; exit 1; }

echo "→ Starting spamd..."
/usr/sbin/spamd -d -c -x -A 127.0.0.1 -p 783 --pidfile=/var/run/spamd/spamd.pid &
sleep 2

if ! pgrep -f "spamd" > /dev/null; then
    echo "Failed to start spamd"
    exit 1
fi

echo "spamd started successfully"
exit 0