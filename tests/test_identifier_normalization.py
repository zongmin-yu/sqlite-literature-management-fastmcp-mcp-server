import sqlite3


def test_identifiers_are_stored_in_normalized_table_and_searchable(server_module):
    add_result = server_module.add_sources.fn([
        ("Normalization Paper", "paper", "doi", "10.1000/ABC", None),
    ])[0]
    source = add_result["source"]

    with sqlite3.connect(server_module.DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT identifier_type, identifier_value, normalized_value, is_primary
            FROM source_identifiers
            WHERE source_id = ?
            """,
            [source["id"]],
        ).fetchone()

    assert row == ("doi", "10.1000/ABC", "10.1000/abc", 1)

    search_results = server_module.search_sources(
        [("Normalization Paper", "paper", "doi", "10.1000/abc")],
        server_module.DB_PATH,
    )
    assert search_results == [(source["id"], [])]


def test_new_identifier_types_are_supported(server_module):
    result = server_module.add_sources.fn([
        ("OpenAlex Import", "paper", "openalex", "W1234567890", None),
    ])[0]
    assert result["status"] == "success"
    assert result["source"]["identifiers"] == {"openalex": "W1234567890"}
