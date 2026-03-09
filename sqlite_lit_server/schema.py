class SourceIdentifiers:
    """Defines valid identifier types for sources."""

    VALID_TYPES = {
        "semantic_scholar",
        "arxiv",
        "doi",
        "openalex",
        "pmid",
        "isbn",
        "url",
    }


class SourceTypes:
    """Defines valid source types."""

    VALID_TYPES = {"paper", "webpage", "book", "video", "blog"}


class SourceStatus:
    """Defines valid source status values."""

    VALID_STATUS = {"unread", "reading", "completed", "archived"}


class EntityRelations:
    """Defines valid relation types for entity links."""

    VALID_TYPES = {
        "discusses",
        "introduces",
        "extends",
        "evaluates",
        "applies",
        "critiques",
    }
