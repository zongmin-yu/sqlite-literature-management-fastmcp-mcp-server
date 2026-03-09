import os
import sqlite3
from pathlib import Path


SCHEMA_VERSION = 2


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
        self._ensure_supported_schema_version()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def _ensure_supported_schema_version(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = 'sources'
            """
        )
        has_sources_table = cursor.fetchone() is not None
        if not has_sources_table:
            return

        cursor.execute("PRAGMA user_version")
        user_version = cursor.fetchone()[0]
        if user_version < SCHEMA_VERSION:
            raise ValueError(
                "Database schema version "
                f"{user_version} is outdated. Expected at least version {SCHEMA_VERSION}. "
                "Apply migrations/2026-03-09__normalize-identifiers.sql."
            )
