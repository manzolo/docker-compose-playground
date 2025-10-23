#!/bin/bash
set -e

echo "🛡️  Installing SpamAssassin..."

# Fix dpkg issues first
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq 2>&1 | grep -v "^Get\|^Reading\|^Building" || true
apt-get install -y -qq --no-install-recommends apt-utils 2>&1 | grep -v "^Get\|^Reading\|^Building" || true

# Fix any broken dependencies
dpkg --configure -a 2>&1 | grep -v "^Processing\|^Setting up" || true

echo "→ Creating spamd user..."
useradd -m -s /usr/sbin/nologin -u 5001 spamd 2>/dev/null || echo "spamd user already exists"

echo "→ Setting up directories..."
mkdir -p /var/lib/spamassassin/sa-update-keys
mkdir -p /var/run/spamd
chown -R spamd:spamd /var/lib/spamassassin
chmod 700 /var/lib/spamassassin/sa-update-keys

echo "→ Installing SpamAssassin packages..."
apt-get install -y -qq --no-install-recommends \
    spamassassin \
    spamc \
    libmail-dkim-perl \
    pyzor \
    razor \
    mysql-client \
    2>&1 | grep -v "^Get\|^Reading\|^Building\|^Unpacking\|^Setting up" || true

echo "→ Creating SpamAssassin configuration..."
cat > /etc/spamassassin/local.cf << 'SPAMEOF'
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
chown -R spamd:spamd /var/lib/spamassassin

echo "→ Configuring Razor..."
razor-admin -home=/var/lib/spamassassin/.spamassassin -register 2>&1 | grep -v "^razor" || true

echo "→ Starting spamd..."
mkdir -p /var/run/spamd
chown spamd:spamd /var/run/spamd

# Start spamd in background
/usr/sbin/spamd -d -c -x -A 127.0.0.1 -p 783 --pidfile=/var/run/spamd/spamd.pid &

sleep 2

# Verify spamd is running
if pgrep -f "spamd" > /dev/null; then
    echo "✓ SpamAssassin started successfully"
else
    echo "⚠️  Warning: spamd may not have started properly, continuing anyway..."
fi

exit 0