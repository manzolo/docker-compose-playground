#!/bin/bash
CONTAINER_NAME="$1"
echo "🐬 Initializing MySQL 8.0 for $CONTAINER_NAME..."

# Wait for MySQL to be ready with more thorough check
echo "Waiting for MySQL to be ready..."
MAX_WAIT=60
COUNTER=0

while [ $COUNTER -lt $MAX_WAIT ]; do
# Check both ping AND actual query capability
if docker exec "$CONTAINER_NAME" mysqladmin ping -u root -pplayground --silent 2>/dev/null && \
    docker exec "$CONTAINER_NAME" mysql -u root -pplayground -e "SELECT 1;" >/dev/null 2>&1; then
    echo "✓ MySQL is fully ready!"
    break
fi
COUNTER=$((COUNTER + 1))
echo "Waiting... ($COUNTER/$MAX_WAIT)"
sleep 2
done

if [ $COUNTER -ge $MAX_WAIT ]; then
echo "⚠ MySQL did not become ready in time"
exit 1
fi

# Create test table - one statement at a time
echo "Creating test table..."

# Create table
docker exec "$CONTAINER_NAME" mysql -u playground -pplayground playground \
-e "CREATE TABLE IF NOT EXISTS playground_info (
        id INT AUTO_INCREMENT PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        message TEXT,
        version VARCHAR(50)
    );" 2>/dev/null

TABLE_CREATED=$?

if [ $TABLE_CREATED -eq 0 ]; then
echo "✓ Table created successfully"

# Insert data
docker exec "$CONTAINER_NAME" mysql -u playground -pplayground playground \
    -e "INSERT INTO playground_info (message, version) 
        VALUES ('MySQL initialized by playground manager', '8.0');" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ Test data inserted"
    
    # Verify
    ROW_COUNT=$(docker exec "$CONTAINER_NAME" mysql -u playground -pplayground playground \
    -sN -e "SELECT COUNT(*) FROM playground_info;" 2>/dev/null)
    
    if [ "$ROW_COUNT" = "1" ]; then
    echo "✓ MySQL 8.0 fully initialized with test table and data"
    else
    echo "✓ MySQL 8.0 initialized (verification: $ROW_COUNT rows)"
    fi
else
    echo "⚠ Table created but data insertion failed"
fi
else
echo "⚠ Failed to create test table"
# Try to get error details
docker exec "$CONTAINER_NAME" mysql -u playground -pplayground playground \
    -e "SHOW TABLES;" 2>&1 | head -5
fi