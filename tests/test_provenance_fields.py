import sqlite3


def test_sources_include_lightweight_provenance_fields(server_module):
    columns = []
    with sqlite3.connect(server_module.DB_PATH) as conn:
        columns = [
            row[1]
            for row in conn.execute("PRAGMA table_info(sources)").fetchall()
        ]

    assert {"provider", "discovered_via", "discovered_at"}.issubset(columns)

    add_result = server_module.add_sources.fn([
        ("Provenance Paper", "paper", "pmid", "12345678", None),
    ])[0]

    source = add_result["source"]
    assert source["provider"] is None
    assert source["discovered_via"] is None
    assert source["discovered_at"] is None
