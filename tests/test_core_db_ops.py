import sqlite3


def test_add_source_note_identifier_status_and_entity_flow(server_module):
    add_results = server_module.add_sources.fn([
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
    ])

    assert add_results[0]["status"] == "success"
    source = add_results[0]["source"]
    assert source["title"] == "Attention Is All You Need"
    assert source["status"] == "unread"
    assert source["identifiers"] == {"arxiv": "1706.03762"}
    assert source["notes"][0]["title"] == "Initial thoughts"

    search_results = server_module.search_sources(
        [("Attention Is All You Need", "paper", "arxiv", "1706.03762")],
        server_module.DB_PATH,
    )
    assert search_results == [(source["id"], [])]

    note_results = server_module.add_notes.fn([
        (
            "Attention Is All You Need",
            "paper",
            "arxiv",
            "1706.03762",
            "Implementation details",
            "Scaled dot-product attention.",
        ),
    ])
    assert note_results[0]["status"] == "success"
    assert {note["title"] for note in note_results[0]["source"]["notes"]} == {
        "Initial thoughts",
        "Implementation details",
    }

    identifier_results = server_module.add_identifiers.fn([
        (
            "Attention Is All You Need",
            "paper",
            "arxiv",
            "1706.03762",
            "semantic_scholar",
            "204e3073870fae3d05bcbc2f6a8e263d9b72e776",
        ),
    ])
    assert identifier_results[0]["status"] == "success"
    assert identifier_results[0]["source"]["identifiers"]["semantic_scholar"].startswith("204e")

    status_results = server_module.update_status.fn([
        (
            "Attention Is All You Need",
            "paper",
            "arxiv",
            "1706.03762",
            "reading",
        ),
    ])
    assert status_results[0]["status"] == "success"
    assert status_results[0]["source"]["status"] == "reading"

    link_results = server_module.link_to_entities.fn([
        (
            "Attention Is All You Need",
            "paper",
            "arxiv",
            "1706.03762",
            "transformer",
            "introduces",
            "Original transformer paper.",
        ),
    ])
    assert link_results[0]["status"] == "success"
    assert link_results[0]["source"]["entity_links"][0]["entity_name"] == "transformer"

    source_entities = server_module.get_source_entities.fn([
        ("Attention Is All You Need", "paper", "arxiv", "1706.03762"),
    ])
    assert source_entities[0]["status"] == "success"
    assert source_entities[0]["source"]["entity_links"][0]["relation_type"] == "introduces"

    entity_sources = server_module.get_entity_sources.fn([
        ("transformer", "paper", "introduces"),
    ])
    assert entity_sources[0]["status"] == "success"
    assert entity_sources[0]["sources"][0]["id"] == source["id"]


def test_foreign_keys_are_enforced(server_module):
    with server_module.SQLiteConnection(server_module.DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO source_notes (source_id, note_title, content)
                VALUES (?, ?, ?)
                """,
                ("missing-source", "orphan", "should fail"),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("Expected foreign key enforcement to reject orphan note")
