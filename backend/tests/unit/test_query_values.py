import pytest

from app.ai.query.scanner import QuestionScanner
from app.ai.query.values import find_document_types, find_values
from app.domain.enums import DocumentType, FilterField


def _values(question: str):
    return [(m.field, m.values) for m in find_values(QuestionScanner(question))]


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("las pólizas A, B y C", [(FilterField.POLICY_NUMBER, ("A", "B", "C"))]),
        ("la póliza S", [(FilterField.POLICY_NUMBER, ("S",))]),
        ("póliza nº FS-2024-001", [(FilterField.POLICY_NUMBER, ("FS-2024-001",))]),
        ("número de póliza 123", [(FilterField.POLICY_NUMBER, ("123",))]),
        ("lo que tengan A, B, C como pólizas", [(FilterField.POLICY_NUMBER, ("A", "B", "C"))]),
        ("matrícula 1234-BCD", [(FilterField.LICENSE_PLATE, ("1234-BCD",))]),
        ("NIF: B12345678", [(FilterField.TAX_ID, ("B12345678",))]),
        ("el DNI 12345678Z", [(FilterField.TAX_ID, ("12345678Z",))]),
    ],
)
def test_labelled_values(question, expected):
    assert _values(question) == expected


@pytest.mark.parametrize(
    ("question", "field", "value"),
    [
        ("¿qué cubre FS-2024-001?", FilterField.POLICY_NUMBER, "FS-2024-001"),
        ("facturas del 12345678Z", FilterField.TAX_ID, "12345678Z"),
        ("el coche 1234 BCD", FilterField.LICENSE_PLATE, "1234 BCD"),
    ],
)
def test_bare_identifiers_are_recognized_by_shape(question, field, value):
    assert _values(question) == [(field, (value,))]


def test_a_list_stops_at_the_next_label():
    assert _values("matrícula 1234-BCD y NIF B12345678") == [
        (FilterField.LICENSE_PLATE, ("1234-BCD",)),
        (FilterField.TAX_ID, ("B12345678",)),
    ]


@pytest.mark.parametrize(
    "question",
    ["pólizas vigentes", "la póliza de vida", "pólizas a nombre de alguien", "las facturas"],
)
def test_lower_case_words_after_a_label_are_not_values(question):
    assert _values(question) == []


def test_document_types_after_values():
    scanner = QuestionScanner("facturas de la póliza FS-1 y pólizas")
    find_values(scanner)
    types = [m.document_type for m in find_document_types(scanner)]
    assert types == [DocumentType.INVOICE, DocumentType.POLICY]


def test_labelled_policy_is_not_a_type_mention():
    scanner = QuestionScanner("la póliza FS-2024-001")
    find_values(scanner)
    assert find_document_types(scanner) == []
