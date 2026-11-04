from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.ai.extraction.specs import FIELD_SPECS
from app.domain.enums import Confidence, DocumentType
from app.schemas.extraction import Classification, Money, Validity


def _spec(document_type: DocumentType, name: str):
    return next(s for s in FIELD_SPECS[document_type] if s.name == name)


def test_spanish_confidence_is_translated():
    spec = _spec(DocumentType.POLICY, "policy_number")
    value = spec.adapter.validate_python({"valor": "FS-1", "confianza": "media"})
    assert value.value == "FS-1"
    assert value.confidence is Confidence.MEDIUM


def test_unknown_confidence_is_rejected():
    spec = _spec(DocumentType.POLICY, "policy_number")
    with pytest.raises(ValidationError):
        spec.adapter.validate_python({"valor": "FS-1", "confianza": "segura"})


def test_classification_translates_spanish_type():
    result = Classification.model_validate({"tipo": "factura", "confianza": "alta"})
    assert result.document_type is DocumentType.INVOICE
    assert result.confidence is Confidence.HIGH


def test_validity_rejects_end_before_start():
    with pytest.raises(ValidationError):
        Validity.model_validate({"inicio": "2025-12-31", "fin": "2025-01-01"})


def test_validity_parses_iso_dates():
    validity = Validity.model_validate({"inicio": "2025-01-01", "fin": "2025-12-31"})
    assert validity.start.year == 2025
    assert validity.end.month == 12


def test_money_normalizes_currency_and_rejects_negative():
    money = Money.model_validate({"importe": "1250.50", "moneda": "eur"})
    assert money.amount == Decimal("1250.50")
    assert money.currency == "EUR"
    with pytest.raises(ValidationError):
        Money.model_validate({"importe": "-1", "moneda": "EUR"})


def test_money_rejects_invalid_currency():
    with pytest.raises(ValidationError):
        Money.model_validate({"importe": "10", "moneda": "euros"})


def test_coverages_reject_empty_strings():
    spec = _spec(DocumentType.POLICY, "coverages")
    with pytest.raises(ValidationError):
        spec.adapter.validate_python({"valor": ["Robo", ""], "confianza": "alta"})


def test_values_are_dumped_with_english_keys():
    spec = _spec(DocumentType.POLICY, "validity")
    value = spec.adapter.validate_python(
        {"valor": {"inicio": "2025-01-01", "fin": "2025-12-31"}, "confianza": "alta"}
    )
    dumped = spec.adapter.dump_python(value, mode="json")
    assert dumped["value"] == {"start": "2025-01-01", "end": "2025-12-31"}
    assert dumped["confidence"] == "high"


@pytest.mark.parametrize("bad_date", ["31/12/2025", "2025-13-01", "mañana"])
def test_validity_rejects_non_iso_dates(bad_date):
    with pytest.raises(ValidationError):
        Validity.model_validate({"inicio": bad_date, "fin": "2026-01-01"})


def test_money_rejects_more_than_two_decimals():
    with pytest.raises(ValidationError):
        Money.model_validate({"importe": "10.555", "moneda": "EUR"})


@pytest.mark.parametrize(
    "label", ["desconocido", "Desconocido", "otro", "contrato", "carta", "nómina"]
)
def test_any_type_that_is_not_policy_or_invoice_is_unknown(label):
    result = Classification.model_validate({"tipo": label, "confianza": "alta"})
    assert result.document_type is DocumentType.UNKNOWN


@pytest.mark.parametrize(
    ("label", "expected"), [("poliza", "policy"), ("Póliza", "policy"), ("factura", "invoice")]
)
def test_known_types_keep_their_value(label, expected):
    assert (
        Classification.model_validate({"tipo": label, "confianza": "alta"}).document_type
        == expected
    )


@pytest.mark.parametrize(
    "data",
    [{"confianza": "alta"}, {"tipo": None, "confianza": "alta"}, {"tipo": 3, "confianza": "alta"}],
)
def test_missing_or_non_text_type_is_still_rejected(data):
    with pytest.raises(ValidationError):
        Classification.model_validate(data)


def test_otro_is_not_a_document_type_label():
    from app.schemas.helpers import DOCUMENT_TYPE_ES

    assert "otro" not in DOCUMENT_TYPE_ES


def test_english_names_are_also_accepted():
    result = Classification.model_validate({"document_type": "policy", "confidence": "low"})
    assert result.document_type is DocumentType.POLICY


def test_too_long_policy_number_is_rejected():
    spec = _spec(DocumentType.POLICY, "policy_number")
    with pytest.raises(ValidationError):
        spec.adapter.validate_python({"valor": "X" * 65, "confianza": "alta"})


def test_value_may_be_null_when_absent():
    spec = _spec(DocumentType.INVOICE, "invoice_amount")
    value = spec.adapter.validate_python({"valor": None, "confianza": "baja"})
    assert value.value is None
    assert value.confidence is Confidence.LOW
