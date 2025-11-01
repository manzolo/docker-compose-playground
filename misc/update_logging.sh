#!/bin/bash
# Helper script to update logging imports in Python files
# This script updates files to use the centralized logging configuration

echo "Updating Python files to use centralized logging..."

# Function to update a single file
update_file() {
    local file="$1"
    echo "Processing: $file"

    # Check if file uses old logging pattern
    if grep -q 'logger = logging.getLogger("uvicorn")' "$file"; then
        # Add import at the top after other imports
        if ! grep -q "from src.web.core.logging_config import get_logger" "$file"; then
            # Find the line with "import logging" and add our import after it
            sed -i '/^import logging$/a from src.web.core.logging_config import get_logger' "$file"
        fi

        # Replace logger initialization
        sed -i 's/logger = logging.getLogger("uvicorn")/logger = get_logger(__name__)/' "$file"

        echo "  ✓ Updated: $file"
    else
        echo "  - Skipped: $file (already using correct pattern or no logger)"
    fi
}

# Update API files
for file in src/web/api/*.py; do
    if [ -f "$file" ]; then
        update_file "$file"
    fi
done

# Update core files (except logging_config.py itself)
for file in src/web/core/*.py; do
    if [ -f "$file" ] && [ "$file" != "src/web/core/logging_config.py" ]; then
        update_file "$file"
    fi
done

echo ""
echo "✓ Logging update complete!"
echo ""
echo "Note: Review the changes and test before committing."
