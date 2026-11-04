"""Filters of a chat question and how they were obtained."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.domain.enums import FilterSource, Unresolved

if TYPE_CHECKING:
    from app.schemas.filters import QueryFilters


@dataclass(frozen=True)
class InterpretedQuery:
    """Filters of a question and how they were obtained.

    Attributes:
        filters: Filters to apply.
        source: Where they came from.
        unresolved: What the rules could not resolve.
    """

    filters: QueryFilters
    source: FilterSource
    unresolved: list[Unresolved] = field(default_factory=list)
