"""Reasons why the rule-based question parser needs the LLM."""

from enum import StrEnum


class Unresolved(StrEnum):
    """Reasons to hand the question to the LLM."""

    NEGATION = "negation"
    """A negation whose target the rules could not identify (``que no sea de Juan``)."""
    DATE = "date"
    """Date words the rules cannot resolve (``el lunes``, ``el trimestre pasado``)."""
    NAME = "name"
    """A person or company name (``de Juan Pérez``): holder or issuer is ambiguous."""
    REFERENCE = "reference"
    """A reference to earlier messages (``esa póliza``, ``¿y la de B?``)."""
