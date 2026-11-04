"""Confidence level the LLM assigns to an extracted value."""

from enum import StrEnum


class Confidence(StrEnum):
    """Confidence level the LLM assigns to an extracted value."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
