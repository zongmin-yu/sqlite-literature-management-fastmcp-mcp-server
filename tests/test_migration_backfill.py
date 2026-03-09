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


VERSION_2_SCHEMA = """
CREATE TABLE sources (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    type TEXT CHECK(type IN ('paper', 'webpage', 'book', 'video', 'blog')) NOT NULL,
    identifiers TEXT NOT NULL,
    status TEXT CHECK(status IN ('unread', 'reading', 'completed', 'archived')) DEFAULT 'unread',
    provider TEXT,
    discovered_via TEXT,
    discovered_at TIMESTAMP
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

CREATE TABLE source_identifiers (
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    identifier_type TEXT NOT NULL CHECK(identifier_type IN ('semantic_scholar', 'doi', 'arxiv', 'openalex', 'pmid', 'isbn', 'url')),
    identifier_value TEXT NOT NULL,
    normalized_value TEXT NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 0 CHECK(is_primary IN (0, 1)),
    PRIMARY KEY (source_id, identifier_type),
    UNIQUE (identifier_type, normalized_value)
);

CREATE INDEX idx_sources_type ON sources(type);
CREATE INDEX idx_sources_status ON sources(status);
CREATE INDEX idx_source_notes_created ON source_notes(created_at);
CREATE INDEX idx_entity_links_name ON source_entity_links(entity_name);
CREATE INDEX idx_source_identifiers_source ON source_identifiers(source_id);
CREATE INDEX idx_source_identifiers_lookup ON source_identifiers(identifier_type, normalized_value);

PRAGMA user_version = 2;
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

    expand_relations_sql = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "2026-03-09__expand-entity-relation-types.sql"
    )
    with sqlite3.connect(db_path) as conn:
        conn.executescript(expand_relations_sql.read_text())

    server_module = load_server_module(db_path)
    search_results = server_module.search_sources(
        [("Migrated Source", "paper", "doi", "10.1000/xyz")],
        server_module.DB_PATH,
    )
    assert search_results == [("source-1", [])]


def test_expand_entity_relations_migration_preserves_existing_rows(tmp_path):
    db_path = tmp_path / "relations-v2.db"
    migration_sql = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "2026-03-09__expand-entity-relation-types.sql"
    )

    with sqlite3.connect(db_path) as conn:
        conn.executescript(VERSION_2_SCHEMA)
        conn.execute(
            """
            INSERT INTO sources (id, title, type, identifiers, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                "source-1",
                "Migrated Relations Source",
                "paper",
                '{"arxiv": "1706.03762"}',
                "unread",
            ],
        )
        conn.execute(
            """
            INSERT INTO source_entity_links (source_id, entity_name, relation_type, notes)
            VALUES (?, ?, ?, ?)
            """,
            ["source-1", "transformer", "introduces", "Preserve me"],
        )
        conn.executescript(migration_sql.read_text())
        migrated_rows = conn.execute(
            """
            SELECT source_id, entity_name, relation_type, notes
            FROM source_entity_links
            """
        ).fetchall()
        version = conn.execute("PRAGMA user_version").fetchone()[0]

    assert migrated_rows == [("source-1", "transformer", "introduces", "Preserve me")]
    assert version == 3
