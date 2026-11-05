"""Body of ``PATCH /documents/{id}/facts/{fact_id}``."""

from pydantic import BaseModel, model_validator


class FactUpdateRequest(BaseModel):
    """New label and/or value of a free datum, typed by the user.

    Attributes:
        label: New label; ``None`` keeps the current one.
        value: New value: a string, or for a table row an object with its
            columns (``{"Concepto": "Kit", "Importe": "1.280,00 €"}``);
            ``None`` keeps the current one.
    """

    label: str | None = None
    value: str | dict[str, str] | None = None

    @model_validator(mode="after")
    def _something_to_change(self) -> "FactUpdateRequest":
        """Reject a body without label nor value.

        Returns:
            The request.

        Raises:
            ValueError: If both are missing.
        """
        if self.label is None and self.value is None:
            raise ValueError("Send a new label, a new value or both")
        return self
