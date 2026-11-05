"""Turn the extracted fields of a document into facts the LLM can cite."""

from collections.abc import Iterable
from typing import Any, Protocol

from app.domain.dtos import FieldFact
from app.domain.enums import FieldStatus

# Spanish label of each field shown to the LLM (fields not listed are not used).
_LABELS = {
    "policy_number": "Número de póliza",
    "validity": "Vigencia",
    "coverages": "Coberturas",
    "invoice_amount": "Importe total de la factura",
    "invoice_date": "Fecha de emisión de la factura",
    "holder": "Titular",
    "tax_id": "NIF",
    "license_plate": "Matrícula",
}
_WITH_VALUE = frozenset({FieldStatus.OK, FieldStatus.EDITED})


class _StoredField(Protocol):
    """What this module reads from an ``ExtractedField`` row."""

    name: str
    value: Any
    status: str
    page: int | None


class _DocumentWithFields(Protocol):
    """What this module reads from a ``Document`` with its fields loaded."""

    id: Any
    filename: str
    fields: Iterable[_StoredField]


def build_field_facts(document: _DocumentWithFields) -> list[FieldFact]:
    """Describe the extracted fields of a document as citable facts.

    Only fields with a value (``ok`` or ``edited``) are used; ``not_found``,
    ``failed`` and ``document_type`` are skipped.

    Args:
        document: Document with its fields loaded.

    Returns:
        One fact per usable field, in a stable order.
    """
    facts = []
    for field in sorted(document.fields, key=lambda f: f.name):
        label = _LABELS.get(field.name)
        if label is None or field.status not in _WITH_VALUE or field.value in (None, [], ""):
            continue
        facts.append(
            FieldFact(
                document_id=document.id,
                filename=document.filename,
                page=field.page,
                name=field.name,
                label=label,
                value=format_value(field.value),
                edited=field.status == FieldStatus.EDITED,
            )
        )
    return facts


def format_value(value: Any) -> str:
    """Render a stored JSON value as readable text.

    Args:
        value: Value from ``extracted_fields.value``.

    Returns:
        ``1250.50 EUR`` for amounts, ``del 2025-01-01 al 2025-12-31`` for
        periods, items joined with ``; `` for lists, and the text otherwise.
    """
    if isinstance(value, dict) and {"amount", "currency"} <= value.keys():
        return f"{value['amount']} {value['currency']}"
    if isinstance(value, dict) and {"start", "end"} <= value.keys():
        return f"del {value['start']} al {value['end']}"
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    return str(value)
