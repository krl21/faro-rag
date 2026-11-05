from decimal import Decimal

import pytest

from app.ai.query.amounts import find_amount, parse_number
from app.ai.query.scanner import QuestionScanner


def _amount(question: str):
    return find_amount(QuestionScanner(question))


@pytest.mark.parametrize(
    ("raw", "value"),
    [
        ("1.250,50", "1250.50"),
        ("1250.5", "1250.5"),
        ("1.000", "1000"),
        ("1 000", "1000"),
        ("12", "12"),
    ],
)
def test_spanish_numbers(raw, value):
    assert parse_number(raw) == Decimal(value)


@pytest.mark.parametrize(
    ("question", "minimum", "maximum", "currency"),
    [
        ("facturas de más de 1000 €", "1000", None, "EUR"),
        ("facturas mayores de 1.000 euros", "1000", None, "EUR"),
        ("facturas de menos de 500", None, "500", None),
        ("facturas inferiores a 99,90 eur", None, "99.90", "EUR"),
        ("facturas entre 100 y 200 euros", "100", "200", "EUR"),
        ("facturas entre 200 y 100", "100", "200", None),
        ("importe superior a 50 USD", "50", None, "USD"),
        ("facturas de más de 100 y menos de 300 €", "100", "300", "EUR"),
    ],
)
def test_amount_ranges(question, minimum, maximum, currency):
    match = _amount(question)
    assert match.range.min == (Decimal(minimum) if minimum else None)
    assert match.range.max == (Decimal(maximum) if maximum else None)
    assert match.range.currency == currency


def test_bare_numbers_need_a_money_context():
    assert _amount("pólizas con más de 3 coberturas") is None


def test_currency_is_enough_without_context():
    assert _amount("documentos de más de 3 €").range.min == Decimal(3)


def test_questions_without_amounts():
    assert _amount("¿qué cubre la póliza?") is None


def test_amount_is_consumed():
    scanner = QuestionScanner("facturas de menos de 500 €")
    find_amount(scanner)
    assert scanner.remaining() == "facturas de"
