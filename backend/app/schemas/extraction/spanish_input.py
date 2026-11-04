"""Base model for the LLM extraction output: Spanish aliases on input, English names in code."""

from pydantic import BaseModel, ConfigDict


class SpanishInput(BaseModel):
    """Base model: Spanish aliases on input, English names in code."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore", str_strip_whitespace=True)
