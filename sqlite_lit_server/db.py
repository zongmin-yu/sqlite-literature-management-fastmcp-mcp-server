import os
import sqlite3
from pathlib import Path


if "SQLITE_DB_PATH" not in os.environ:
    raise ValueError("SQLITE_DB_PATH environment variable must be set")

DB_PATH = Path(os.environ["SQLITE_DB_PATH"])


class SQLiteConnection:
    """Context manager for SQLite database connections."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
