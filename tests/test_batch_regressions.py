def add_source(server_module, title: str, identifier_value: str):
    result = server_module.add_sources.fn([
        (title, "paper", "arxiv", identifier_value, None),
    ])[0]
    assert result["status"] == "success"
    return result["source"]


def test_invalid_initial_note_does_not_insert_source(server_module):
    results = server_module.add_sources.fn([
        (
            "Broken Source",
            "paper",
            "arxiv",
            "9999.00001",
            {"title": "missing content"},
        ),
    ])

    assert results == [{
        "status": "error",
        "message": "Invalid initial note format for source 'Broken Source'",
    }]
    assert server_module.search_sources(
        [("Broken Source", "paper", "arxiv", "9999.00001")],
        server_module.DB_PATH,
    ) == [(None, [])]


def test_add_notes_preserves_result_order_for_duplicate_errors(server_module):
    add_source(server_module, "Existing Source", "1111.11111")
    server_module.add_notes.fn([
        ("Existing Source", "paper", "arxiv", "1111.11111", "Summary", "first"),
    ])

    results = server_module.add_notes.fn([
        ("Missing Source", "paper", "arxiv", "0000.00000", "Missing", "nope"),
        ("Existing Source", "paper", "arxiv", "1111.11111", "Summary", "duplicate"),
    ])

    assert results[0] == {"status": "error", "message": "Source not found"}
    assert results[1] == {
        "status": "error",
        "message": "Note with this title already exists for this source",
    }


def test_link_to_entities_preserves_result_order_for_duplicate_errors(server_module):
    add_source(server_module, "Entity Source", "2222.22222")
    server_module.link_to_entities.fn([
        ("Entity Source", "paper", "arxiv", "2222.22222", "transformer", "introduces", None),
    ])

    results = server_module.link_to_entities.fn([
        ("Missing Source", "paper", "arxiv", "0000.00000", "transformer", "introduces", None),
        ("Entity Source", "paper", "arxiv", "2222.22222", "transformer", "introduces", None),
    ])

    assert results[0] == {"status": "error", "message": "Source not found"}
    assert results[1] == {
        "status": "error",
        "message": "Link already exists between this source and entity",
    }


def test_update_entity_links_matches_errors_by_source_and_entity(server_module):
    add_source(server_module, "Update Source", "3333.33333")
    server_module.link_to_entities.fn([
        ("Update Source", "paper", "arxiv", "3333.33333", "transformer", "introduces", "before"),
    ])

    results = server_module.update_entity_links.fn([
        ("Update Source", "paper", "arxiv", "3333.33333", "transformer", "extends", None),
        ("Update Source", "paper", "arxiv", "3333.33333", "attention", "evaluates", None),
    ])

    assert results[0]["status"] == "success"
    updated_links = {link["entity_name"]: link for link in results[0]["source"]["entity_links"]}
    assert updated_links["transformer"]["relation_type"] == "extends"
    assert results[1] == {
        "status": "error",
        "message": "No link found between this source and entity",
    }


def test_remove_entity_links_reports_mixed_batches_correctly(server_module):
    add_source(server_module, "Removal Source", "4444.44444")
    server_module.link_to_entities.fn([
        ("Removal Source", "paper", "arxiv", "4444.44444", "transformer", "introduces", None),
    ])

    results = server_module.remove_entity_links.fn([
        ("Removal Source", "paper", "arxiv", "4444.44444", "transformer"),
        ("Removal Source", "paper", "arxiv", "4444.44444", "attention"),
    ])

    assert results[0]["status"] == "success"
    assert results[0]["source"]["entity_links"] == []
    assert results[1] == {
        "status": "error",
        "message": "No link found between this source and entity",
    }
