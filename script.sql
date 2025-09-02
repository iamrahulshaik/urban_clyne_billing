
CREATE DATABASE bills;
USE bills;

CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    sizes VARCHAR(50) DEFAULT 'S,M,L,XL'
);

CREATE TABLE bills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    mobile_number VARCHAR(15) NOT NULL,
    product_id INT NOT NULL,
    size VARCHAR(5) NOT NULL,
    quantity INT NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    bill_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

ALTER TABLE products 
ADD COLUMN buying_price DECIMAL(10,2) AFTER name,
ADD COLUMN selling_price DECIMAL(10,2) AFTER buying_price;

-- Optional: remove old price column if not needed
ALTER TABLE products DROP COLUMN price;


SELECT 
    p.id,
    p.name,
    SUM(b.quantity) AS total_quantity_sold,
    SUM(b.total) AS total_revenue,
    SUM((p.selling_price - p.buying_price) * b.quantity) AS total_profit
FROM bills b
JOIN products p ON b.product_id = p.id
GROUP BY p.id, p.name;
