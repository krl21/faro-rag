"""Rule-based question parser: the cheap path that avoids calling the LLM.

It extracts the filters it can recognize with certainty and reports what it
could not resolve. The interpreter calls the LLM only when something is
unresolved (see ``Unresolved``).
"""

import re
from collections import defaultdict
from datetime import date

from app.ai.query.amounts import find_amount
from app.ai.query.dates import find_dates, has_unresolved_dates, merge_ranges
from app.ai.query.negation import find_negations, is_negated
from app.ai.query.scanner import QuestionScanner
from app.ai.query.types import RuleParse
from app.ai.query.values import find_document_types, find_values
from app.core.text_normalization import fold
from app.domain.enums import DateTarget, DocumentType, FilterField, Unresolved
from app.schemas.filters import DateRange, FieldValues, QueryFilters

_NAME = re.compile(
    r"\b(?:de|del|a nombre de|titular|tomador|cliente|emisor|emitid[ao]s? por|por)\s+"
    r"([A-ZÁÉÍÓÚÑ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñü]+)*)"
)
_REFERENCE = re.compile(
    r"^\W*y\b|\b(?:es[aeo]s?|aquel\w*|anterior(?:es)?|mism[oa]s?|tambien|otr[oa]s?|ademas|"
    r"dich[oa]s?|mencionad\w*|previ[oa]s?|de antes)\b"
)
_FILLER_VERBS = re.compile(
    r"^(?:sub|guard|carg|recib|anad|ingres|registr|almacen|emit|fech|vigent|tengan|teng|"
    r"necesit|quier|quisier|muestr|mostr|ensen|list|busc|encuentr|tra[ei]|d[aá]m)\w*$"
)
_FILLER_WORDS = frozenset(
    [
        "a",
        "al",
        "algun",
        "alguna",
        "algunas",
        "alguno",
        "algunos",
        "archivo",
        "archivos",
        "como",
        "con",
        "cual",
        "cuales",
        "cuantas",
        "cuantos",
        "de",
        "del",
        "documento",
        "documentos",
        "donde",
        "e",
        "el",
        "ella",
        "ellas",
        "ellos",
        "en",
        "entre",
        "es",
        "esta",
        "estan",
        "este",
        "estos",
        "ficheros",
        "fichero",
        "hay",
        "la",
        "las",
        "le",
        "les",
        "lo",
        "los",
        "me",
        "mi",
        "mis",
        "o",
        "para",
        "pdf",
        "pdfs",
        "por",
        "favor",
        "que",
        "se",
        "sea",
        "sean",
        "ser",
        "solo",
        "solamente",
        "son",
        "su",
        "sus",
        "te",
        "tienes",
        "todas",
        "todos",
        "tu",
        "un",
        "una",
        "unas",
        "uno",
        "unos",
        "y",
        "ya",
        "ver",
        "dame",
        "dime",
        "fecha",
        "fechas",
        "dia",
        "dias",
    ]
)
_WORD = re.compile(r"[a-z0-9]+")
_IN_FORCE = re.compile(r"\bvigentes?\b")


def _is_content(word: str) -> bool:
    """Tell whether a word asks for content (``deducible``) rather than filler (``necesito``).

    Args:
        word: Folded lower-case word.

    Returns:
        ``True`` for words worth a semantic search.
    """
    return len(word) > 1 and word not in _FILLER_WORDS and not _FILLER_VERBS.match(word)


def _name_mentioned(scanner: QuestionScanner) -> bool:
    """Tell whether the question names a person or company that was not consumed.

    Args:
        scanner: Question scanner.

    Returns:
        ``True`` when a capitalized name follows ``de``, ``titular``, ``emisor``...
    """
    for match in _NAME.finditer(scanner.original):
        start, end = match.span(1)
        if scanner.text[start:end].strip() == fold(match.group(1)).lower():
            return True
    return False


def parse_with_rules(question: str, today: date, *, has_history: bool) -> RuleParse:
    """Extract filters from a question with deterministic rules.

    Args:
        question: The user question.
        today: Current date in the configured time zone.
        has_history: Whether the conversation has earlier messages.

    Returns:
        The filters and the reasons, if any, to call the LLM.
    """
    scanner = QuestionScanner(question)
    values = find_values(scanner)
    dates = find_dates(scanner, today)
    amount = find_amount(scanner)
    types = find_document_types(scanner)
    scopes = find_negations(scanner)

    unresolved: list[Unresolved] = []
    include: dict[FilterField, list[str]] = defaultdict(list)
    exclude: dict[FilterField, list[str]] = defaultdict(list)
    for match in values:
        target = exclude if is_negated(scopes, match.start) else include
        target[match.field].extend(match.values)

    included_types: list[DocumentType] = []
    for match in types:
        if is_negated(scopes, match.start):
            exclude[FilterField.DOCUMENT_TYPE].append(match.document_type.value)
        elif match.document_type not in included_types:
            included_types.append(match.document_type)
    document_type = None
    if len(included_types) == 1:
        document_type = included_types[0]
    elif len(included_types) > 1:
        include[FilterField.DOCUMENT_TYPE].extend(t.value for t in included_types)

    used = [m.start for m in values] + [m.start for m in types]
    for scope in scopes:
        if not any(scope.contains(position) for position in used):
            unresolved.append(Unresolved.NEGATION)
            break
    # The filter format cannot exclude dates ("no las de ayer"): the LLM decides.
    positive_dates = [m for m in dates if not is_negated(scopes, m.start)]
    if len(positive_dates) < len(dates):
        unresolved.append(Unresolved.NEGATION)
    if has_unresolved_dates(scanner):
        unresolved.append(Unresolved.DATE)
    if _name_mentioned(scanner):
        unresolved.append(Unresolved.NAME)
    if has_history and _REFERENCE.search(scanner.text):
        unresolved.append(Unresolved.REFERENCE)

    for scope in scopes:  # The negated clause only describes what to remove.
        scanner.consume(scope.trigger_start, scope.end)
    leftover = scanner.remaining()
    has_content = any(_is_content(w) for w in _WORD.findall(fold(leftover).lower()))

    document_ranges = [m.range for m in positive_dates if m.target is DateTarget.DOCUMENT]
    if not document_ranges and _IN_FORCE.search(scanner.text):
        # "pólizas vigentes" without a date means in force today.
        document_ranges = [DateRange(start=today, end=today)]

    filters = QueryFilters(
        document_type=document_type,
        uploaded=merge_ranges([m.range for m in positive_dates if m.target is DateTarget.UPLOADED]),
        document_date=merge_ranges(document_ranges),
        amount=amount.range if amount else None,
        include=[FieldValues(field=f, values=_unique(v)) for f, v in include.items()],
        exclude=[FieldValues(field=f, values=_unique(v)) for f, v in exclude.items()],
        query=leftover if has_content else "",
    )
    return RuleParse(filters=filters, unresolved=list(dict.fromkeys(unresolved)))


def _unique(values: list[str]) -> list[str]:
    """Remove duplicated values keeping their order.

    Args:
        values: Values as written.

    Returns:
        The values without repetitions (at most 20, the schema limit).
    """
    return list(dict.fromkeys(values))[:20]
