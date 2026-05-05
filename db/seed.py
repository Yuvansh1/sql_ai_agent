"""
Creates and seeds a SQLite database with realistic e-commerce data.
Run once: python db/seed.py
"""

import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "store.db"


def seed():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
        DROP TABLE IF EXISTS order_items;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS customers;

        CREATE TABLE customers (
            id          INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            email       TEXT UNIQUE NOT NULL,
            country     TEXT NOT NULL,
            joined_at   DATE NOT NULL
        );

        CREATE TABLE products (
            id          INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            category    TEXT NOT NULL,
            price       REAL NOT NULL,
            stock       INTEGER NOT NULL
        );

        CREATE TABLE orders (
            id          INTEGER PRIMARY KEY,
            customer_id INTEGER REFERENCES customers(id),
            status      TEXT NOT NULL,
            created_at  DATE NOT NULL
        );

        CREATE TABLE order_items (
            id          INTEGER PRIMARY KEY,
            order_id    INTEGER REFERENCES orders(id),
            product_id  INTEGER REFERENCES products(id),
            quantity    INTEGER NOT NULL,
            unit_price  REAL NOT NULL
        );
    """)

    # Customers
    countries = ["USA", "Canada", "UK", "Germany", "India", "Australia"]
    names = [
        "Alice Johnson", "Bob Smith", "Carol White", "David Brown", "Eva Green",
        "Frank Miller", "Grace Lee", "Henry Wilson", "Isla Davis", "Jack Taylor",
        "Karen Moore", "Liam Anderson", "Mia Thomas", "Noah Jackson", "Olivia Harris",
        "Paul Martin", "Quinn Thompson", "Rachel Garcia", "Sam Martinez", "Tina Robinson",
    ]
    customers = [
        (i + 1, name, f"{name.lower().replace(' ', '.')}@email.com",
         random.choice(countries),
         (datetime(2022, 1, 1) + timedelta(days=random.randint(0, 900))).strftime("%Y-%m-%d"))
        for i, name in enumerate(names)
    ]
    cur.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", customers)

    # Products
    products = [
        (1,  "Wireless Headphones",  "Electronics",  89.99,  120),
        (2,  "Mechanical Keyboard",  "Electronics", 129.99,   85),
        (3,  "USB-C Hub",            "Electronics",  39.99,  200),
        (4,  "Standing Desk",        "Furniture",   349.99,   30),
        (5,  "Ergonomic Chair",      "Furniture",   299.99,   25),
        (6,  "Desk Lamp",            "Furniture",    45.99,  150),
        (7,  "Python Crash Course",  "Books",        29.99,  500),
        (8,  "Clean Code",           "Books",        34.99,  400),
        (9,  "Running Shoes",        "Apparel",      79.99,   90),
        (10, "Yoga Mat",             "Sports",       24.99,  300),
    ]
    cur.executemany("INSERT INTO products VALUES (?,?,?,?,?)", products)

    # Orders + items
    statuses = ["completed", "completed", "completed", "shipped", "pending", "cancelled"]
    order_id = 1
    item_id = 1
    for customer_id in range(1, 21):
        for _ in range(random.randint(1, 5)):
            date = (datetime(2024, 1, 1) + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d")
            status = random.choice(statuses)
            cur.execute("INSERT INTO orders VALUES (?,?,?,?)", (order_id, customer_id, status, date))
            for _ in range(random.randint(1, 3)):
                product = random.choice(products)
                qty = random.randint(1, 4)
                cur.execute("INSERT INTO order_items VALUES (?,?,?,?,?)",
                            (item_id, order_id, product[0], qty, product[3]))
                item_id += 1
            order_id += 1

    conn.commit()
    conn.close()
    print(f"Database seeded at {DB_PATH}")
    print(f"  {len(customers)} customers, {len(products)} products, {order_id-1} orders")


if __name__ == "__main__":
    seed()
