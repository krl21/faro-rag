"""Rule-based parser: the cases discussed plus edge cases. Today is 2026-11-03."""

from datetime import date
from decimal import Decimal

import pytest

from app.ai.query.negation import find_negations
from app.ai.query.rule_parser import parse_with_rules
from app.ai.query.scanner import QuestionScanner
from app.domain.enums import DocumentType, FilterField, Unresolved
from app.schemas.filters import DateRange, FieldValues

TODAY = date(2026, 11, 3)


def _parse(question: str, has_history: bool = False):
    return parse_with_rules(question, TODAY, has_history=has_history)


def test_invoices_saved_yesterday_is_a_listing():
    result = _parse("necesito las facturas guardadas ayer")
    assert result.filters.document_type is DocumentType.INVOICE
    assert result.filters.uploaded == DateRange(start=date(2026, 11, 2), end=date(2026, 11, 2))
    assert result.filters.query == ""
    assert result.unresolved == []


def test_values_as_policies():
    result = _parse("quiero lo que tengan A, B, C como pólizas")
    assert result.filters.include == [
        FieldValues(field=FilterField.POLICY_NUMBER, values=["A", "B", "C"])
    ]
    assert result.unresolved == []


def test_negated_policy_is_excluded():
    result = _parse("no quiero la que sea de póliza S")
    assert result.filters.exclude == [FieldValues(field=FilterField.POLICY_NUMBER, values=["S"])]
    assert result.filters.include == []
    assert result.unresolved == []


@pytest.mark.parametrize("trigger", ["excepto", "salvo", "menos", "sin", "aparte de"])
def test_negation_words(trigger):
    result = _parse(f"pólizas {trigger} la FS-2024-001")
    assert result.filters.exclude == [
        FieldValues(field=FilterField.POLICY_NUMBER, values=["FS-2024-001"])
    ]


def test_negation_ends_with_the_clause():
    result = _parse("no la póliza FS-1, pero sí la póliza FS-2")
    assert result.filters.exclude == [FieldValues(field=FilterField.POLICY_NUMBER, values=["FS-1"])]
    assert result.filters.include == [FieldValues(field=FilterField.POLICY_NUMBER, values=["FS-2"])]


def test_excluded_document_type():
    result = _parse("documentos subidos la semana pasada excepto facturas")
    assert result.filters.exclude == [
        FieldValues(field=FilterField.DOCUMENT_TYPE, values=["invoice"])
    ]
    assert result.filters.document_type is None


def test_amount_with_less_than_is_not_a_negation():
    result = _parse("facturas de menos de 500 €")
    assert result.filters.amount.max == Decimal(500)
    assert result.filters.exclude == []
    assert result.unresolved == []


def test_content_question_keeps_a_query_and_its_filters():
    result = _parse("¿cuál es el deducible de la póliza FS-2024-001?")
    assert result.filters.include == [
        FieldValues(field=FilterField.POLICY_NUMBER, values=["FS-2024-001"])
    ]
    assert "deducible" in result.filters.query
    assert "FS-2024-001" not in result.filters.query


def test_question_without_filters():
    result = _parse("¿Qué cubre la asistencia en carretera?")
    assert not result.filters.has_restrictions
    assert result.filters.query == "¿Qué cubre la asistencia en carretera?"


def test_two_types_become_an_include_group():
    result = _parse("pólizas y facturas de hoy")
    assert result.filters.document_type is None
    assert result.filters.include == [
        FieldValues(field=FilterField.DOCUMENT_TYPE, values=["policy", "invoice"])
    ]


def test_policies_in_force_today():
    result = _parse("pólizas vigentes")
    assert result.filters.document_date == DateRange(start=TODAY, end=TODAY)


def test_everything_together():
    result = _parse("facturas emitidas en marzo de más de 1000 € de la matrícula 1234-BCD")
    filters = result.filters
    assert filters.document_type is DocumentType.INVOICE
    assert filters.document_date == DateRange(start=date(2026, 3, 1), end=date(2026, 3, 31))
    assert filters.amount.min == Decimal(1000)
    assert filters.include == [FieldValues(field=FilterField.LICENSE_PLATE, values=["1234-BCD"])]
    assert filters.query == ""


@pytest.mark.parametrize(
    ("question", "reason"),
    [
        ("no quiero la de S", Unresolved.NEGATION),
        ("no quiero las facturas de ayer", Unresolved.NEGATION),
        ("facturas del lunes", Unresolved.DATE),
        ("pólizas de Juan Pérez", Unresolved.NAME),
        ("facturas emitidas por Taller Faro", Unresolved.NAME),
    ],
)
def test_unresolved_cases_ask_for_the_llm(question, reason):
    assert reason in _parse(question).unresolved


def test_negated_date_is_not_applied_as_a_filter():
    result = _parse("no quiero las facturas de ayer")
    assert result.filters.uploaded is None


@pytest.mark.parametrize("question", ["¿y la de B?", "¿y esa póliza?", "dame también las otras"])
def test_references_need_the_llm_only_with_history(question):
    assert Unresolved.REFERENCE in _parse(question, has_history=True).unresolved
    assert Unresolved.REFERENCE not in _parse(question, has_history=False).unresolved


def test_negation_scope_positions():
    (scope,) = find_negations(QuestionScanner("pólizas excepto la S. Y facturas"))
    text = "pólizas excepto la S. Y facturas"
    assert text[scope.trigger_start : scope.trigger_end] == "excepto"
    assert text[scope.trigger_end : scope.end] == " la S"


def test_duplicated_values_are_kept_once():
    result = _parse("pólizas FS-1 y FS-1")
    assert result.filters.include[0].values == ["FS-1"]
