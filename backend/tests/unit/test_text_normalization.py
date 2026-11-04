import pytest

from app.core.text_normalization import fold, normalize_identifier, normalize_name


@pytest.mark.parametrize("text", ["Pólizas", "ÑANDÚ", "camión", "sin acentos", "€ 10", ""])
def test_fold_keeps_the_length(text):
    assert len(fold(text)) == len(text)


def test_fold_removes_accents():
    assert fold("Póliza Ñandú") == "Poliza Nandu"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("FW-23", "FW23"), ("fw 23", "FW23"), (" fs-2024-001 ", "FS2024001"), ("1234-bcd", "1234BCD")],
)
def test_identifiers_compare_equal_after_normalizing(raw, expected):
    assert normalize_identifier(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("Pérez, Juan", "PEREZ JUAN"), ("  Taller   El Faro S.L. ", "TALLER EL FARO S L")],
)
def test_names_are_normalized(raw, expected):
    assert normalize_name(raw) == expected


def test_punctuation_only_identifier_is_empty():
    assert normalize_identifier("--- ") == ""
