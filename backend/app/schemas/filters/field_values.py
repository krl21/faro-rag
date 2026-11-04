"""Values of one field: a document matches if the field has ANY of them."""

from typing import Annotated

from pydantic import BeforeValidator, Field, model_validator

from app.domain.enums import DocumentType, FilterField
from app.schemas.filters.filter_model import FilterModel
from app.schemas.filters.types import FilterValue
from app.schemas.helpers import (
    document_type_from_spanish,
    filter_field_from_spanish,
    spanish_alias,
)


class FieldValues(FilterModel):
    """Values of one field: a document matches if the field has ANY of them.

    Attributes:
        field: Field to compare (``campo``), from a closed list.
        values: Accepted values (``valores``).
    """

    field: Annotated[FilterField, BeforeValidator(filter_field_from_spanish)] = Field(
        validation_alias=spanish_alias("field", "campo")
    )
    values: list[FilterValue] = Field(
        min_length=1, max_length=20, validation_alias=spanish_alias("values", "valores")
    )

    @model_validator(mode="after")
    def _valid_document_types(self) -> "FieldValues":
        """Translate and check the values of the ``document_type`` field.

        Returns:
            The validated values.

        Raises:
            ValueError: If a document type is unknown.
        """
        if self.field is FilterField.DOCUMENT_TYPE:
            translated = [str(document_type_from_spanish(v)) for v in self.values]
            allowed = {t.value for t in DocumentType}
            unknown = [v for v in translated if v not in allowed]
            if unknown:
                raise ValueError(f"unknown document types: {unknown}")
            self.values = translated
        return self
