"""Constrained string types for chat filter values."""

from typing import Annotated

from pydantic import StringConstraints

FilterValue = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
"""One value of a filter: a non-empty text of at most 100 characters."""
