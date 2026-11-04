"""Base model for the chat filters: Spanish or English input, English output."""

from pydantic import BaseModel, ConfigDict


class FilterModel(BaseModel):
    """Base model: Spanish or English input, English output, unknown keys ignored."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore", str_strip_whitespace=True)
