from datetime import date
from decimal import Decimal

from app.ai.extraction.field_indexing import build_field_values
from app.domain.dtos import FieldDraft, FieldValueDraft


def _field(name, value, status="ok"):
    return FieldDraft(
        name=name, value=value, confidence="high", status=status, error=None, attempts=1
    )


def test_every_filterable_field_is_indexed():
    rows = build_field_values(
        [
            _field("policy_number", "FS-2024-001"),
            _field("tax_id", "b12345678"),
            _field("license_plate", "1234 bcd"),
            _field("holder", "Juan Pérez García"),
            _field("issuer", "Taller El Faro, S.L."),
            _field("invoice_amount", {"amount": "1250.50", "currency": "EUR"}),
            _field("invoice_date", "2025-03-15"),
            _field("document_date", "2025-01-02"),
            _field("validity", {"start": "2025-01-01", "end": "2025-12-31"}),
        ]
    )
    assert rows == [
        FieldValueDraft(field_name="policy_number", text_value="FS2024001"),
        FieldValueDraft(field_name="tax_id", text_value="B12345678"),
        FieldValueDraft(field_name="license_plate", text_value="1234BCD"),
        FieldValueDraft(field_name="holder", text_value="JUAN PEREZ GARCIA"),
        FieldValueDraft(field_name="issuer", text_value="TALLER EL FARO S L"),
        FieldValueDraft(
            field_name="invoice_amount", number_value=Decimal("1250.50"), currency="EUR"
        ),
        FieldValueDraft(
            field_name="invoice_date", date_from=date(2025, 3, 15), date_to=date(2025, 3, 15)
        ),
        FieldValueDraft(
            field_name="document_date", date_from=date(2025, 1, 2), date_to=date(2025, 1, 2)
        ),
        FieldValueDraft(
            field_name="validity", date_from=date(2025, 1, 1), date_to=date(2025, 12, 31)
        ),
    ]


def test_not_found_failed_and_non_filterable_fields_are_skipped():
    rows = build_field_values(
        [
            _field("policy_number", None, status="not_found"),
            _field("tax_id", None, status="failed"),
            _field("coverages", ["Robo"]),
            _field("summary", "Resumen"),
            _field("document_type", "policy"),
        ]
    )
    assert rows == []


def test_list_values_yield_one_row_each():
    rows = build_field_values([_field("holder", ["Ana", "Luis"])])
    assert [r.text_value for r in rows] == ["ANA", "LUIS"]


def test_malformed_value_is_skipped_with_a_warning(caplog):
    rows = build_field_values(
        [_field("invoice_date", "no es fecha"), _field("policy_number", "FS-1")]
    )
    assert [r.field_name for r in rows] == ["policy_number"]
    assert "field value not indexed" in caplog.text


def test_long_text_is_truncated():
    (row,) = build_field_values([_field("holder", "A" * 400)])
    assert len(row.text_value) == 255
