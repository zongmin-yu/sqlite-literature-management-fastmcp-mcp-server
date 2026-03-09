BEGIN;

CREATE TABLE source_entity_links_new (
    source_id TEXT REFERENCES sources(id),
    entity_name TEXT,
    relation_type TEXT CHECK(relation_type IN (
        'discusses',
        'introduces',
        'extends',
        'evaluates',
        'applies',
        'critiques',
        'supports',
        'contradicts',
        'refutes'
    )),
    notes TEXT,
    PRIMARY KEY (source_id, entity_name)
);

INSERT INTO source_entity_links_new (
    source_id,
    entity_name,
    relation_type,
    notes
)
SELECT
    source_id,
    entity_name,
    relation_type,
    notes
FROM source_entity_links;

DROP TABLE source_entity_links;

ALTER TABLE source_entity_links_new RENAME TO source_entity_links;

CREATE INDEX idx_entity_links_name ON source_entity_links(entity_name);

PRAGMA user_version = 3;

COMMIT;
