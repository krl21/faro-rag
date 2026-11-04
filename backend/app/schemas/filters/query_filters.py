"""Every filter of a question. All of them are combined with AND."""

from typing import Annotated

from pydantic import BeforeValidator, Field

from app.domain.enums import DocumentType
from app.schemas.filters.amount_range import AmountRange
from app.schemas.filters.date_range import DateRange
from app.schemas.filters.field_values import FieldValues
from app.schemas.filters.filter_model import FilterModel
from app.schemas.helpers import document_type_from_spanish, none_to_empty, spanish_alias


class QueryFilters(FilterModel):
    """Every filter of a question. All of them are combined with AND.

    Attributes:
        document_type: Only this type (``tipo_documento``).
        uploaded: Upload date range in the configured time zone (``fecha_subida``).
        document_date: Date of the document: issue date, document date or a
            validity period that overlaps the range (``fecha_documento``).
        amount: Invoice amount range (``importe``).
        include: Each group must match (``incluir``).
        exclude: Documents matching any group are removed (``excluir``).
        query: What remains of the question for the semantic search
            (``consulta``); empty when the question only lists documents.
    """

    document_type: Annotated[DocumentType | None, BeforeValidator(document_type_from_spanish)] = (
        Field(default=None, validation_alias=spanish_alias("document_type", "tipo_documento"))
    )
    uploaded: DateRange | None = Field(
        default=None, validation_alias=spanish_alias("uploaded", "fecha_subida")
    )
    document_date: DateRange | None = Field(
        default=None, validation_alias=spanish_alias("document_date", "fecha_documento")
    )
    amount: AmountRange | None = Field(
        default=None, validation_alias=spanish_alias("amount", "importe")
    )
    include: list[FieldValues] = Field(
        default_factory=list, max_length=10, validation_alias=spanish_alias("include", "incluir")
    )
    exclude: list[FieldValues] = Field(
        default_factory=list, max_length=10, validation_alias=spanish_alias("exclude", "excluir")
    )
    query: Annotated[str, BeforeValidator(none_to_empty)] = Field(
        default="", max_length=1000, validation_alias=spanish_alias("query", "consulta")
    )

    @property
    def has_restrictions(self) -> bool:
        """Whether any filter restricts the documents.

        Returns:
            ``True`` if a type, date, amount, include or exclude filter is set.
        """
        return bool(
            self.document_type
            or self.uploaded
            or self.document_date
            or self.amount
            or self.include
            or self.exclude
        )
