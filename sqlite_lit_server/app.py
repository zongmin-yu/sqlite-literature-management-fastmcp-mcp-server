from fastmcp import FastMCP

from .db import DB_PATH, SQLiteConnection
from .repository import get_sources_details, search_sources
from .resources import register_resources
from .schema import EntityRelations, SourceIdentifiers, SourceStatus, SourceTypes
from .tools_admin import register_tools as register_admin_tools
from .tools_entities import register_tools as register_entity_tools
from .tools_sources import register_tools as register_source_tools


mcp = FastMCP("Source Manager")

globals().update(register_admin_tools(mcp))
globals().update(register_source_tools(mcp))
globals().update(register_entity_tools(mcp))
globals().update(register_resources(mcp))

__all__ = [
    "DB_PATH",
    "EntityRelations",
    "SQLiteConnection",
    "SourceIdentifiers",
    "SourceStatus",
    "SourceTypes",
    "add_identifiers",
    "add_notes",
    "add_sources",
    "describe_table",
    "get_database_info",
    "get_entity_sources",
    "get_source_entities",
    "get_sources_details",
    "get_table_stats",
    "link_to_entities",
    "list_tables",
    "mcp",
    "read_query",
    "remove_entity_links",
    "search_sources",
    "update_entity_links",
    "update_status",
    "vacuum_database",
]
