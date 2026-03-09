import sqlite3
from pathlib import Path


OLD_SCHEMA = """
CREATE TABLE sources (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    type TEXT CHECK(type IN ('paper', 'webpage', 'book', 'video', 'blog')) NOT NULL,
    identifiers TEXT NOT NULL,
    status TEXT CHECK(status IN ('unread', 'reading', 'completed', 'archived')) DEFAULT 'unread'
);

CREATE TABLE source_notes (
    source_id TEXT REFERENCES sources(id),
    note_title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_id, note_title)
);

CREATE TABLE source_entity_links (
    source_id TEXT REFERENCES sources(id),
    entity_name TEXT,
    relation_type TEXT CHECK(relation_type IN ('discusses', 'introduces', 'extends', 'evaluates', 'applies', 'critiques')),
    notes TEXT,
    PRIMARY KEY (source_id, entity_name)
);
"""


def test_migration_backfills_identifier_rows(tmp_path, load_server_module):
    db_path = tmp_path / "migrated.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(OLD_SCHEMA)
        conn.execute(
            """
            INSERT INTO sources (id, title, type, identifiers, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                "source-1",
                "Migrated Source",
                "paper",
                '{"arxiv": "1706.03762", "doi": "10.1000/XYZ"}',
                "unread",
            ],
        )
        conn.commit()
        migration_sql = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "2026-03-09__normalize-identifiers.sql"
        )
    finally:
        conn.close()

    with sqlite3.connect(db_path) as conn:
        conn.executescript(migration_sql.read_text())
        rows = conn.execute(
            """
            SELECT identifier_type, identifier_value, normalized_value, is_primary
            FROM source_identifiers
            WHERE source_id = ?
            ORDER BY identifier_type
            """,
            ["source-1"],
        ).fetchall()

    assert rows == [
        ("arxiv", "1706.03762", "1706.03762", 1),
        ("doi", "10.1000/XYZ", "10.1000/xyz", 0),
    ]

    server_module = load_server_module(db_path)
    search_results = server_module.search_sources(
        [("Migrated Source", "paper", "doi", "10.1000/xyz")],
        server_module.DB_PATH,
    )
    assert search_results == [("source-1", [])]
