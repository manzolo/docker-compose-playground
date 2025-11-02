set -e
echo "Initializing PHP 8.3 Playground..."
CONTAINER_NAME="$1"

# Crea i file localmente
mkdir -p temp_php_files

cat > temp_php_files/index.php << 'EOF'
<?php
echo "<h1>Hello from PHP 8.3 Playground!</h1>";
echo "<p>PHP Version: " . phpversion() . "</p>";
echo "<p>Server Time: " . date('Y-m-d H:i:s') . "</p>";
?>
<hr>
<h3>Quick PHP Commands:</h3>
<ul>
    <li>php -v</li>
    <li>php -S 0.0.0.0:8000 -t /shared</li>
</ul>
EOF

cat > temp_php_files/api.php << 'EOF'
<?php
header('Content-Type: application/json');
echo json_encode([
    'message' => 'PHP API Endpoint',
    'timestamp' => date('Y-m-d H:i:s'),
    'php_version' => phpversion()
]);
?>
EOF

cat > temp_php_files/form.php << 'EOF'
<?php
if ($_POST) {
    echo "<h3>Form Data Received:</h3>";
    echo "<pre>" . print_r($_POST, true) . "</pre>";
}
?>
<h2>PHP Form Test</h2>
<form method="POST">
    <input type="text" name="name" placeholder="Your Name" required><br><br>
    <textarea name="message" placeholder="Your Message"></textarea><br><br>
    <button type="submit">Submit</button>
</form>
EOF

# Copia i file nel container
CUSTOM_FOLDER="/shared/data/${CONTAINER_NAME#playground-}"
docker exec "${CONTAINER_NAME}" mkdir -p "${CUSTOM_FOLDER}"
docker cp temp_php_files/. "${CONTAINER_NAME}:${CUSTOM_FOLDER}/"

# Pulisci
rm -rf temp_php_files

# Configura il container
docker exec "${CONTAINER_NAME}" bash -c "
    apt-get update -qq >/dev/null 2>&1
    apt-get install -y -qq curl wget nano git >/dev/null 2>&1
    
    chown -R www-data:www-data ${CUSTOM_FOLDER}
    chmod -R 755 ${CUSTOM_FOLDER}
    
    # Avvia server PHP
    php -S 0.0.0.0:8000 -t ${CUSTOM_FOLDER} > /dev/null 2>&1 &
    
    echo '✓ PHP Playground ready'
    echo 'Access at: http://localhost:8098'
    echo 'Files created:'
    echo '  ${CUSTOM_FOLDER}/index.php    - Main page'
    echo '  ${CUSTOM_FOLDER}/api.php      - JSON API'
    echo '  ${CUSTOM_FOLDER}/form.php     - Form handler'
"