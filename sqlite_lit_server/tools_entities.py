import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from .db import DB_PATH, SQLiteConnection
from .repository import get_sources_details, search_sources
from .schema import EntityRelations, SourceTypes


def register_tools(mcp):
    @mcp.tool()
    def link_to_entities(
        source_entity_links: List[Tuple[str, str, str, str, str, str, Optional[str]]]
    ) -> List[Dict[str, Any]]:
        """Link multiple sources to entities."""
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Database not found at: {DB_PATH}")
        if not source_entity_links:
            return []

        for _, _, _, _, _, relation_type, _ in source_entity_links:
            if relation_type not in EntityRelations.VALID_TYPES:
                raise ValueError(
                    f"Invalid relation type. Must be one of: {EntityRelations.VALID_TYPES}"
                )

        search_inputs = [
            (title, type_, id_type, id_value)
            for title, type_, id_type, id_value, _, _, _ in source_entity_links
        ]
        search_results = search_sources(search_inputs, DB_PATH)

        results = [None] * len(source_entity_links)
        links_to_add = []
        source_ids = []

        for input_index, ((title, type_, id_type, id_value, entity_name, relation_type, notes), (uuid_str, matches)) in enumerate(
            zip(source_entity_links, search_results)
        ):
            if not uuid_str:
                results[input_index] = (
                    {
                        "status": "error",
                        "message": "Multiple potential matches found. Please verify the source.",
                        "matches": matches,
                    }
                    if matches
                    else {"status": "error", "message": "Source not found"}
                )
                continue

            links_to_add.append(
                {
                    "input_index": input_index,
                    "source_id": uuid_str,
                    "entity_name": entity_name,
                    "relation_type": relation_type,
                    "notes": notes,
                }
            )
            source_ids.append(uuid_str)
            results[input_index] = {"status": "pending", "source_id": uuid_str}

        if links_to_add:
            with SQLiteConnection(DB_PATH) as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        f"""
                        SELECT source_id, entity_name
                        FROM source_entity_links
                        WHERE (source_id, entity_name) IN ({','.join('(?,?)' for _ in links_to_add)})
                        """,
                        [val for link in links_to_add for val in (link["source_id"], link["entity_name"])],
                    )
                    existing_links = {
                        (row["source_id"], row["entity_name"])
                        for row in cursor.fetchall()
                    }

                    filtered_links = []
                    for link in links_to_add:
                        if (link["source_id"], link["entity_name"]) in existing_links:
                            results[link["input_index"]] = {
                                "status": "error",
                                "message": "Link already exists between this source and entity",
                            }
                        else:
                            filtered_links.append(link)

                    if filtered_links:
                        cursor.executemany(
                            """
                            INSERT INTO source_entity_links
                            (source_id, entity_name, relation_type, notes)
                            VALUES (:source_id, :entity_name, :relation_type, :notes)
                            """,
                            filtered_links,
                        )
                        conn.commit()
                        source_details_by_id = {
                            source["id"]: source
                            for source in get_sources_details(list(set(source_ids)), DB_PATH)
                        }
                        for link in filtered_links:
                            results[link["input_index"]] = {
                                "status": "success",
                                "source": source_details_by_id[link["source_id"]],
                            }
                except sqlite3.Error as exc:
                    conn.rollback()
                    raise ValueError(f"Database error: {str(exc)}")

        return [result for result in results if result is not None]

    @mcp.tool()
    def get_source_entities(
        sources: List[Tuple[str, str, str, str]]
    ) -> List[Dict[str, Any]]:
        """Get all entities linked to multiple sources."""
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Database not found at: {DB_PATH}")
        if not sources:
            return []

        search_results = search_sources(sources, DB_PATH)
        results = []
        source_ids = []

        for (title, type_, id_type, id_value), (uuid_str, matches) in zip(sources, search_results):
            if not uuid_str:
                results.append(
                    {
                        "status": "error",
                        "message": "Multiple potential matches found. Please verify the source.",
                        "matches": matches,
                    }
                    if matches
                    else {"status": "error", "message": "Source not found"}
                )
                continue
            source_ids.append(uuid_str)
            results.append({"status": "pending", "source_id": uuid_str})

        if source_ids:
            try:
                source_details = get_sources_details(source_ids, DB_PATH)
                for index, result in enumerate(results):
                    if result.get("status") == "pending":
                        source_id = result["source_id"]
                        source_detail = next(source for source in source_details if source["id"] == source_id)
                        results[index] = {"status": "success", "source": source_detail}
            except ValueError as exc:
                for index, result in enumerate(results):
                    if result.get("status") == "pending":
                        results[index] = {"status": "error", "message": str(exc)}

        return results

    @mcp.tool()
    def update_entity_links(
        source_entity_updates: List[Tuple[str, str, str, str, str, Optional[str], Optional[str]]]
    ) -> List[Dict[str, Any]]:
        """Update existing links between sources and entities."""
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Database not found at: {DB_PATH}")
        if not source_entity_updates:
            return []

        for _, _, _, _, _, relation_type, notes in source_entity_updates:
            if relation_type and relation_type not in EntityRelations.VALID_TYPES:
                raise ValueError(
                    f"Invalid relation type. Must be one of: {EntityRelations.VALID_TYPES}"
                )
            if not relation_type and notes is None:
                raise ValueError("At least one of relation_type or notes must be provided")

        search_inputs = [
            (title, type_, id_type, id_value)
            for title, type_, id_type, id_value, _, _, _ in source_entity_updates
        ]
        search_results = search_sources(search_inputs, DB_PATH)

        results = [None] * len(source_entity_updates)
        updates_to_make = []
        source_ids = []

        for input_index, ((title, type_, id_type, id_value, entity_name, relation_type, notes), (uuid_str, matches)) in enumerate(
            zip(source_entity_updates, search_results)
        ):
            if not uuid_str:
                results[input_index] = (
                    {
                        "status": "error",
                        "message": "Multiple potential matches found. Please verify the source.",
                        "matches": matches,
                    }
                    if matches
                    else {"status": "error", "message": "Source not found"}
                )
                continue
            updates_to_make.append(
                {
                    "input_index": input_index,
                    "source_id": uuid_str,
                    "entity_name": entity_name,
                    "relation_type": relation_type,
                    "notes": notes,
                }
            )
            source_ids.append(uuid_str)
            results[input_index] = {"status": "pending", "source_id": uuid_str}

        if updates_to_make:
            with SQLiteConnection(DB_PATH) as conn:
                cursor = conn.cursor()
                try:
                    for update in updates_to_make:
                        assignments = []
                        params = []
                        if update["relation_type"]:
                            assignments.append("relation_type = ?")
                            params.append(update["relation_type"])
                        if update["notes"] is not None:
                            assignments.append("notes = ?")
                            params.append(update["notes"])
                        params.extend([update["source_id"], update["entity_name"]])
                        cursor.execute(
                            f"""
                            UPDATE source_entity_links
                            SET {', '.join(assignments)}
                            WHERE source_id = ? AND entity_name = ?
                            """,
                            params,
                        )
                        if cursor.rowcount == 0:
                            results[update["input_index"]] = {
                                "status": "error",
                                "message": "No link found between this source and entity",
                            }
                    conn.commit()
                    source_details_by_id = {
                        source["id"]: source
                        for source in get_sources_details(list(set(source_ids)), DB_PATH)
                    }
                    for update in updates_to_make:
                        if results[update["input_index"]].get("status") == "pending":
                            results[update["input_index"]] = {
                                "status": "success",
                                "source": source_details_by_id[update["source_id"]],
                            }
                except sqlite3.Error as exc:
                    conn.rollback()
                    raise ValueError(f"Database error: {str(exc)}")

        return [result for result in results if result is not None]

    @mcp.tool()
    def remove_entity_links(
        source_entity_pairs: List[Tuple[str, str, str, str, str]]
    ) -> List[Dict[str, Any]]:
        """Remove links between sources and entities."""
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Database not found at: {DB_PATH}")
        if not source_entity_pairs:
            return []

        search_inputs = [
            (title, type_, id_type, id_value)
            for title, type_, id_type, id_value, _ in source_entity_pairs
        ]
        search_results = search_sources(search_inputs, DB_PATH)

        results = [None] * len(source_entity_pairs)
        links_to_remove = []
        source_ids = []

        for input_index, ((title, type_, id_type, id_value, entity_name), (uuid_str, matches)) in enumerate(
            zip(source_entity_pairs, search_results)
        ):
            if not uuid_str:
                results[input_index] = (
                    {
                        "status": "error",
                        "message": "Multiple potential matches found. Please verify the source.",
                        "matches": matches,
                    }
                    if matches
                    else {"status": "error", "message": "Source not found"}
                )
                continue
            links_to_remove.append(
                {
                    "input_index": input_index,
                    "source_id": uuid_str,
                    "entity_name": entity_name,
                }
            )
            source_ids.append(uuid_str)
            results[input_index] = {"status": "pending", "source_id": uuid_str}

        if links_to_remove:
            with SQLiteConnection(DB_PATH) as conn:
                cursor = conn.cursor()
                try:
                    pair_params = [
                        val for link in links_to_remove for val in (link["source_id"], link["entity_name"])
                    ]
                    cursor.execute(
                        f"""
                        SELECT source_id, entity_name
                        FROM source_entity_links
                        WHERE (source_id, entity_name) IN ({','.join('(?,?)' for _ in links_to_remove)})
                        """,
                        pair_params,
                    )
                    existing_links = {
                        (row["source_id"], row["entity_name"])
                        for row in cursor.fetchall()
                    }

                    removable_links = []
                    for link in links_to_remove:
                        if (link["source_id"], link["entity_name"]) in existing_links:
                            removable_links.append(link)
                        else:
                            results[link["input_index"]] = {
                                "status": "error",
                                "message": "No link found between this source and entity",
                            }

                    if removable_links:
                        cursor.execute(
                            f"""
                            DELETE FROM source_entity_links
                            WHERE (source_id, entity_name) IN ({','.join('(?,?)' for _ in removable_links)})
                            """,
                            [
                                val
                                for link in removable_links
                                for val in (link["source_id"], link["entity_name"])
                            ],
                        )
                    conn.commit()
                    source_details_by_id = {
                        source["id"]: source
                        for source in get_sources_details(list(set(source_ids)), DB_PATH)
                    }
                    for link in links_to_remove:
                        if results[link["input_index"]].get("status") == "pending":
                            results[link["input_index"]] = {
                                "status": "success",
                                "source": source_details_by_id[link["source_id"]],
                            }
                except sqlite3.Error as exc:
                    conn.rollback()
                    raise ValueError(f"Database error: {str(exc)}")

        return [result for result in results if result is not None]

    @mcp.tool()
    def get_entity_sources(
        entity_filters: List[Tuple[str, Optional[str], Optional[str]]]
    ) -> List[Dict[str, Any]]:
        """Get all sources linked to specific entities with optional filtering."""
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Database not found at: {DB_PATH}")
        if not entity_filters:
            return []

        for _, type_filter, relation_filter in entity_filters:
            if type_filter and type_filter not in SourceTypes.VALID_TYPES:
                raise ValueError(f"Invalid type filter. Must be one of: {SourceTypes.VALID_TYPES}")
            if relation_filter and relation_filter not in EntityRelations.VALID_TYPES:
                raise ValueError(
                    f"Invalid relation filter. Must be one of: {EntityRelations.VALID_TYPES}"
                )

        results = []
        with SQLiteConnection(DB_PATH) as conn:
            cursor = conn.cursor()
            try:
                for entity_name, type_filter, relation_filter in entity_filters:
                    query = """
                        SELECT DISTINCT s.id
                        FROM sources s
                        JOIN source_entity_links l ON s.id = l.source_id
                        WHERE l.entity_name = ?
                    """
                    params = [entity_name]
                    if type_filter:
                        query += " AND s.type = ?"
                        params.append(type_filter)
                    if relation_filter:
                        query += " AND l.relation_type = ?"
                        params.append(relation_filter)
                    cursor.execute(query, params)
                    source_ids = [row["id"] for row in cursor.fetchall()]
                    results.append(
                        {
                            "status": "success",
                            "entity": entity_name,
                            "filters_applied": {"type": type_filter, "relation": relation_filter},
                            "sources": get_sources_details(source_ids, DB_PATH) if source_ids else [],
                        }
                    )
            except sqlite3.Error as exc:
                raise ValueError(f"Database error: {str(exc)}")

        return results

    return {
        "link_to_entities": link_to_entities,
        "get_source_entities": get_source_entities,
        "update_entity_links": update_entity_links,
        "remove_entity_links": remove_entity_links,
        "get_entity_sources": get_entity_sources,
    }
