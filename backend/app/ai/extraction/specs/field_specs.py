"""Which fields are extracted for each document type, and how they are validated."""

from datetime import date

from pydantic import TypeAdapter

from app.ai.extraction.specs.field_spec import FieldSpec
from app.domain.enums import DocumentType, FieldValueType
from app.schemas.extraction import (
    ExtractedValue,
    Identifier,
    Money,
    PolicyNumber,
    ShortText,
    Validity,
)


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
    # Documents that are neither a policy nor an invoice are not used by the chat:
    # no fields, no chunks.
    DocumentType.OTHER: (),
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
