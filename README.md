# Universal Source Management System

A lightweight FastMCP server for managing literature, notes, entity links, and reading-list resources in a local SQLite database.

## Current Scope

This repository provides:

- Local SQLite-backed source management
- Notes attached to sources
- Entity links between sources and named concepts
- Read-only database inspection tools
- MCP resources for source lookup and reading lists
- Normalized identifier storage with a transitional JSON cache

It does not integrate with MCP Memory Server or an external memory graph.

## Quick Start

1. Create a database from the current schema:

```bash
sqlite3 sources.db < create_sources_db.sql
```

2. Install the FastMCP server with your database path:

```bash
fastmcp install sqlite-paper-fastmcp-server.py --name "Source Manager" -e SQLITE_DB_PATH=/path/to/sources.db
```

3. Optional: use the checked-in demo fixture at `examples/sources.db`.

## Docker

This server can be packaged as a containerized stdio MCP server.

Build the image:

```bash
docker build -t sqlite-lit-mcp .
```

Run it with a persistent SQLite volume:

```bash
mkdir -p data
docker run --rm -i \
  -e SQLITE_DB_PATH=/data/sources.db \
  -v "$(pwd)/data:/data" \
  sqlite-lit-mcp
```

Notes:

- The image defaults `SQLITE_DB_PATH` to `/data/sources.db`.
- If the database file does not exist, the container initializes it from `create_sources_db.sql`.
- If you are mounting an older database, apply `migrations/2026-03-09__normalize-identifiers.sql` before starting the server.
- This repo runs as a stdio MCP server, so there is no HTTP port to expose by default.

With Docker Compose:

```bash
docker compose run --rm sqlite-lit-mcp
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

- `source://<id>`
- `source://by-identifier/<type>/<value>`
- `reading-list://unread`
- `reading-list://reading`
- `entity://<entity_name>`

## Schema Notes

The current schema centers on four tables:

- `sources`
- `source_identifiers`
- `source_notes`
- `source_entity_links`

`sources.identifiers` is still kept as a transitional JSON cache, but identifier lookups now use `source_identifiers`.

Supported identifier types:

- `semantic_scholar`
- `doi`
- `arxiv`
- `openalex`
- `pmid`
- `isbn`
- `url`

Lightweight provenance fields live on `sources`:

- `provider`
- `discovered_via`
- `discovered_at`

The schema now uses `PRAGMA user_version = 2`.

## Migration

If you have an older database, apply:

```bash
sqlite3 /path/to/sources.db < migrations/2026-03-09__normalize-identifiers.sql
```

That migration:

- adds `source_identifiers`
- backfills identifier rows from the legacy JSON column
- adds provenance fields
- updates `PRAGMA user_version` to `2`

The server checks `PRAGMA user_version` on connection and will reject older databases until they are migrated.

## Package Layout

The implementation is organized under `sqlite_lit_server/`:

- `app.py` creates the FastMCP instance and registers tools/resources
- `db.py` owns connection setup and schema-version checks
- `repository.py` keeps SQL-heavy lookup logic close to the data layer
- `tools_admin.py`, `tools_sources.py`, and `tools_entities.py` hold the MCP tools
- `resources.py` defines the MCP resources

`sqlite-paper-fastmcp-server.py` remains as a thin compatibility shim.

## Batch Import Sources

`add_sources` is the batch import entrypoint for new sources. It accepts one argument named `sources`, where each item is:

```text
[title, source_type, identifier_type, identifier_value, initial_note]
```

`initial_note` must be either `null` or an object with both `title` and `content`.

Supported `source_type` values:

- `paper`
- `webpage`
- `book`
- `video`
- `blog`

Supported `identifier_type` values:

- `semantic_scholar`
- `doi`
- `arxiv`
- `openalex`
- `pmid`
- `isbn`
- `url`

Duplicate handling:

- Exact identifier matches return `Source already exists` together with the existing source payload.
- Title-based fuzzy matches return `Potential duplicates found. Please verify or use add_identifiers if these are the same source.`
- Successful batch writes return one result per input item in the same order as the request.

Example MCP/JSON payload:

```json
{
  "sources": [
    [
      "Attention Is All You Need",
      "paper",
      "arxiv",
      "1706.03762",
      {
        "title": "Initial thoughts",
        "content": "Transformers start here."
      }
    ],
    [
      "OpenAlex Import",
      "paper",
      "openalex",
      "W1234567890",
      null
    ]
  ]
}
```

Example Python call:

```python
add_sources([
    (
        "Attention Is All You Need",
        "paper",
        "arxiv",
        "1706.03762",
        {
            "title": "Initial thoughts",
            "content": "Transformers start here.",
        },
    ),
    (
        "OpenAlex Import",
        "paper",
        "openalex",
        "W1234567890",
        None,
    ),
])
```

The same tool payloads work whether you start the server locally or through Docker with `docker compose run --rm sqlite-lit-mcp`.

## Batch Write Conventions

Plural write tools accept lists and return a per-input result list in the same order. Related batch tools include:

- `add_notes`
- `add_identifiers`
- `update_status`
- `link_to_entities`

## Example Usage

Add another identifier:

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

Read a source resource:

```text
source://by-identifier/arxiv/1706.03762
```
