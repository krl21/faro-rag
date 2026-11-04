"""Translation of the Spanish labels the LLM returns to English enums.

Plain functions so every schema can reuse them with ``BeforeValidator``
instead of repeating a ``field_validator`` method.
"""

from typing import Any

from app.domain.enums import Confidence, DocumentType, FilterField

CONFIDENCE_ES = {"baja": Confidence.LOW, "media": Confidence.MEDIUM, "alta": Confidence.HIGH}
"""Spanish confidence label (lower case) to its enum."""

DOCUMENT_TYPE_ES = {
    "poliza": DocumentType.POLICY,
    "póliza": DocumentType.POLICY,
    "polizas": DocumentType.POLICY,
    "pólizas": DocumentType.POLICY,
    "factura": DocumentType.INVOICE,
    "facturas": DocumentType.INVOICE,
    "otro": DocumentType.OTHER,
    "otros": DocumentType.OTHER,
}
"""Spanish document type label (lower case, singular or plural) to its enum."""

FIELD_ES = {
    "tipo_documento": FilterField.DOCUMENT_TYPE,
    "numero_poliza": FilterField.POLICY_NUMBER,
    "titular": FilterField.HOLDER,
    "nif": FilterField.TAX_ID,
    "matricula": FilterField.LICENSE_PLATE,
    "emisor": FilterField.ISSUER,
}
"""Spanish filter field key to its enum."""


def translate(value: Any, mapping: dict[str, Any]) -> Any:
    """Translate a Spanish label to its English enum, leaving other values as-is.

    Args:
        value: Raw value from the LLM or the API.
        mapping: Spanish label (lower-case) to enum member.

    Returns:
        The enum member when ``value`` is a known Spanish label; otherwise the
        stripped, lower-cased string, or ``value`` itself if it is not a string.
    """
    if isinstance(value, str):
        key = value.strip().lower()
        return mapping.get(key, key)
    return value


def confidence_from_spanish(value: Any) -> Any:
    """Map ``baja``/``media``/``alta`` to ``low``/``medium``/``high``.

    Args:
        value: Raw confidence.

    Returns:
        The translated confidence.
    """
    return translate(value, CONFIDENCE_ES)


def document_type_from_spanish(value: Any) -> Any:
    """Map ``poliza``/``factura``/``otro`` (singular or plural) to the English enum.

    Args:
        value: Raw document type.

    Returns:
        The translated type.
    """
    return translate(value, DOCUMENT_TYPE_ES)


def filter_field_from_spanish(value: Any) -> Any:
    """Map a Spanish filter field key (``numero_poliza``...) to the English enum.

    Args:
        value: Raw field.

    Returns:
        The translated field.
    """
    return translate(value, FIELD_ES)
