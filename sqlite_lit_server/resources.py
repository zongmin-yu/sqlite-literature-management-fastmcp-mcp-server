import json

from .db import DB_PATH, SQLiteConnection
from .repository import get_sources_details, search_sources, source_exists


def _render_json(payload):
    return json.dumps(payload, indent=2, sort_keys=True)


def register_resources(mcp):
    @mcp.resource("source://{source_id}")
    def source_resource(source_id: str) -> str:
        if not source_exists(source_id, DB_PATH):
            raise ValueError(f"Source not found: {source_id}")
        return _render_json(get_sources_details(source_id, DB_PATH)[0])

    @mcp.resource("source://by-identifier/{identifier_type}/{identifier_value}")
    def source_by_identifier_resource(identifier_type: str, identifier_value: str) -> str:
        matches = search_sources(
            [("", source_type, identifier_type, identifier_value) for source_type in ["paper", "webpage", "book", "video", "blog"]],
            DB_PATH,
        )
        source_id = next((uuid_str for uuid_str, _ in matches if uuid_str), None)
        if source_id is None:
            raise ValueError(
                f"Source not found for identifier {identifier_type}={identifier_value}"
            )
        return _render_json(get_sources_details(source_id, DB_PATH)[0])

    @mcp.resource("reading-list://unread")
    def unread_reading_list() -> str:
        return _render_json(_get_sources_by_status("unread"))

    @mcp.resource("reading-list://reading")
    def reading_reading_list() -> str:
        return _render_json(_get_sources_by_status("reading"))

    @mcp.resource("entity://{entity_name}")
    def entity_resource(entity_name: str) -> str:
        with SQLiteConnection(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT source_id
                FROM source_entity_links
                WHERE entity_name = ?
                ORDER BY source_id
                """,
                [entity_name],
            )
            source_ids = [row["source_id"] for row in cursor.fetchall()]
        return _render_json(
            {
                "entity": entity_name,
                "sources": get_sources_details(source_ids, DB_PATH) if source_ids else [],
            }
        )

    return {
        "source_resource": source_resource,
        "source_by_identifier_resource": source_by_identifier_resource,
        "unread_reading_list": unread_reading_list,
        "reading_reading_list": reading_reading_list,
        "entity_resource": entity_resource,
    }


def _get_sources_by_status(status: str):
    with SQLiteConnection(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id
            FROM sources
            WHERE status = ?
            ORDER BY title
            """,
            [status],
        )
        source_ids = [row["id"] for row in cursor.fetchall()]
    return get_sources_details(source_ids, DB_PATH) if source_ids else []
