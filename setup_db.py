import sqlite3
import pandas as pd

def create_database():
    # Connect to SQLite (this will create 'ecommerce.db' in your current folder)
    conn = sqlite3.connect('ecommerce.db')
    cursor = conn.cursor()

    # 1. Create Tables
    cursor.executescript('''
        DROP TABLE IF EXISTS order_items;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS customers;

        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            region TEXT NOT NULL,
            signup_date DATE NOT NULL
        );

        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL
        );

        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            order_date DATE NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
        );

        CREATE TABLE order_items (
            order_item_id INTEGER PRIMARY KEY,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (order_id),
            FOREIGN KEY (product_id) REFERENCES products (product_id)
        );
    ''')

    # 2. Insert Sample Data
    customers_data = [
        (1, 'Alice Smith', 'West', '2023-01-15'),
        (2, 'Bob Johnson', 'East', '2023-03-22'),
        (3, 'Charlie Brown', 'West', '2023-07-10')
    ]
    
    products_data = [
        (101, 'Laptop', 'Electronics', 1200.00),
        (102, 'Desk Chair', 'Furniture', 250.00),
        (103, 'Mouse', 'Electronics', 45.00)
    ]
    
    orders_data = [
        (1001, 1, '2023-08-01', 'Completed'),
        (1002, 2, '2023-08-15', 'Completed'),
        (1003, 1, '2023-09-10', 'Refunded'),
        (1004, 3, '2023-10-05', 'Completed')
    ]
    
    order_items_data = [
        (10001, 1001, 101, 1),
        (10002, 1001, 103, 2),
        (10003, 1002, 102, 4),
        (10004, 1003, 101, 1),
        (10005, 1004, 101, 2)
    ]

    cursor.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", customers_data)
    cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", products_data)
    cursor.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", orders_data)
    cursor.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?)", order_items_data)

    conn.commit()
    print("Database 'ecommerce.db' created successfully with sample data!")

    # Verify data using Pandas
    print("\nSample Data (Customers in West Region):")
    df = pd.read_sql_query("SELECT * FROM customers WHERE region = 'West'", conn)
    print(df)

    conn.close()

if __name__ == "__main__":
    create_database()