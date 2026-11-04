"""Which fields are extracted for each document type, and how they are validated."""

from dataclasses import dataclass
from datetime import date

from pydantic import TypeAdapter

from app.domain.enums import DocumentType, FieldValueType
from app.schemas.extraction import (
    ExtractedValue,
    Identifier,
    LongText,
    Money,
    PolicyNumber,
    ShortText,
    Validity,
)


@dataclass(frozen=True)
class FieldSpec:
    """Definition of one extractable field.

    Attributes:
        name: English name stored in the database and exposed by the API.
        key: Spanish key the LLM uses in its JSON answer.
        adapter: Pydantic adapter that validates the ``{valor, confianza}`` object.
        value_adapter: Pydantic adapter that validates a bare value, as the
            API returns it (used when the user edits a field).
        value_type: Shape of the value, so the UI can pick the editor.
    """

    name: str
    key: str
    adapter: TypeAdapter
    value_adapter: TypeAdapter
    value_type: FieldValueType


def _spec(name: str, key: str, python_type: object, value_type: FieldValueType) -> FieldSpec:
    """Build a ``FieldSpec`` for a value type.

    Args:
        name: English field name.
        key: Spanish JSON key.
        python_type: Type of the ``valor`` attribute.
        value_type: Shape of the value exposed to the UI.

    Returns:
        The field specification.
    """
    return FieldSpec(
        name=name,
        key=key,
        adapter=TypeAdapter(ExtractedValue[python_type]),
        value_adapter=TypeAdapter(python_type),
        value_type=value_type,
    )


_POLICY_NUMBER = _spec("policy_number", "numero_poliza", PolicyNumber, FieldValueType.TEXT)

COMMON_FIELD_SPECS: tuple[FieldSpec, ...] = (
    _spec("holder", "titular", ShortText, FieldValueType.TEXT),
    _spec("tax_id", "nif", Identifier, FieldValueType.TEXT),
    _spec("license_plate", "matricula", Identifier, FieldValueType.TEXT),
)
"""Fields asked for in every document type so the chat can always filter by them.

They are few on purpose: each one costs tokens in every extraction. A field
the document does not contain is stored as ``not_found``, not as an error.
"""

FIELD_SPECS: dict[DocumentType, tuple[FieldSpec, ...]] = {
    DocumentType.POLICY: (
        _POLICY_NUMBER,
        _spec("validity", "vigencia", Validity, FieldValueType.PERIOD),
        _spec("coverages", "coberturas", list[ShortText], FieldValueType.TEXT_LIST),
        *COMMON_FIELD_SPECS,
    ),
    DocumentType.INVOICE: (
        _spec("invoice_amount", "monto_factura", Money, FieldValueType.MONEY),
        _spec("invoice_date", "fecha_factura", date, FieldValueType.DATE),
        _POLICY_NUMBER,
        *COMMON_FIELD_SPECS,
    ),
    DocumentType.OTHER: (
        _spec("title", "titulo", ShortText, FieldValueType.TEXT),
        _spec("document_date", "fecha", date, FieldValueType.DATE),
        _spec("issuer", "emisor", ShortText, FieldValueType.TEXT),
        _spec("entities", "entidades", list[ShortText], FieldValueType.TEXT_LIST),
        _spec("summary", "resumen", LongText, FieldValueType.LONG_TEXT),
        *COMMON_FIELD_SPECS,
    ),
}
"""Fields extracted per document type, in display order."""


def find_spec(document_type: str | None, name: str) -> FieldSpec | None:
    """Find the definition of a field of a document type.

    Args:
        document_type: Stored document type (``policy``, ``invoice``...), or ``None``.
        name: English field name.

    Returns:
        The field specification, or ``None`` if the type does not have that
        field (``document_type`` itself has no specification).
    """
    try:
        specs = FIELD_SPECS[DocumentType(document_type)]
    except ValueError:
        return None
    return next((spec for spec in specs if spec.name == name), None)
