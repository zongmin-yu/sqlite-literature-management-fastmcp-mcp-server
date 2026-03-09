# Universal Source Management System

A lightweight FastMCP server for managing literature and related notes in a local SQLite database.

## Current Scope

This repository currently provides:

- Local SQLite-backed source management
- Notes attached to sources
- Entity links between sources and named concepts
- Read-only database inspection tools

It does not currently implement MCP resources, MCP Memory Server integration, or a memory graph backend.

## Quick Start

1. Create a new SQLite database with the checked-in schema:

```bash
sqlite3 sources.db < create_sources_db.sql
```

2. Install the FastMCP server with your database path:

```bash
fastmcp install sqlite-paper-fastmcp-server.py --name "Source Manager" -e SQLITE_DB_PATH=/path/to/sources.db
```

## Current Tool Surface

Implemented tools:

- `read_query`
- `list_tables`
- `describe_table`
- `get_table_stats`
- `get_database_info`
- `vacuum_database`
- `add_sources`
- `add_notes`
- `update_status`
- `add_identifiers`
- `link_to_entities`
- `get_source_entities`
- `update_entity_links`
- `remove_entity_links`
- `get_entity_sources`

Implemented resources:

- None yet

## Schema

The current SQLite schema uses three tables:

```sql
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
```

`sources.identifiers` is currently stored as a JSON string in SQLite text.

## Usage Examples

Add sources in batch form:

```python
add_sources([
    (
        "Attention Is All You Need",
        "paper",
        "arxiv",
        "1706.03762",
        {
            "title": "Initial thoughts",
            "content": "Groundbreaking paper introducing transformers.",
        },
    ),
])
```

Add an additional identifier:

```python
add_identifiers([
    (
        "Attention Is All You Need",
        "paper",
        "arxiv",
        "1706.03762",
        "semantic_scholar",
        "204e3073870fae3d05bcbc2f6a8e263d9b72e776",
    ),
])
```

Add notes:

```python
add_notes([
    (
        "Attention Is All You Need",
        "paper",
        "arxiv",
        "1706.03762",
        "Implementation details",
        "The paper describes the architecture...",
    ),
])
```

Link a source to an entity:

```python
link_to_entities([
    (
        "Attention Is All You Need",
        "paper",
        "arxiv",
        "1706.03762",
        "transformer",
        "introduces",
        "First paper to introduce the transformer architecture",
    ),
])
```

Query sources by entity:

```python
get_entity_sources([
    ("transformer", "paper", "discusses"),
])
```
