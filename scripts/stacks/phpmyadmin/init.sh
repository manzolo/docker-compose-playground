#!/bin/bash
echo "Configuring phpmyadmin-stack auto-login..."

# Wait for phpmyadmin-stack
sleep 5

# Create auto-login config
docker exec "${CONTAINER_NAME}" sh -c '
cat > /etc/phpmyadmin/config.user.inc.php << "PHP"
<?php
/* Auto-login configuration */
$cfg["Servers"][$i]["auth_type"] = "config";
$cfg["Servers"][$i]["user"] = "root";
$cfg["Servers"][$i]["password"] = "playground";
$cfg["Servers"][$i]["AllowNoPassword"] = true;

/* Disable login cookie expiration warnings */
$cfg["LoginCookieValidity"] = 86400;

/* Set default database */
$cfg["Servers"][$i]["only_db"] = "";
?>
PHP
'

echo "✓ phpmyadmin-stack ready at http://localhost:8088"
echo "✓ Auto-login enabled (root/playground)"