import os
import sqlite3
from typing import Any, Dict, List, Optional

from .db import DB_PATH, SQLiteConnection


def register_tools(mcp):
    @mcp.tool()
    def read_query(
        query: str,
        params: Optional[List[Any]] = None,
        fetch_all: bool = True,
        row_limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Execute a read-only query on the literature database."""
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Literature database not found at: {DB_PATH}")

        query = query.strip()
        if query.endswith(";"):
            query = query[:-1].strip()

        def contains_multiple_statements(sql: str) -> bool:
            in_single_quote = False
            in_double_quote = False
            for char in sql:
                if char == "'" and not in_double_quote:
                    in_single_quote = not in_single_quote
                elif char == '"' and not in_single_quote:
                    in_double_quote = not in_double_quote
                elif char == ";" and not in_single_quote and not in_double_quote:
                    return True
            return False

        if contains_multiple_statements(query):
            raise ValueError("Multiple SQL statements are not allowed")

        query_lower = query.lower()
        if not any(query_lower.startswith(prefix) for prefix in ("select", "with")):
            raise ValueError("Only SELECT queries (including WITH clauses) are allowed for safety")

        params = params or []

        with SQLiteConnection(DB_PATH) as conn:
            cursor = conn.cursor()
            try:
                if "limit" not in query_lower:
                    query = f"{query} LIMIT {row_limit}"
                cursor.execute(query, params)
                results = cursor.fetchall() if fetch_all else [cursor.fetchone()]
                return [dict(row) for row in results if row is not None]
            except sqlite3.Error as exc:
                raise ValueError(f"SQLite error: {str(exc)}")

    @mcp.tool()
    def list_tables() -> List[str]:
        """List all tables in the literature database."""
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Literature database not found at: {DB_PATH}")

        with SQLiteConnection(DB_PATH) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='table'
                    ORDER BY name
                    """
                )
                return [row["name"] for row in cursor.fetchall()]
            except sqlite3.Error as exc:
                raise ValueError(f"SQLite error: {str(exc)}")

    @mcp.tool()
    def describe_table(table_name: str) -> List[Dict[str, str]]:
        """Describe a table schema."""
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Literature database not found at: {DB_PATH}")

        with SQLiteConnection(DB_PATH) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name=?
                    """,
                    [table_name],
                )
                if not cursor.fetchone():
                    raise ValueError(f"Table '{table_name}' does not exist")
                cursor.execute(f"PRAGMA table_info({table_name})")
                return [dict(row) for row in cursor.fetchall()]
            except sqlite3.Error as exc:
                raise ValueError(f"SQLite error: {str(exc)}")

    @mcp.tool()
    def get_table_stats(table_name: str) -> Dict[str, Any]:
        """Get simple statistics about a table."""
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Literature database not found at: {DB_PATH}")

        with SQLiteConnection(DB_PATH) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name=?
                    """,
                    [table_name],
                )
                if not cursor.fetchone():
                    raise ValueError(f"Table '{table_name}' does not exist")

                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                row_count = cursor.fetchone()["count"]
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = len(cursor.fetchall())
                return {
                    "table_name": table_name,
                    "row_count": row_count,
                    "column_count": columns,
                    "page_size": page_size,
                }
            except sqlite3.Error as exc:
                raise ValueError(f"SQLite error: {str(exc)}")

    @mcp.tool()
    def get_database_info() -> Dict[str, Any]:
        """Get overall database information and row counts."""
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Literature database not found at: {DB_PATH}")

        with SQLiteConnection(DB_PATH) as conn:
            cursor = conn.cursor()
            try:
                db_size = os.path.getsize(DB_PATH)
                cursor.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    """
                )
                table_count = cursor.fetchone()["count"]
                cursor.execute("SELECT sqlite_version()")
                version = cursor.fetchone()[0]
                tables = {}
                cursor.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    """
                )
                for row in cursor.fetchall():
                    table_name = row["name"]
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                    tables[table_name] = cursor.fetchone()["count"]
                return {
                    "database_size_bytes": db_size,
                    "table_count": table_count,
                    "sqlite_version": version,
                    "table_row_counts": tables,
                    "path": str(DB_PATH),
                }
            except sqlite3.Error as exc:
                raise ValueError(f"SQLite error: {str(exc)}")

    @mcp.tool()
    def vacuum_database() -> Dict[str, Any]:
        """Optimize the database by running VACUUM."""
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Literature database not found at: {DB_PATH}")

        with SQLiteConnection(DB_PATH) as conn:
            cursor = conn.cursor()
            try:
                size_before = os.path.getsize(DB_PATH)
                cursor.execute("VACUUM")
                size_after = os.path.getsize(DB_PATH)
                return {
                    "status": "success",
                    "size_before_bytes": size_before,
                    "size_after_bytes": size_after,
                    "space_saved_bytes": size_before - size_after,
                }
            except sqlite3.Error as exc:
                raise ValueError(f"SQLite error: {str(exc)}")

    return {
        "read_query": read_query,
        "list_tables": list_tables,
        "describe_table": describe_table,
        "get_table_stats": get_table_stats,
        "get_database_info": get_database_info,
        "vacuum_database": vacuum_database,
    }
