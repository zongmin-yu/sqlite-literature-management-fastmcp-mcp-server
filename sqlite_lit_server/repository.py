import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .db import SQLiteConnection
from .schema import SourceIdentifiers, SourceTypes


def normalize_identifier_value(identifier_type: str, identifier_value: str) -> str:
    del identifier_type
    return identifier_value.strip().lower()


def table_exists(conn, table_name: str) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        [table_name],
    )
    return cursor.fetchone() is not None


def source_exists(source_id: str, db_path: Path) -> bool:
    with SQLiteConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM sources WHERE id = ?", [source_id])
        return cursor.fetchone() is not None


def search_sources(
    sources: List[Tuple[str, str, str, str]],
    db_path: Path,
) -> List[Tuple[Optional[str], List[Dict[str, Any]]]]:
    """Bulk search for multiple sources while preserving input order."""
    results = []

    with SQLiteConnection(db_path) as conn:
        cursor = conn.cursor()
        has_normalized_identifiers = table_exists(conn, "source_identifiers")

        for title, type_, identifier_type, identifier_value in sources:
            if type_ not in SourceTypes.VALID_TYPES:
                raise ValueError(f"Invalid source type. Must be one of: {SourceTypes.VALID_TYPES}")
            if identifier_type not in SourceIdentifiers.VALID_TYPES:
                raise ValueError(
                    f"Invalid identifier type. Must be one of: {SourceIdentifiers.VALID_TYPES}"
                )

            if has_normalized_identifiers:
                cursor.execute(
                    """
                    SELECT s.id
                    FROM sources s
                    JOIN source_identifiers si ON s.id = si.source_id
                    WHERE s.type = ?
                      AND si.identifier_type = ?
                      AND si.normalized_value = ?
                    """,
                    [
                        type_,
                        identifier_type,
                        normalize_identifier_value(identifier_type, identifier_value),
                    ],
                )
            else:
                cursor.execute(
                    """
                    SELECT id FROM sources
                    WHERE type = ? AND
                          json_extract(identifiers, ?) = ?
                    """,
                    [type_, f"$.{identifier_type}", identifier_value],
                )

            result = cursor.fetchone()
            if result:
                results.append((result["id"], []))
                continue

            cursor.execute(
                """
                SELECT id, title, identifiers
                FROM sources
                WHERE type = ? AND
                      LOWER(title) LIKE ?
                """,
                [type_, f"%{title.lower()}%"],
            )

            potential_matches = [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "identifiers": json.loads(row["identifiers"]),
                }
                for row in cursor.fetchall()
            ]
            results.append((None, potential_matches))

    return results


def get_sources_details(uuids: Union[str, List[str]], db_path: Path) -> List[Dict[str, Any]]:
    """Get complete information about one or more sources by UUID."""
    if isinstance(uuids, str):
        uuids = [uuids]

    if not uuids:
        return []

    with SQLiteConnection(db_path) as conn:
        cursor = conn.cursor()
        placeholders = ",".join("?" * len(uuids))
        cursor.execute(f"PRAGMA table_info(sources)")
        source_columns = {row["name"] for row in cursor.fetchall()}
        has_provenance = {"provider", "discovered_via", "discovered_at"}.issubset(source_columns)

        selected_columns = ["id", "title", "type", "status", "identifiers"]
        if has_provenance:
            selected_columns.extend(["provider", "discovered_via", "discovered_at"])

        cursor.execute(
            f"""
            SELECT {', '.join(selected_columns)}
            FROM sources
            WHERE id IN ({placeholders})
            """,
            uuids,
        )

        sources = cursor.fetchall()
        if len(sources) != len(uuids):
            found_ids = {source["id"] for source in sources}
            missing_ids = [uuid for uuid in uuids if uuid not in found_ids]
            raise ValueError(f"Sources not found for UUIDs: {', '.join(missing_ids)}")

        has_normalized_identifiers = table_exists(conn, "source_identifiers")

        results = []
        for source in sources:
            source_data = {
                "id": source["id"],
                "title": source["title"],
                "type": source["type"],
                "status": source["status"],
                "identifiers": json.loads(source["identifiers"]),
            }
            if has_provenance:
                source_data["provider"] = source["provider"]
                source_data["discovered_via"] = source["discovered_via"]
                source_data["discovered_at"] = source["discovered_at"]
            results.append(source_data)

        if has_normalized_identifiers:
            cursor.execute(
                f"""
                SELECT source_id, identifier_type, identifier_value
                FROM source_identifiers
                WHERE source_id IN ({placeholders})
                ORDER BY is_primary DESC, identifier_type ASC
                """,
                uuids,
            )
            identifiers_by_source: Dict[str, Dict[str, str]] = {}
            for row in cursor.fetchall():
                identifiers_by_source.setdefault(row["source_id"], {})[row["identifier_type"]] = row[
                    "identifier_value"
                ]
            for source_data in results:
                source_data["identifiers"] = identifiers_by_source.get(
                    source_data["id"], source_data["identifiers"]
                )

        cursor.execute(
            f"""
            SELECT source_id, note_title, content, created_at
            FROM source_notes
            WHERE source_id IN ({placeholders})
            ORDER BY created_at DESC
            """,
            uuids,
        )
        notes_by_source: Dict[str, List[Dict[str, Any]]] = {}
        for row in cursor.fetchall():
            notes_by_source.setdefault(row["source_id"], []).append(
                {
                    "title": row["note_title"],
                    "content": row["content"],
                    "created_at": row["created_at"],
                }
            )

        cursor.execute(
            f"""
            SELECT source_id, entity_name, relation_type, notes
            FROM source_entity_links
            WHERE source_id IN ({placeholders})
            """,
            uuids,
        )
        links_by_source: Dict[str, List[Dict[str, Any]]] = {}
        for row in cursor.fetchall():
            links_by_source.setdefault(row["source_id"], []).append(
                {
                    "entity_name": row["entity_name"],
                    "relation_type": row["relation_type"],
                    "notes": row["notes"],
                }
            )

        for source_data in results:
            source_id = source_data["id"]
            source_data["notes"] = notes_by_source.get(source_id, [])
            source_data["entity_links"] = links_by_source.get(source_id, [])

        return results
