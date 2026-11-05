"""Result of the rule-based question parser."""

from dataclasses import dataclass, field

from app.domain.enums import Unresolved
from app.schemas.filters import QueryFilters


@dataclass(frozen=True)
class RuleParse:
    """Result of the rule-based parser.

    Attributes:
        filters: Filters recognized with certainty.
        unresolved: Why the LLM is needed; empty when the rules are enough.
    """

    filters: QueryFilters
    unresolved: list[Unresolved] = field(default_factory=list)
