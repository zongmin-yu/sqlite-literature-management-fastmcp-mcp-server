-- Core sources table
CREATE TABLE sources (
    id TEXT PRIMARY KEY,  -- Using TEXT for UUID storage
    title TEXT NOT NULL,
    type TEXT CHECK(type IN ('paper', 'webpage', 'book', 'video', 'blog')) NOT NULL,
    identifiers TEXT NOT NULL,  -- JSON string storing {type: value} pairs
    status TEXT CHECK(status IN ('unread', 'reading', 'completed', 'archived')) DEFAULT 'unread',
    provider TEXT,
    discovered_via TEXT,
    discovered_at TIMESTAMP
);

-- Notes with titles for better organization
CREATE TABLE source_notes (
    source_id TEXT REFERENCES sources(id),
    note_title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_id, note_title)
);

-- Entity links remain essential for knowledge graph integration
CREATE TABLE source_entity_links (
    source_id TEXT REFERENCES sources(id),
    entity_name TEXT,
    relation_type TEXT CHECK(relation_type IN ('discusses', 'introduces', 'extends', 'evaluates', 'applies', 'critiques', 'supports', 'contradicts', 'refutes')),
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

-- Create indexes for better performance
CREATE INDEX idx_sources_type ON sources(type);
CREATE INDEX idx_sources_status ON sources(status);
CREATE INDEX idx_source_notes_created ON source_notes(created_at);
CREATE INDEX idx_entity_links_name ON source_entity_links(entity_name);
CREATE INDEX idx_source_identifiers_source ON source_identifiers(source_id);
CREATE INDEX idx_source_identifiers_lookup ON source_identifiers(identifier_type, normalized_value);

PRAGMA user_version = 3;
