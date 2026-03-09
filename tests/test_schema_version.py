import sqlite3


OLD_SCHEMA = """
CREATE TABLE sources (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    type TEXT CHECK(type IN ('paper', 'webpage', 'book', 'video', 'blog')) NOT NULL,
    identifiers TEXT NOT NULL,
    status TEXT CHECK(status IN ('unread', 'reading', 'completed', 'archived')) DEFAULT 'unread'
);
"""


def test_fresh_schema_sets_user_version(server_module):
    with sqlite3.connect(server_module.DB_PATH) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]

    assert version == 2
    assert server_module.list_tables.fn()


def test_outdated_schema_raises_clear_error(tmp_path, load_server_module):
    db_path = tmp_path / "old.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(OLD_SCHEMA)
        conn.commit()

    server_module = load_server_module(db_path)

    try:
        server_module.list_tables.fn()
    except ValueError as exc:
        assert "Database schema version 0 is outdated" in str(exc)
        assert "2026-03-09__normalize-identifiers.sql" in str(exc)
    else:
        raise AssertionError("Expected outdated schema check to reject version 0 database")
