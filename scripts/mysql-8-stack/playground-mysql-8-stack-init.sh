#!/bin/bash
echo "Initializing MySQL..."

# Wait for MySQL
MAX_WAIT=60
COUNT=0
while [ $COUNT -lt $MAX_WAIT ]; do
if docker exec "${CONTAINER_NAME}" mysqladmin ping -u root -pplayground --silent 2>/dev/null; then
    echo "✓ MySQL is ready!"
    break
fi
sleep 2
COUNT=$((COUNT + 2))
done

sleep 5

# Create tables and insert data
docker exec "${CONTAINER_NAME}" mysql -u root -pplayground playground -e "
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2),
    category VARCHAR(50)
);

INSERT INTO users (username, email) VALUES 
('admin', 'admin@playground.local'),
('user1', 'user1@example.com')
ON DUPLICATE KEY UPDATE username=username;

INSERT INTO products (name, price, category) VALUES 
('Laptop', 999.99, 'Electronics'),
('Mouse', 29.99, 'Electronics')
ON DUPLICATE KEY UPDATE name=name;
" 2>/dev/null

echo "✓ MySQL initialized"