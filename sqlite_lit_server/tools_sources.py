import json
import sqlite3
import uuid
from typing import Any, Dict, List, Optional, Tuple

from .db import DB_PATH, SQLiteConnection
from .repository import get_sources_details, normalize_identifier_value, search_sources
from .schema import SourceIdentifiers, SourceStatus


def register_tools(mcp):
    @mcp.tool()
    def add_sources(
        sources: List[Tuple[str, str, str, str, Optional[Dict[str, str]]]]
    ) -> List[Dict[str, Any]]:
        """Add multiple new sources with duplicate checking."""
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Database not found at: {DB_PATH}")
        if not sources:
            return []

        search_inputs = [
            (title, type_, id_type, id_value)
            for title, type_, id_type, id_value, _ in sources
        ]
        search_results = search_sources(search_inputs, DB_PATH)

        results = [None] * len(sources)
        sources_to_add = []
        notes_to_add = []

        for input_index, ((title, type_, id_type, id_value, initial_note), (uuid_str, matches)) in enumerate(
            zip(sources, search_results)
        ):
            if uuid_str:
                try:
                    existing_source = get_sources_details(uuid_str, DB_PATH)[0]
                    results[input_index] = {
                        "status": "error",
                        "message": "Source already exists",
                        "existing_source": existing_source,
                    }
                except Exception as exc:
                    results[input_index] = {
                        "status": "error",
                        "message": f"Error retrieving existing source: {str(exc)}",
                    }
                continue

            if matches:
                results[input_index] = {
                    "status": "error",
                    "message": "Potential duplicates found. Please verify or use add_identifier if these are the same source.",
                    "matches": matches,
                }
                continue

            if initial_note and not all(k in initial_note for k in ("title", "content")):
                results[input_index] = {
                    "status": "error",
                    "message": f"Invalid initial note format for source '{title}'",
                }
                continue

            new_id = str(uuid.uuid4())
            sources_to_add.append(
                {
                    "input_index": input_index,
                    "id": new_id,
                    "title": title,
                    "type": type_,
                    "identifiers": json.dumps({id_type: id_value}),
                }
            )
            if initial_note:
                notes_to_add.append(
                    {
                        "input_index": input_index,
                        "source_id": new_id,
                        "note_title": initial_note["title"],
                        "content": initial_note["content"],
                    }
                )
            results[input_index] = {"status": "pending", "source_id": new_id}

        if sources_to_add:
            with SQLiteConnection(DB_PATH) as conn:
                cursor = conn.cursor()
                try:
                    cursor.executemany(
                        """
                        INSERT INTO sources (id, title, type, identifiers)
                        VALUES (:id, :title, :type, :identifiers)
                        """,
                        sources_to_add,
                    )
                    if notes_to_add:
                        cursor.executemany(
                            """
                            INSERT INTO source_notes (source_id, note_title, content)
                            VALUES (:source_id, :note_title, :content)
                            """,
                            notes_to_add,
                        )
                    cursor.executemany(
                        """
                        INSERT INTO source_identifiers (
                            source_id,
                            identifier_type,
                            identifier_value,
                            normalized_value,
                            is_primary
                        )
                        VALUES (:source_id, :identifier_type, :identifier_value, :normalized_value, :is_primary)
                        """,
                        [
                            {
                                "source_id": source["id"],
                                "identifier_type": next(iter(json.loads(source["identifiers"]).keys())),
                                "identifier_value": next(iter(json.loads(source["identifiers"]).values())),
                                "normalized_value": normalize_identifier_value(
                                    next(iter(json.loads(source["identifiers"]).keys())),
                                    next(iter(json.loads(source["identifiers"]).values())),
                                ),
                                "is_primary": 1,
                            }
                            for source in sources_to_add
                        ],
                    )
                    conn.commit()

                    details_by_id = {
                        source["id"]: source
                        for source in get_sources_details([source["id"] for source in sources_to_add], DB_PATH)
                    }
                    for source in sources_to_add:
                        results[source["input_index"]] = {
                            "status": "success",
                            "source": details_by_id[source["id"]],
                        }
                except sqlite3.Error as exc:
                    conn.rollback()
                    raise ValueError(f"Database error: {str(exc)}")

        return [result for result in results if result is not None]

    @mcp.tool()
    def add_notes(
        source_notes: List[Tuple[str, str, str, str, str, str]]
    ) -> List[Dict[str, Any]]:
        """Add notes to multiple sources in a single transaction."""
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Database not found at: {DB_PATH}")
        if not source_notes:
            return []

        search_inputs = [
            (title, type_, id_type, id_value)
            for title, type_, id_type, id_value, _, _ in source_notes
        ]
        search_results = search_sources(search_inputs, DB_PATH)

        results = [None] * len(source_notes)
        notes_to_add = []
        source_ids = []

        for input_index, ((title, type_, id_type, id_value, note_title, note_content), (uuid_str, matches)) in enumerate(
            zip(source_notes, search_results)
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

            notes_to_add.append(
                {
                    "input_index": input_index,
                    "source_id": uuid_str,
                    "note_title": note_title,
                    "content": note_content,
                }
            )
            source_ids.append(uuid_str)
            results[input_index] = {"status": "pending", "source_id": uuid_str}

        if notes_to_add:
            with SQLiteConnection(DB_PATH) as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        f"""
                        SELECT source_id, note_title
                        FROM source_notes
                        WHERE (source_id, note_title) IN
                        ({','.join('(?,?)' for _ in notes_to_add)})
                        """,
                        [val for note in notes_to_add for val in (note["source_id"], note["note_title"])],
                    )
                    existing_notes = {
                        (row["source_id"], row["note_title"])
                        for row in cursor.fetchall()
                    }

                    filtered_notes = []
                    for note in notes_to_add:
                        if (note["source_id"], note["note_title"]) in existing_notes:
                            results[note["input_index"]] = {
                                "status": "error",
                                "message": "Note with this title already exists for this source",
                            }
                        else:
                            filtered_notes.append(note)

                    if filtered_notes:
                        cursor.executemany(
                            """
                            INSERT INTO source_notes (source_id, note_title, content)
                            VALUES (:source_id, :note_title, :content)
                            """,
                            filtered_notes,
                        )
                        conn.commit()
                        source_details_by_id = {
                            source["id"]: source
                            for source in get_sources_details(list(set(source_ids)), DB_PATH)
                        }
                        for note in filtered_notes:
                            results[note["input_index"]] = {
                                "status": "success",
                                "source": source_details_by_id[note["source_id"]],
                            }
                except sqlite3.Error as exc:
                    conn.rollback()
                    raise ValueError(f"Database error: {str(exc)}")

        return [result for result in results if result is not None]

    @mcp.tool()
    def update_status(
        source_status: List[Tuple[str, str, str, str, str]]
    ) -> List[Dict[str, Any]]:
        """Update status for multiple sources in a single transaction."""
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Database not found at: {DB_PATH}")
        if not source_status:
            return []

        for _, _, _, _, status in source_status:
            if status not in SourceStatus.VALID_STATUS:
                raise ValueError(f"Invalid status. Must be one of: {SourceStatus.VALID_STATUS}")

        search_inputs = [
            (title, type_, id_type, id_value)
            for title, type_, id_type, id_value, _ in source_status
        ]
        search_results = search_sources(search_inputs, DB_PATH)

        results = []
        updates_to_make = []
        source_ids = []

        for (title, type_, id_type, id_value, new_status), (uuid_str, matches) in zip(
            source_status, search_results
        ):
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
            updates_to_make.append({"id": uuid_str, "status": new_status})
            source_ids.append(uuid_str)
            results.append({"status": "pending", "source_id": uuid_str})

        if updates_to_make:
            with SQLiteConnection(DB_PATH) as conn:
                cursor = conn.cursor()
                try:
                    cursor.executemany(
                        """
                        UPDATE sources
                        SET status = :status
                        WHERE id = :id
                        """,
                        updates_to_make,
                    )
                    conn.commit()
                    source_details = get_sources_details(list(set(source_ids)), DB_PATH)
                    for index, result in enumerate(results):
                        if result.get("status") == "pending":
                            source_id = result["source_id"]
                            source_detail = next(source for source in source_details if source["id"] == source_id)
                            results[index] = {"status": "success", "source": source_detail}
                except sqlite3.Error as exc:
                    conn.rollback()
                    raise ValueError(f"Database error: {str(exc)}")

        return results

    @mcp.tool()
    def add_identifiers(
        source_identifiers: List[Tuple[str, str, str, str, str, str]]
    ) -> List[Dict[str, Any]]:
        """Add new identifiers to multiple sources in a single transaction."""
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Database not found at: {DB_PATH}")
        if not source_identifiers:
            return []

        for _, _, _, _, new_type, _ in source_identifiers:
            if new_type not in SourceIdentifiers.VALID_TYPES:
                raise ValueError(
                    f"Invalid new identifier type. Must be one of: {SourceIdentifiers.VALID_TYPES}"
                )

        search_inputs = [
            (title, type_, current_type, current_value)
            for title, type_, current_type, current_value, _, _ in source_identifiers
        ]
        search_results = search_sources(search_inputs, DB_PATH)
        new_id_search_results = search_sources(
            [
                (f"Check {index}", type_, id_type, id_value)
                for index, (_, type_, _, _, id_type, id_value) in enumerate(source_identifiers)
            ],
            DB_PATH,
        )
        existing_new_ids = {
            (type_, id_type, id_value): uuid_str
            for (_, type_, _, _, id_type, id_value), (uuid_str, _) in zip(
                source_identifiers, new_id_search_results
            )
            if uuid_str
        }

        results = []
        updates_to_make = []
        source_ids = []

        for (title, type_, current_type, current_value, new_type, new_value), (uuid_str, matches) in zip(
            source_identifiers, search_results
        ):
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

            existing_source = existing_new_ids.get((type_, new_type, new_value))
            if existing_source and existing_source != uuid_str:
                try:
                    existing_details = get_sources_details(existing_source, DB_PATH)[0]
                    results.append(
                        {
                            "status": "error",
                            "message": "New identifier already exists on a different source",
                            "existing_source": existing_details,
                        }
                    )
                except Exception as exc:
                    results.append(
                        {
                            "status": "error",
                            "message": f"Error retrieving existing source: {str(exc)}",
                        }
                    )
                continue

            updates_to_make.append({"id": uuid_str, "new_type": new_type, "new_value": new_value})
            source_ids.append(uuid_str)
            results.append({"status": "pending", "source_id": uuid_str})

        if updates_to_make:
            with SQLiteConnection(DB_PATH) as conn:
                cursor = conn.cursor()
                try:
                    for update in updates_to_make:
                        cursor.execute(
                            """
                            INSERT INTO source_identifiers (
                                source_id,
                                identifier_type,
                                identifier_value,
                                normalized_value,
                                is_primary
                            )
                            VALUES (?, ?, ?, ?, 0)
                            ON CONFLICT(source_id, identifier_type) DO UPDATE SET
                                identifier_value = excluded.identifier_value,
                                normalized_value = excluded.normalized_value
                            """,
                            (
                                update["id"],
                                update["new_type"],
                                update["new_value"],
                                normalize_identifier_value(update["new_type"], update["new_value"]),
                            ),
                        )
                        cursor.execute(
                            """
                            UPDATE sources
                            SET identifiers = json_set(identifiers, :path, :value)
                            WHERE id = :id
                            """,
                            {
                                "id": update["id"],
                                "path": f"$.{update['new_type']}",
                                "value": update["new_value"],
                            },
                        )
                    conn.commit()
                    source_details = get_sources_details(list(set(source_ids)), DB_PATH)
                    for index, result in enumerate(results):
                        if result.get("status") == "pending":
                            source_id = result["source_id"]
                            source_detail = next(source for source in source_details if source["id"] == source_id)
                            results[index] = {"status": "success", "source": source_detail}
                except sqlite3.Error as exc:
                    conn.rollback()
                    raise ValueError(f"Database error: {str(exc)}")

        return results

    return {
        "add_sources": add_sources,
        "add_notes": add_notes,
        "update_status": update_status,
        "add_identifiers": add_identifiers,
    }
