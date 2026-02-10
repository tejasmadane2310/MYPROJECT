CREATE DATABASE billing_db;
CREATE USER 'billuser'@'localhost' IDENTIFIED BY 'billpass';
GRANT ALL PRIVILEGES ON billing_db.* TO 'billuser'@'localhost';
FLUSH PRIVILEGES;

use billing_db;

-- Customers

CREATE TABLE IF NOT EXISTS customers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  phone VARCHAR(30) UNIQUE,
  email VARCHAR(200),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products
CREATE TABLE IF NOT EXISTS products (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  price DECIMAL(10,2) NOT NULL,
  sku VARCHAR(100) UNIQUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inventory (stock levels)
CREATE TABLE IF NOT EXISTS inventory (
  product_id INT PRIMARY KEY,
  stock INT DEFAULT 0,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Bills
CREATE TABLE IF NOT EXISTS bills (
  bill_id INT AUTO_INCREMENT PRIMARY KEY,
  customer_id INT,
  bill_date DATETIME DEFAULT CURRENT_TIMESTAMP,
  total_amount DECIMAL(12,2),
  gst_amount DECIMAL(12,2),
  discount_amount DECIMAL(12,2),
  final_amount DECIMAL(12,2),
  FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
);

-- Bill items
CREATE TABLE IF NOT EXISTS bill_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  bill_id INT,
  product_id INT,
  quantity INT,
  price_each DECIMAL(10,2),
  line_total DECIMAL(12,2),
  FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
);

show tables;
select*from customers;