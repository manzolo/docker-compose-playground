#!/bin/bash

echo "🛡️ Installing and configuring SpamAssassin..."

# Install packages
apt-get update -qq >/dev/null 2>&1
apt-get install -y -qq --no-install-recommends \
    spamassassin \
    spamc \
    libmail-spf-perl \
    libmail-dkim-perl \
    pyzor \
    razor \
    mysql-client \
    curl \
    wget >/dev/null 2>&1

# Configure MySQL client to disable SSL
mkdir -p /etc/mysql/conf.d
cat > /etc/mysql/conf.d/client.cnf << 'CLIENTCNF'
[client]
ssl=0
CLIENTCNF

# Create spamd user if not exists
useradd -r -d /var/lib/spamassassin -s /bin/false spamd 2>/dev/null || true

# Create directories
mkdir -p /var/lib/spamassassin/.spamassassin
mkdir -p /var/log/spamassassin
chown -R spamd:spamd /var/lib/spamassassin
chmod -R 755 /var/lib/spamassassin

# Configure SpamAssassin
echo "→ Configuring SpamAssassin..."
cat > /etc/spamassassin/local.cf << 'EOF'
# Basic Configuration
rewrite_header Subject [SPAM]
report_safe 0
required_score 5.0
use_bayes 1
bayes_auto_learn 1
bayes_path /var/lib/spamassassin/.spamassassin/bayes
skip_rbl_checks 0
use_razor2 1
use_pyzor 1

# Network Tests
dns_available yes
dns_server 8.8.8.8
dns_server 8.8.4.4

# Bayes Database Settings
bayes_auto_expire 1
bayes_learn_to_journal 1

# Score adjustments
score URIBL_BLOCKED 0
score RCVD_IN_DNSWL_HI -5
score RCVD_IN_DNSWL_MED -2
score RCVD_IN_DNSWL_LOW -1

# Whitelist and Blacklist
whitelist_from *@localhost
whitelist_from *@example.com

# Headers to add
add_header spam Flag _YESNOCAPS_
add_header spam Score _SCORE_
add_header spam Level _STARS(*)_
add_header spam Status _YESNO_, score=_SCORE_ required=_REQD_ tests=_TESTS_ autolearn=_AUTOLEARN_ version=_VERSION_

# Character sets
ok_locales all
normalize_charset 1

# Performance
dns_timeout 5
rbl_timeout 5
EOF

# Configure spamd defaults
cat > /etc/default/spamassassin << 'EOF'
# SpamAssassin daemon options
ENABLED=1
OPTIONS="--create-prefs --max-children 5 --helper-home-dir --username spamd -H /var/lib/spamassassin -s /var/log/spamassassin/spamd.log --listen-ip=0.0.0.0 --allowed-ips=0.0.0.0/0"
PIDFILE="/var/run/spamd.pid"
CRON=1
EOF

# Initialize Razor
echo "→ Initializing Razor..."
su - spamd -s /bin/bash -c "razor-admin -create" 2>/dev/null || true
su - spamd -s /bin/bash -c "razor-admin -register" 2>/dev/null || true

# Initialize Pyzor
echo "→ Initializing Pyzor..."
su - spamd -s /bin/bash -c "pyzor discover" 2>/dev/null || true

# Update SpamAssassin rules
echo "→ Updating SpamAssassin rules..."
sa-update --nogpg 2>/dev/null || true

# Compile rules for better performance
sa-compile 2>/dev/null || true

# Create a test script
cat > /usr/local/bin/test-spam << 'EOF'
#!/bin/bash
echo "Testing SpamAssassin..."
echo -e "Subject: Test spam mail\nFrom: spammer@spam.com\nTo: user@localhost\n\nThis is a test spam message with viagra casino lottery" | spamc -R
EOF
chmod +x /usr/local/bin/test-spam

# Create systemd override for container
mkdir -p /etc/systemd/system
cat > /etc/systemd/system/spamassassin.service << 'EOF'
[Unit]
Description=SpamAssassin daemon
After=network.target

[Service]
Type=forking
PIDFile=/var/run/spamd.pid
ExecStart=/usr/sbin/spamd --create-prefs --max-children 5 --helper-home-dir --username spamd -H /var/lib/spamassassin -s /var/log/spamassassin/spamd.log --listen-ip=0.0.0.0 --allowed-ips=0.0.0.0/0 --pidfile /var/run/spamd.pid -d
ExecReload=/bin/kill -HUP $MAINPID
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Start SpamAssassin
echo "→ Starting SpamAssassin daemon..."
service spamassassin start

# /usr/sbin/spamd --create-prefs --max-children 5 --helper-home-dir \
#     --username spamd -H /var/lib/spamassassin \
#     -s /var/log/spamassassin/spamd.log \
#     --listen-ip=0.0.0.0 --allowed-ips=0.0.0.0/0 \
#     --pidfile /var/run/spamd.pid -d

sleep 5

# Verify service
if ps aux | grep -v grep | grep -q spamd; then
    echo "✓ SpamAssassin daemon running"
    echo "  - Port: 783"
    echo "  - Threshold: 5.0 points"
    echo "  - Bayes: Enabled with auto-learn"
    echo ""
    echo "Test with: echo 'test' | spamc -R"
else
    echo "⚠️ SpamAssassin might not be running"
fi

#sleep 5
#service spamassassin restart

# Keep container alive by monitoring log
touch /var/log/spamassassin/spamd.log
echo "Monitoring SpamAssassin (tail -f /var/log/spamassassin/spamd.log)..."
#tail -f /var/log/spamassassin/spamd.log