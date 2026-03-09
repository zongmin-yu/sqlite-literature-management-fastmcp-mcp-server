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


def test_fresh_schema_sets_user_version(server_module):
    with sqlite3.connect(server_module.DB_PATH) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]

    assert version == 3
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
        assert "2026-03-09__expand-entity-relation-types.sql" in str(exc)
    else:
        raise AssertionError("Expected outdated schema check to reject version 0 database")


def test_version_2_schema_raises_clear_error(tmp_path, load_server_module):
    db_path = tmp_path / "v2.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(VERSION_2_SCHEMA)
        conn.commit()

    server_module = load_server_module(db_path)

    try:
        server_module.list_tables.fn()
    except ValueError as exc:
        assert "Database schema version 2 is outdated" in str(exc)
        assert "2026-03-09__expand-entity-relation-types.sql" in str(exc)
    else:
        raise AssertionError("Expected version 2 database to be rejected until migrated")
