"""Pages a question about one document is restricted to."""

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class PageRangeIn(BaseModel):
    """Inclusive range of 1-based pages; either end may be omitted.

    Attributes:
        start: First page (``from`` in JSON).
        end: Last page (``to`` in JSON).
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    start: int | None = Field(
        default=None,
        ge=1,
        validation_alias=AliasChoices("from", "start"),
        serialization_alias="from",
    )
    end: int | None = Field(
        default=None, ge=1, validation_alias=AliasChoices("to", "end"), serialization_alias="to"
    )

    @model_validator(mode="after")
    def _ordered(self) -> "PageRangeIn":
        """Reject ranges whose first page is after the last one.

        Returns:
            The validated range.

        Raises:
            ValueError: If ``from`` is greater than ``to``.
        """
        if self.start is not None and self.end is not None and self.start > self.end:
            raise ValueError("'from' is greater than 'to'")
        return self
