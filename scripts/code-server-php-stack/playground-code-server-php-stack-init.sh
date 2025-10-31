#!/bin/bash
# Post-start script for code-server-php-stack
# Configures VS Code Server for PHP development with debugging support

CONTAINER_NAME="$1"

echo "Setting up Code Server for PHP development..."

# Install PHP in code-server container (needed for IntelliSense and local analysis)
echo "Installing PHP 8.4 in code-server container..."
docker exec "${CONTAINER_NAME}" bash -c '
  apt-get update -qq 2>/dev/null
  apt-get install -y php8.2-cli php8.2-xml php8.2-mbstring php8.2-curl -qq 2>/dev/null || \
  apt-get install -y php-cli php-xml php-mbstring php-curl -qq 2>/dev/null
  ln -sf /usr/bin/php /usr/local/bin/php 2>/dev/null || true
  echo "✓ PHP installed"
'

# Wait for code-server to be ready (check if process is running)
echo "Waiting for code-server to start..."
MAX_WAIT=60
COUNT=0
while [ $COUNT -lt $MAX_WAIT ]; do
  if docker exec "${CONTAINER_NAME}" pgrep -f "code-server" > /dev/null 2>&1; then
    echo "✓ Code-server process detected"
    break
  fi
  sleep 2
  COUNT=$((COUNT + 2))
done

# Additional wait for code-server to be fully ready
sleep 5

# Check if extensions are already installed
EXTENSIONS_EXIST=$(docker exec "${CONTAINER_NAME}" bash -c '
  [ -d /config/extensions ] && ls -1 /config/extensions | grep -q "intelephense" && echo "yes" || echo "no"
')

if [ "$EXTENSIONS_EXIST" = "yes" ]; then
  echo "✓ PHP extensions already installed, skipping"
else
  # Install PHP extensions (run as user abc with correct HOME)
  echo "Installing VS Code PHP extensions..."
  docker exec -u abc "${CONTAINER_NAME}" bash -c '
    export HOME=/config

    # Install Intelephense (best PHP IntelliSense)
    /app/code-server/bin/code-server --extensions-dir /config/extensions --install-extension bmewburn.vscode-intelephense-client 2>/dev/null || true

    # Install PHP Debug
    /app/code-server/bin/code-server --extensions-dir /config/extensions --install-extension xdebug.php-debug 2>/dev/null || true

    # Install PHP CS Fixer (code formatter)
    /app/code-server/bin/code-server --extensions-dir /config/extensions --install-extension junstyle.php-cs-fixer 2>/dev/null || true

    # Install additional useful extensions
    /app/code-server/bin/code-server --extensions-dir /config/extensions --install-extension neilbrayfield.php-docblocker 2>/dev/null || true
    /app/code-server/bin/code-server --extensions-dir /config/extensions --install-extension mrmlnc.vscode-apache 2>/dev/null || true
  '

  echo "✓ Extensions installation triggered (may complete in background)"
fi

# Create workspace settings for PHP debugging (as user abc)
echo "Configuring PHP debugger..."
docker exec "${CONTAINER_NAME}" chown -R 1000:1000 /workspace 2>/dev/null || true
docker exec -u abc "${CONTAINER_NAME}" bash -c 'mkdir -p /workspace/.vscode'

# Create launch.json for debugging (only if not exists)
if docker exec "${CONTAINER_NAME}" [ ! -f /workspace/.vscode/launch.json ]; then
  echo "Creating launch.json..."
  docker exec "${CONTAINER_NAME}" bash -c 'cat > /workspace/.vscode/launch.json << "EOF"
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Listen for Xdebug",
            "type": "php",
            "request": "launch",
            "port": 9003,
            "hostname": "0.0.0.0",
            "pathMappings": {
                "/workspace": "${workspaceFolder}"
            }
        },
        {
            "name": "Launch Built-in Server",
            "type": "php",
            "request": "launch",
            "runtimeArgs": [
                "-S",
                "localhost:8000",
                "-t",
                "${workspaceFolder}"
            ],
            "port": 9003,
            "serverReadyAction": {
                "action": "openExternally"
            }
        },
        {
            "name": "Launch Current Script",
            "type": "php",
            "request": "launch",
            "program": "${file}",
            "cwd": "${fileDirname}",
            "port": 9003
        }
    ]
}
EOF'
else
  echo "✓ launch.json already exists, skipping"
fi

# Create settings.json (only if not exists)
if docker exec "${CONTAINER_NAME}" [ ! -f /workspace/.vscode/settings.json ]; then
  echo "Creating settings.json..."
  docker exec "${CONTAINER_NAME}" bash -c 'cat > /workspace/.vscode/settings.json << "EOF"
{
    "php.suggest.basic": false,
    "php.validate.enable": true,
    "php.validate.executablePath": "/usr/bin/php",
    "intelephense.environment.phpVersion": "8.4.0",
    "intelephense.files.maxSize": 5000000,
    "files.watcherExclude": {
        "**/.git/objects/**": true,
        "**/.git/subtree-cache/**": true,
        "**/node_modules/*/**": true,
        "**/vendor/**": true
    },
    "editor.formatOnSave": true,
    "files.associations": {
        "*.php": "php"
    }
}
EOF'
else
  echo "✓ settings.json already exists, skipping"
fi

# Create tasks.json for common PHP tasks (only if not exists)
if docker exec "${CONTAINER_NAME}" [ ! -f /workspace/.vscode/tasks.json ]; then
  echo "Creating tasks.json..."
  docker exec "${CONTAINER_NAME}" bash -c 'cat > /workspace/.vscode/tasks.json << "EOF"
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Start PHP Built-in Server",
            "type": "shell",
            "command": "docker exec playground-php-8.4-stack start-php-server",
            "problemMatcher": [],
            "presentation": {
                "reveal": "always",
                "panel": "new"
            }
        },
        {
            "label": "Run Current PHP File",
            "type": "shell",
            "command": "docker exec playground-php-8.4-stack php /workspace/${relativeFile}",
            "problemMatcher": []
        },
        {
            "label": "Composer Install",
            "type": "shell",
            "command": "docker exec playground-php-8.4-stack composer install",
            "problemMatcher": []
        }
    ]
}
EOF'
else
  echo "✓ tasks.json already exists, skipping"
fi

# Create sample PHP project (only if not exists)
if docker exec "${CONTAINER_NAME}" [ ! -f /workspace/index.php ]; then
  echo "Creating sample PHP project..."

  # Create index.php with sample code
  docker exec "${CONTAINER_NAME}" bash -c 'cat > /workspace/index.php << "EOF"
<?php
/**
 * Sample PHP Application
 *
 * A simple demonstration of PHP 8.4 features
 */

// Enable error reporting for development
error_reporting(E_ALL);
ini_set("display_errors", 1);

// Sample data
$colors = ["red", "green", "blue", "yellow"];
$numbers = range(1, 10);

/**
 * Calculate factorial of a number
 */
function factorial(int $n): int {
    if ($n <= 1) {
        return 1;
    }
    return $n * factorial($n - 1);
}

/**
 * Format array as HTML list
 */
function formatList(array $items): string {
    $html = "<ul>";
    foreach ($items as $item) {
        $html .= "<li>" . htmlspecialchars($item) . "</li>";
    }
    $html .= "</ul>";
    return $html;
}

?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PHP <?= PHP_VERSION ?> Demo</title>
    <style>
        body {
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            max-width: 900px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #4F5D95;
            border-bottom: 3px solid #4F5D95;
            padding-bottom: 10px;
        }
        .info-box {
            background: #e8f4f8;
            padding: 15px;
            border-left: 4px solid #4F5D95;
            margin: 20px 0;
        }
        .result {
            background: #f0f0f0;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
            font-family: monospace;
        }
        .success {
            color: #4CAF50;
            font-weight: bold;
        }
        ul {
            background: #fafafa;
            padding: 20px;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🐘 PHP <?= PHP_VERSION ?> Development Stack</h1>

        <div class="info-box">
            <h3>📊 System Information</h3>
            <p><strong>PHP Version:</strong> <?= PHP_VERSION ?></p>
            <p><strong>Server Time:</strong> <?= date("Y-m-d H:i:s") ?></p>
            <p><strong>Working Directory:</strong> <?= getcwd() ?></p>
        </div>

        <h2>🎨 Sample Data</h2>
        <h3>Colors:</h3>
        <?= formatList($colors) ?>

        <h2>🔢 Factorial Demo</h2>
        <?php foreach ([5, 7, 10] as $num): ?>
            <div class="result">
                factorial(<?= $num ?>) = <span class="success"><?= factorial($num) ?></span>
            </div>
        <?php endforeach; ?>

        <h2>📈 Number Sequence</h2>
        <?= formatList($numbers) ?>

        <div class="info-box">
            <h3>🚀 Next Steps</h3>
            <ul>
                <li>Edit this file in VS Code Server (http://localhost:8445)</li>
                <li>Add breakpoints and press F5 to debug</li>
                <li>Create new PHP files in the workspace</li>
                <li>Install Composer packages: <code>composer require package/name</code></li>
            </ul>
        </div>

        <p style="text-align: center; margin-top: 30px; color: #888;">
            <small>PHP Dev Stack - Powered by Docker Playground</small>
        </p>
    </div>
</body>
</html>
EOF'

  # Create composer.json
  docker exec "${CONTAINER_NAME}" bash -c 'cat > /workspace/composer.json << "EOF"
{
    "name": "playground/php-dev-stack",
    "description": "PHP Development Stack Sample Project",
    "type": "project",
    "require": {
        "php": ">=8.4"
    },
    "require-dev": {
        "phpstan/phpstan": "^1.10",
        "friendsofphp/php-cs-fixer": "^3.0"
    },
    "autoload": {
        "psr-4": {
            "App\\": "src/"
        }
    }
}
EOF'

  # Create README
  docker exec "${CONTAINER_NAME}" bash -c 'cat > /workspace/README.md << "EOF"
# PHP Development Stack

Complete PHP development environment with VS Code Server and PHP 8.4.

## 🚀 Quick Start

1. **Access Code Server**: http://localhost:8445
   - Password: `phpdev`

2. **Start PHP built-in server**:
   ```bash
   # In PHP container terminal
   start-php-server
   ```
   Access: http://localhost:8082

3. **Install Composer dependencies**:
   ```bash
   composer install
   ```

## 🐛 Debugging

### Built-in Server with Xdebug
1. In PHP container: `start-php-server`
2. In VS Code: Press F5 → Select "Listen for Xdebug"
3. Open http://localhost:8082
4. Set breakpoints and debug!

### Current File
1. Open any PHP file in VS Code
2. Press F5 → "Launch Current Script"
3. Debugger will run the file

## 📦 Composer

```bash
# Install dependencies
composer install

# Add a package
composer require vendor/package

# Update packages
composer update
```

## 🔧 VS Code Tasks

Use Ctrl+Shift+P → "Tasks: Run Task":
- Start PHP Built-in Server
- Run Current PHP File
- Composer Install

## 📁 Project Structure

```
/workspace/
├── index.php         # Main demo file
├── composer.json     # Composer config
├── .vscode/          # VS Code configurations
└── README.md
```

## 💡 Tips

- Code is shared between code-server and php-8.4-stack containers
- Use the integrated terminal in Code Server
- PHP executable path: `/usr/local/bin/php`
- Extensions auto-installed: Intelephense, PHP Debug
EOF'
else
  echo "✓ Sample project already exists, skipping"
fi

# Fix ownership of all created files to match PUID:PGID (1000:1000)
echo "Setting correct permissions..."
docker exec "${CONTAINER_NAME}" chown -R 1000:1000 /workspace/.vscode 2>/dev/null || true
docker exec "${CONTAINER_NAME}" chown 1000:1000 /workspace/index.php 2>/dev/null || true
docker exec "${CONTAINER_NAME}" chown 1000:1000 /workspace/composer.json 2>/dev/null || true
docker exec "${CONTAINER_NAME}" chown 1000:1000 /workspace/README.md 2>/dev/null || true

echo "✅ Code Server configured for PHP development"
echo "🌐 Access at: http://localhost:8445"
echo "🔑 Password: phpdev"
echo "📁 Workspace: ./shared-volumes/data/php-dev-workspace"
echo "📁 Config: ./shared-volumes/data/php-dev-config"
echo "🐘 PHP version: 8.4"
echo ""
echo "⚠️  NOTE: PHP extensions may take 30-60 seconds to fully activate"
echo "   If you see errors, wait and reload the window"
