"""Disposable, fake commerce records for database acceptance checks."""

from contextlib import closing
from pathlib import Path
import sqlite3


def prepare_sample_database(path):
    """Create a new fixture only; callers own temporary-directory cleanup."""
    path = Path(path)
    # Exclusive reservation prevents overwriting an existing database.
    with path.open('xb'):
        pass
    try:
        with closing(sqlite3.connect(path)) as connection, connection:
            connection.executescript('''
                CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL,
                    price INTEGER NOT NULL CHECK(price >= 0), stock INTEGER NOT NULL);
                CREATE TABLE orders (id INTEGER PRIMARY KEY, customer TEXT NOT NULL,
                    status TEXT NOT NULL, note TEXT);
                CREATE TABLE order_items (order_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL, unit_price INTEGER NOT NULL);
            ''')
            connection.executemany('INSERT INTO products VALUES (?, ?, ?, ?)',
                [(1, 'Notebook', 10, 5), (2, 'Pencil', 2, 0), (3, 'Çanta', 30, 2)])
            connection.executemany('INSERT INTO orders VALUES (?, ?, ?, ?)',
                [(1, 'demo-user', 'paid', None), (2, 'other-user', 'cancelled', 'fixture')])
            connection.executemany('INSERT INTO order_items VALUES (?, ?, ?, ?)',
                [(1, 1, 2, 10), (1, 2, 3, 2), (2, 3, 1, 30)])
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path
