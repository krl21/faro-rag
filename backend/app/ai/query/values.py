"""Find identifiers and document types mentioned in a question.

Two kinds of identifiers:

- **Labelled lists**: a label followed by one or more values, such as
  ``las pólizas A, B y C``, ``matrícula 1234-BCD`` or ``NIF B12345678``, or
  values followed by ``como``/``de`` and the label (``A, B, C como pólizas``).
  A value counts if it has a digit or is written in upper case (``S``), so
  ``pólizas vigentes`` is not read as a policy called "vigentes".
- **Bare identifiers** recognized by their shape: policy numbers
  (``FS-2024-001``), Spanish tax ids (``12345678Z``) and license plates
  (``1234-BCD``).

Any remaining ``póliza(s)`` / ``factura(s)`` is a document type mention.
"""

import re

from app.ai.query.scanner import QuestionScanner
from app.ai.query.types import TypeMatch, ValueMatch
from app.domain.enums import DocumentType, FilterField

_TOKEN = r"[a-z0-9][a-z0-9-]*"  # noqa: S105 - a regex, not a secret
_SEPARATOR = r"\s*(?:,|\by\b|\be\b|\bo\b|\bu\b)\s*"
_LABEL = r"(?P<label>n(?:umero)?s?\s+de\s+polizas?|polizas?|matriculas?|nifs?|cifs?|dnis?)"
_LABELLED = re.compile(
    rf"\b{_LABEL}"
    r"(?:\s+(?:n[o.]|numero|num\.?|con\s+numero))?"
    r"(?P<filler>(?:\s+(?:la|el|las|los|de|del|que\s+sean?|sean?|con|igual\s+a))*)\s*:?\s+"
    rf"(?P<values>{_TOKEN}(?:{_SEPARATOR}{_TOKEN})*)"
)
_LABELLED_AFTER = re.compile(
    rf"\b(?P<values>{_TOKEN}(?:{_SEPARATOR}{_TOKEN})*)\s+(?:como|de)\s+(?:(?:la|el|las|los)\s+)?{_LABEL}\b"
)
_LABEL_WORD = re.compile(r"^(?:polizas?|matriculas?|nifs?|cifs?|dnis?|numeros?)$")
_BARE: tuple[tuple[re.Pattern[str], FilterField], ...] = (
    (re.compile(r"\b[a-z]{1,5}-\d{2,}(?:-\d+)*\b"), FilterField.POLICY_NUMBER),
    (re.compile(r"\b(?:\d{8}[a-z]|[a-z]\d{7}[0-9a-z])\b"), FilterField.TAX_ID),
    (re.compile(r"\b\d{4}[ -]?[bcdfghjklmnprstvwxyz]{3}\b"), FilterField.LICENSE_PLATE),
)
_DOCUMENT_TYPES = re.compile(r"\b(polizas?|facturas?)\b")
_LABEL_FIELDS = {
    "poliza": FilterField.POLICY_NUMBER,
    "matricula": FilterField.LICENSE_PLATE,
    "nif": FilterField.TAX_ID,
    "cif": FilterField.TAX_ID,
    "dni": FilterField.TAX_ID,
}
_STOPWORDS = frozenset({"y", "e", "o", "u", "de", "del", "la", "el", "las", "los", "que"})


def _label_field(label: str) -> FilterField:
    """Map a label (``pólizas``, ``matrícula``, ``nº de póliza``...) to its field.

    Args:
        label: Folded label text.

    Returns:
        The field.
    """
    for prefix, field in _LABEL_FIELDS.items():
        if prefix in label:
            return field
    return FilterField.POLICY_NUMBER


def _looks_like_value(scanner: QuestionScanner, start: int, end: int, token: str) -> bool:
    """Tell whether a token after a label is an identifier and not a word.

    Args:
        scanner: Question scanner.
        start: Token start.
        end: Token end.
        token: Folded token.

    Returns:
        ``True`` if it has a digit, or is upper case in the original question.
    """
    if token in _STOPWORDS or _LABEL_WORD.match(token):
        return False
    return any(c.isdigit() for c in token) or scanner.is_upper(start, end)


def _labelled_values(scanner: QuestionScanner) -> list[ValueMatch]:
    """Find and consume labelled lists of identifiers.

    Args:
        scanner: Question scanner.

    Returns:
        The matches.
    """
    matches = []
    position = 0
    # Search again after each match: a list can stop at the next label
    # ("matrícula 1234-BCD y NIF B12345678"), which must then match on its own.
    while match := _LABELLED.search(scanner.text, position):
        values_start = match.start("values")
        accepted: list[str] = []
        end = values_start
        for token in re.finditer(_TOKEN, match.group("values")):
            token_start, token_end = values_start + token.start(), values_start + token.end()
            if not _looks_like_value(scanner, token_start, token_end, token.group()):
                if token.group() in _STOPWORDS:
                    continue  # A separator word such as "y".
                break
            accepted.append(scanner.original[token_start:token_end])
            end = token_end
        if not accepted:
            position = match.start() + 1
            continue
        field = _label_field(match.group("label"))
        matches.append(ValueMatch(match.start(), end, field, tuple(accepted)))
        scanner.consume(match.start(), end)
        position = end
    for match in list(scanner.finditer(_LABELLED_AFTER)):
        values_start = match.start("values")
        tokens = list(re.finditer(_TOKEN, match.group("values")))
        accepted_reversed: list[str] = []
        start = match.start("label")
        for token in reversed(tokens):  # Values closest to the label first.
            token_start, token_end = values_start + token.start(), values_start + token.end()
            if token.group() in _STOPWORDS:
                continue
            if not _looks_like_value(scanner, token_start, token_end, token.group()):
                break
            accepted_reversed.append(scanner.original[token_start:token_end])
            start = token_start
        if not accepted_reversed:
            continue
        field = _label_field(match.group("label"))
        values = tuple(reversed(accepted_reversed))
        matches.append(ValueMatch(start, match.end(), field, values))
        scanner.consume(start, match.end())
    return matches


def find_values(scanner: QuestionScanner) -> list[ValueMatch]:
    """Find and consume identifiers, labelled or bare.

    Args:
        scanner: Question scanner.

    Returns:
        The matches, in the order they were found.
    """
    matches = _labelled_values(scanner)
    for pattern, field in _BARE:
        for match in list(scanner.finditer(pattern)):
            value = scanner.original[match.start() : match.end()]
            matches.append(ValueMatch(match.start(), match.end(), field, (value,)))
            scanner.consume(match.start(), match.end())
    return matches


def find_document_types(scanner: QuestionScanner) -> list[TypeMatch]:
    """Find and consume ``póliza(s)`` / ``factura(s)`` mentions.

    Run it after ``find_values``, so ``la póliza FS-1`` is read as a policy
    number and not as a document type.

    Args:
        scanner: Question scanner.

    Returns:
        The matches.
    """
    matches = []
    for match in list(scanner.finditer(_DOCUMENT_TYPES)):
        word = match.group(1)
        doc_type = DocumentType.INVOICE if word.startswith("factura") else DocumentType.POLICY
        matches.append(TypeMatch(match.start(), match.end(), doc_type))
        scanner.consume(match.start(), match.end())
    return matches
