"""Typed filter columns computed for each extracted field."""

from datetime import date
from decimal import Decimal

import pytest

from app.ai.extraction.field_indexing import filter_columns, with_filter_columns
from app.domain.dtos import FieldDraft, FilterColumns


def _field(name, value, status="ok"):
    return FieldDraft(
        name=name, value=value, confidence="high", status=status, error=None, attempts=1
    )


@pytest.mark.parametrize(
    ("name", "value", "expected"),
    [
        ("policy_number", "FS-2024-001", FilterColumns(text_value="FS2024001")),
        ("tax_id", "b12345678", FilterColumns(text_value="B12345678")),
        ("license_plate", "1234 bcd", FilterColumns(text_value="1234BCD")),
        ("holder", "Juan Pérez García", FilterColumns(text_value="JUAN PEREZ GARCIA")),
        (
            "invoice_amount",
            {"amount": "1250.50", "currency": "EUR"},
            FilterColumns(number_value=Decimal("1250.50"), currency="EUR"),
        ),
        (
            "invoice_date",
            "2025-03-15",
            FilterColumns(date_from=date(2025, 3, 15), date_to=date(2025, 3, 15)),
        ),
        (
            "validity",
            {"start": "2025-01-01", "end": "2025-12-31"},
            FilterColumns(date_from=date(2025, 1, 1), date_to=date(2025, 12, 31)),
        ),
    ],
)
def test_filterable_fields_get_their_typed_columns(name, value, expected):
    assert filter_columns(_field(name, value)) == expected


def test_edited_fields_are_filterable_too():
    assert filter_columns(_field("policy_number", "FS-9", status="edited")) == FilterColumns(
        text_value="FS9"
    )


@pytest.mark.parametrize(
    "field",
    [
        _field("policy_number", None, status="not_found"),
        _field("tax_id", "B1", status="failed"),
        _field("coverages", ["Robo"]),
        _field("document_type", "policy"),
    ],
)
def test_fields_without_filter_columns(field):
    assert filter_columns(field) is None


def test_list_values_are_not_indexed(caplog):
    assert filter_columns(_field("holder", ["Ana", "Luis"])) is None
    assert "field value not indexed" in caplog.text


def test_malformed_value_is_skipped_with_a_warning(caplog):
    assert filter_columns(_field("invoice_date", "no es fecha")) is None
    assert "field value not indexed" in caplog.text


def test_long_text_is_truncated():
    assert len(filter_columns(_field("holder", "A" * 400)).text_value) == 255


def test_with_filter_columns_keeps_every_field():
    fields = with_filter_columns([_field("policy_number", "FS-1"), _field("coverages", ["Robo"])])
    assert [f.name for f in fields] == ["policy_number", "coverages"]
    assert fields[0].filter_columns == FilterColumns(text_value="FS1")
    assert fields[1].filter_columns is None
