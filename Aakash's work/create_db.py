"""
create_db.py
-------------
Creates database.db (SQLite) with the `categories` and `products` tables
required by the Mini E-Commerce Product Management System, and seeds it
with a handful of sample rows so the app is immediately demoable.

Run this ONCE before starting the Flask app:

    python create_db.py
"""

import sqlite3
import os

DB_NAME = "database.db"


def create_database():
    # Remove old database file if it exists, so this script can be re-run safely.
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"Existing '{DB_NAME}' removed.")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # ---------------------------------------------------------
    # categories table
    # ---------------------------------------------------------
    cursor.execute("""
        CREATE TABLE categories (
            category_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL UNIQUE
        )
    """)

    # ---------------------------------------------------------
    # products table
    # ---------------------------------------------------------
    cursor.execute("""
        CREATE TABLE products (
            product_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            category_id  INTEGER NOT NULL,
            price        REAL NOT NULL,
            status       INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (category_id) REFERENCES categories (category_id)
        )
    """)

    # ---------------------------------------------------------
    # Seed: categories
    # ---------------------------------------------------------
    categories = [
        ("Electronics",),
        ("Clothing",),
        ("Home & Kitchen",),
        ("Books",),
        ("Sports & Fitness",),
    ]
    cursor.executemany(
        "INSERT INTO categories (category_name) VALUES (?)", categories
    )

    # ---------------------------------------------------------
    # Seed: products  (category_id is 1-indexed, matching insert order above)
    # ---------------------------------------------------------
    products = [
        ("Wireless Mouse",        1, 799.00, 1),
        ("Bluetooth Headphones",  1, 1999.00, 1),
        ("4K Monitor",            1, 15999.00, 0),
        ("Men's Cotton T-Shirt",  2, 499.00, 1),
        ("Denim Jacket",          2, 2199.00, 1),
        ("Running Shoes",         5, 2999.00, 1),
        ("Non-Stick Frying Pan",  3, 899.00, 1),
        ("Ceramic Dinner Set",    3, 1799.00, 0),
        ("The Pragmatic Programmer", 4, 599.00, 1),
        ("Atomic Habits",         4, 399.00, 1),
        ("Yoga Mat",              5, 699.00, 1),
        ("Smart Watch",           1, 3499.00, 1),
    ]
    cursor.executemany(
        """INSERT INTO products (product_name, category_id, price, status)
           VALUES (?, ?, ?, ?)""",
        products,
    )

    conn.commit()
    conn.close()
    print(f"'{DB_NAME}' created successfully with sample data.")


if __name__ == "__main__":
    create_database()
