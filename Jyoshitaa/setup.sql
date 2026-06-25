-- Run this in MySQL Workbench or terminal before starting Flask

CREATE DATABASE IF NOT EXISTS ecommerce_db;
USE ecommerce_db;

CREATE TABLE IF NOT EXISTS categories (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    status      ENUM('active', 'inactive') DEFAULT 'active',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(150) NOT NULL,
    category_id INT,
    price       DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    description TEXT,
    status      ENUM('active', 'inactive') DEFAULT 'active',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
);

-- Sample data (optional)
INSERT INTO categories (name, status) VALUES
  ('Electronics', 'active'),
  ('Clothing',    'active'),
  ('Books',       'inactive');

INSERT INTO products (name, category_id, price, description, status) VALUES
  ('iPhone 15',     1, 79999.00, 'Latest Apple smartphone',  'active'),
  ('T-Shirt',       2,   499.00, 'Cotton round neck t-shirt','active'),
  ('Python Basics', 3,   299.00, 'Beginner Python book',     'inactive');