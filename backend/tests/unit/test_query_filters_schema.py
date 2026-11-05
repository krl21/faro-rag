from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.enums import DocumentType, FilterField
from app.schemas.filters import AmountRange, DateRange, FieldValues, QueryFilters

SPANISH = {
    "tipo_documento": "factura",
    "fecha_subida": {"desde": "2026-11-02", "hasta": "2026-11-02"},
    "fecha_documento": None,
    "importe": {"minimo": 100, "maximo": "200.50", "moneda": "eur"},
    "incluir": [{"campo": "numero_poliza", "valores": ["A", "B"]}],
    "excluir": [{"campo": "tipo_documento", "valores": ["poliza"]}],
    "consulta": "",
}


def test_spanish_llm_output_is_translated():
    filters = QueryFilters.model_validate(SPANISH)
    assert filters.document_type is DocumentType.INVOICE
    assert filters.uploaded == DateRange(start=date(2026, 11, 2), end=date(2026, 11, 2))
    assert filters.amount == AmountRange(min=Decimal(100), max=Decimal("200.50"), currency="EUR")
    assert filters.include == [FieldValues(field=FilterField.POLICY_NUMBER, values=["A", "B"])]
    assert filters.exclude[0].values == ["policy"]


def test_output_uses_english_names_and_round_trips():
    filters = QueryFilters.model_validate(SPANISH)
    dumped = filters.model_dump(mode="json")
    assert set(dumped) == {
        "document_type",
        "uploaded",
        "document_date",
        "amount",
        "include",
        "exclude",
        "query",
    }
    assert QueryFilters.model_validate(dumped) == filters


def test_empty_filters_have_no_restrictions():
    assert not QueryFilters().has_restrictions
    assert not QueryFilters(query="deducible").has_restrictions
    assert QueryFilters(document_type="policy").has_restrictions


def test_null_query_is_empty_and_unknown_keys_are_ignored():
    filters = QueryFilters.model_validate({"consulta": None, "otra_cosa": 1})
    assert filters.query == ""


@pytest.mark.parametrize(
    "data",
    [
        {"fecha_subida": {}},
        {"fecha_subida": {"desde": "2026-02-01", "hasta": "2026-01-01"}},
        {"fecha_documento": {"desde": "ayer"}},
        {"importe": {}},
        {"importe": {"minimo": 10, "maximo": 5}},
        {"importe": {"minimo": -1}},
        {"importe": {"minimo": 1, "moneda": "EURO"}},
        {"incluir": [{"campo": "contraseña", "valores": ["x"]}]},
        {"incluir": [{"campo": "numero_poliza", "valores": []}]},
        {"incluir": [{"campo": "numero_poliza", "valores": [""]}]},
        {"incluir": [{"campo": "tipo_documento", "valores": ["contrato"]}]},
        {"tipo_documento": "contrato"},
        {"incluir": [{"campo": "nif", "valores": ["x" * 101]}]},
        {"incluir": [{"campo": "nif", "valores": [str(i) for i in range(21)]}]},
    ],
)
def test_invalid_filters_are_rejected(data):
    with pytest.raises(ValidationError):
        QueryFilters.model_validate(data)


@pytest.mark.parametrize(
    ("spanish", "field"),
    [
        ("numero_poliza", FilterField.POLICY_NUMBER),
        ("titular", FilterField.HOLDER),
        ("nif", FilterField.TAX_ID),
        ("matricula", FilterField.LICENSE_PLATE),
        ("emisor", FilterField.ISSUER),
        ("tipo_documento", FilterField.DOCUMENT_TYPE),
    ],
)
def test_every_spanish_field_is_accepted(spanish, field):
    values = ["factura"] if field is FilterField.DOCUMENT_TYPE else ["X"]
    assert FieldValues.model_validate({"campo": spanish, "valores": values}).field is field
