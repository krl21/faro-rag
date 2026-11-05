"""Date expressions in questions. Today is Tuesday 2026-11-03."""

from datetime import date

import pytest

from app.ai.query.dates import find_dates, has_unresolved_dates, merge_ranges
from app.ai.query.scanner import QuestionScanner
from app.domain.enums import DateTarget
from app.schemas.filters import DateRange

TODAY = date(2026, 11, 3)


def _dates(question: str):
    return find_dates(QuestionScanner(question), TODAY)


def _only(question: str):
    (match,) = _dates(question)
    return match


@pytest.mark.parametrize(
    ("expression", "start", "end"),
    [
        ("hoy", date(2026, 11, 3), date(2026, 11, 3)),
        ("ayer", date(2026, 11, 2), date(2026, 11, 2)),
        ("anteayer", date(2026, 11, 1), date(2026, 11, 1)),
        ("antes de ayer", date(2026, 11, 1), date(2026, 11, 1)),
        ("esta semana", date(2026, 11, 2), date(2026, 11, 3)),
        ("la semana pasada", date(2026, 10, 26), date(2026, 11, 1)),
        ("este mes", date(2026, 11, 1), date(2026, 11, 3)),
        ("el mes pasado", date(2026, 10, 1), date(2026, 10, 31)),
        ("este año", date(2026, 1, 1), date(2026, 11, 3)),
        ("el año pasado", date(2025, 1, 1), date(2025, 12, 31)),
        ("los últimos 7 días", date(2026, 10, 28), date(2026, 11, 3)),
        ("las últimas 2 semanas", date(2026, 10, 21), date(2026, 11, 3)),
        ("los últimos 3 meses", date(2026, 8, 4), date(2026, 11, 3)),
    ],
)
def test_relative_dates_default_to_the_upload_date(expression, start, end):
    match = _only(f"documentos de {expression}")
    assert match.range == DateRange(start=start, end=end)
    assert match.target is DateTarget.UPLOADED


@pytest.mark.parametrize(
    ("expression", "start", "end"),
    [
        ("15/03/2025", date(2025, 3, 15), date(2025, 3, 15)),
        ("3 de marzo de 2025", date(2025, 3, 3), date(2025, 3, 3)),
        ("en marzo", date(2026, 3, 1), date(2026, 3, 31)),
        ("en diciembre", date(2025, 12, 1), date(2025, 12, 31)),  # Still to come: last year.
        ("de febrero de 2024", date(2024, 2, 1), date(2024, 2, 29)),
        ("en 2025", date(2025, 1, 1), date(2025, 12, 31)),
    ],
)
def test_calendar_dates_default_to_the_document_date(expression, start, end):
    match = _only(f"facturas {expression}")
    assert match.range == DateRange(start=start, end=end)
    assert match.target is DateTarget.DOCUMENT


def test_day_without_year_is_the_most_recent_one():
    assert _only("facturas del 20 de diciembre").range.start == date(2025, 12, 20)
    assert _only("facturas del 3 de noviembre").range.start == date(2026, 11, 3)


@pytest.mark.parametrize(
    "question",
    ["facturas entre el 1/3/2025 y el 15/3/2025", "facturas del 1/3/2025 al 15/3/2025"],
)
def test_explicit_ranges(question):
    assert _only(question).range == DateRange(start=date(2025, 3, 1), end=date(2025, 3, 15))


def test_reversed_range_is_ordered():
    match = _only("entre el 15/3/2025 y el 1/3/2025")
    assert match.range == DateRange(start=date(2025, 3, 1), end=date(2025, 3, 15))


def test_open_ranges():
    assert _only("desde el 1/3/2025").range == DateRange(start=date(2025, 3, 1))
    assert _only("hasta el 1/3/2025").range == DateRange(end=date(2025, 3, 1))
    assert _only("antes del 1/3/2025").range == DateRange(end=date(2025, 3, 1))


@pytest.mark.parametrize(
    ("question", "target"),
    [
        ("facturas subidas en marzo", DateTarget.UPLOADED),
        ("lo que guardé el 15/03/2026", DateTarget.UPLOADED),
        ("facturas emitidas ayer", DateTarget.DOCUMENT),
        ("pólizas con fecha de hoy", DateTarget.DOCUMENT),
    ],
)
def test_nearby_verbs_choose_the_target(question, target):
    assert _only(question).target is target


def test_invalid_dates_are_ignored():
    assert _dates("facturas del 31/02/2025") == []


def test_dates_are_consumed():
    scanner = QuestionScanner("facturas de ayer")
    find_dates(scanner, TODAY)
    assert scanner.remaining() == "facturas de"


@pytest.mark.parametrize(
    "question",
    ["las del lunes", "el trimestre pasado", "las facturas más recientes", "el próximo mes"],
)
def test_unresolved_date_words_are_reported(question):
    scanner = QuestionScanner(question)
    find_dates(scanner, TODAY)
    assert has_unresolved_dates(scanner)


@pytest.mark.parametrize("question", ["facturas de ayer", "pólizas de 2025", "deducible"])
def test_resolved_questions_have_no_unresolved_dates(question):
    scanner = QuestionScanner(question)
    find_dates(scanner, TODAY)
    assert not has_unresolved_dates(scanner)


def test_merge_ranges_covers_all():
    merged = merge_ranges(
        [
            DateRange(start=date(2025, 3, 1), end=date(2025, 3, 2)),
            DateRange(start=date(2025, 1, 1), end=date(2025, 1, 5)),
        ]
    )
    assert merged == DateRange(start=date(2025, 1, 1), end=date(2025, 3, 2))


def test_merge_ranges_keeps_open_ends_and_handles_empty():
    assert merge_ranges([]) is None
    merged = merge_ranges(
        [DateRange(start=date(2025, 1, 1), end=date(2025, 2, 1)), DateRange(end=date(2025, 6, 1))]
    )
    assert (merged.start, merged.end) == (None, date(2025, 6, 1))
