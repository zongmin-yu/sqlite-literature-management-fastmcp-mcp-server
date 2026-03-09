import asyncio
import json


def _read_resource_text(server_module, uri: str) -> str:
    contents = asyncio.run(server_module.mcp._read_resource_mcp(uri))
    text = getattr(contents[0], "content", None)
    if text is None:
        raise AssertionError(f"Expected text resource content for {uri}")
    return text


def test_resource_uris_return_expected_source_views(server_module):
    add_result = server_module.add_sources.fn([
        (
            "Resourceful Paper",
            "paper",
            "arxiv",
            "2501.00001",
            {"title": "Context", "content": "Useful resource payload."},
        ),
    ])[0]
    source = add_result["source"]

    server_module.link_to_entities.fn([
        (
            "Resourceful Paper",
            "paper",
            "arxiv",
            "2501.00001",
            "transformer",
            "discusses",
            "Linked for resource testing.",
        ),
    ])
    server_module.update_status.fn([
        ("Resourceful Paper", "paper", "arxiv", "2501.00001", "reading"),
    ])

    source_payload = json.loads(_read_resource_text(server_module, f"source://{source['id']}"))
    assert source_payload["title"] == "Resourceful Paper"
    assert source_payload["entity_links"][0]["entity_name"] == "transformer"

    identifier_payload = json.loads(
        _read_resource_text(server_module, "source://by-identifier/arxiv/2501.00001")
    )
    assert identifier_payload["id"] == source["id"]

    unread_payload = json.loads(_read_resource_text(server_module, "reading-list://unread"))
    assert unread_payload == []

    reading_payload = json.loads(_read_resource_text(server_module, "reading-list://reading"))
    assert reading_payload[0]["id"] == source["id"]

    entity_payload = json.loads(_read_resource_text(server_module, "entity://transformer"))
    assert entity_payload["sources"][0]["id"] == source["id"]
