"""Where the filters of a chat question came from."""

from enum import StrEnum


class FilterSource(StrEnum):
    """Where the filters of a question came from."""

    RULES = "rules"
    """The rules resolved everything: no LLM call."""
    LLM = "llm"
    """The rules left something unresolved and the LLM answered."""
    RULES_FALLBACK = "rules_fallback"
    """The LLM was needed but its answers were invalid: rule-based filters used."""
    EXPLICIT = "explicit"
    """The client sent the filters (for example, edited in the UI)."""
    DOCUMENT = "document"
    """The question is about one document: no filters are interpreted."""
