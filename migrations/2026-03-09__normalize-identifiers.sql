ALTER TABLE sources ADD COLUMN provider TEXT;
ALTER TABLE sources ADD COLUMN discovered_via TEXT;
ALTER TABLE sources ADD COLUMN discovered_at TIMESTAMP;

CREATE TABLE source_identifiers (
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    identifier_type TEXT NOT NULL CHECK(identifier_type IN ('semantic_scholar', 'doi', 'arxiv', 'openalex', 'pmid', 'isbn', 'url')),
    identifier_value TEXT NOT NULL,
    normalized_value TEXT NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 0 CHECK(is_primary IN (0, 1)),
    PRIMARY KEY (source_id, identifier_type),
    UNIQUE (identifier_type, normalized_value)
);

INSERT INTO source_identifiers (
    source_id,
    identifier_type,
    identifier_value,
    normalized_value,
    is_primary
)
SELECT
    sources.id,
    json_each.key,
    CAST(json_each.value AS TEXT),
    LOWER(TRIM(CAST(json_each.value AS TEXT))),
    CASE
        WHEN ROW_NUMBER() OVER (PARTITION BY sources.id ORDER BY json_each.key) = 1 THEN 1
        ELSE 0
    END
FROM sources
JOIN json_each(sources.identifiers)
WHERE json_each.key IN ('semantic_scholar', 'doi', 'arxiv', 'openalex', 'pmid', 'isbn', 'url');

CREATE INDEX idx_source_identifiers_source ON source_identifiers(source_id);
CREATE INDEX idx_source_identifiers_lookup ON source_identifiers(identifier_type, normalized_value);

PRAGMA user_version = 2;
