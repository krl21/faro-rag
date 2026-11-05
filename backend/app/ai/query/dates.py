"""Find dates in a question and decide whether they are upload or document dates.

Supported (Spanish, accents optional): ``hoy``, ``ayer``, ``anteayer``, ``esta
semana``, ``la semana pasada``, ``este mes``, ``el mes pasado``, ``este año``,
``el año pasado``, ``los últimos N días/semanas/meses``, ``15/03/2025``,
``3 de marzo (de 2025)``, ``en marzo (de 2025)``, ``en 2025`` and ranges such
as ``entre el 1/3/2025 y el 15/3/2025``, ``desde ...`` or ``hasta ...``.

Without a year, a day or month refers to its most recent occurrence (today
included). Weeks run from Monday to Sunday.
"""

import re
from collections.abc import Callable
from datetime import date, timedelta

from app.ai.query.scanner import QuestionScanner
from app.ai.query.types import DateMatch
from app.domain.enums import DateTarget
from app.schemas.filters import DateRange

MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
_MONTH = "(" + "|".join(MONTHS) + ")"

_UPLOAD_HINT = re.compile(
    r"\b(?:sub[iao]|subid|subiste|subieron|subimos|guard[aeo]|cargad|cargu|carga[rds]|"
    r"recibid|anadid|ingresad|registrad|almacenad)\w*"
)
_DOCUMENT_HINT = re.compile(
    r"\b(?:emitid|emision|fechad|con fecha|expedid|vigente|vigencia|vence|vencid|valid)\w*"
)
_UNRESOLVED = re.compile(
    r"\b(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo|manana|pasad[oa]s?|"
    r"anterior(?:es)?|recientes?|ultim[oa]s?|proxim[oa]s?|trimestre|semestre|quincena)\b"
)

_EXPLICIT = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")
_DAY_MONTH = re.compile(rf"\b(\d{{1,2}})\s+de\s+{_MONTH}(?:\s+de(?:l)?\s+(\d{{4}}))?\b")
_MONTH_ALONE = re.compile(
    rf"\b(?:(?:en|de|del|durante)\s+(?:el\s+mes\s+de\s+)?)?{_MONTH}(?:\s+de(?:l)?\s+(\d{{4}}))?\b"
)
_YEAR = re.compile(r"\b(?:en|de|del|durante)\s+(?:el\s+)?(?:ano\s+)?((?:19|20)\d{2})\b")
_LAST_N = re.compile(r"\b(?:en\s+)?(?:los|las)?\s*ultim[oa]s\s+(\d{1,3})\s+(dias|semanas|meses)\b")

_RANGE_START = re.compile(r"\b(entre|desde|del|de|a partir del?|despues del?)\s+(?:el\s+)?$")
_RANGE_END = re.compile(r"\b(antes del?|hasta(?:\s+el)?)\s+(?:el\s+)?$")
_RANGE_JOIN = re.compile(r"^\s*(?:y|hasta|al|a)\s+(?:el\s+)?$")


def _month_end(year: int, month: int) -> date:
    """Return the last day of a month.

    Args:
        year: Year.
        month: Month (1-12).

    Returns:
        The last day.
    """
    first_next = date(year + month // 12, month % 12 + 1, 1)
    return first_next - timedelta(days=1)


def _shift_months(day: date, months: int) -> date:
    """Move a date back by whole months, clamping the day to the month length.

    Args:
        day: Starting date.
        months: Months to go back.

    Returns:
        The shifted date.
    """
    total = day.year * 12 + day.month - 1 - months
    year, month = divmod(total, 12)
    return date(year, month + 1, min(day.day, _month_end(year, month + 1).day))


def _recent_year(today: date, month: int, day: int = 1) -> int:
    """Year of the most recent occurrence of a month/day, today included.

    Args:
        today: Current date.
        month: Month.
        day: Day of the month.

    Returns:
        This year, or last year if the date is still to come.
    """
    return today.year if (month, day) <= (today.month, today.day) else today.year - 1


def _relative_rules(today: date) -> list[tuple[re.Pattern[str], Callable[[re.Match], DateRange]]]:
    """Build the relative date rules for a given day.

    Args:
        today: Current date in the configured time zone.

    Returns:
        ``(pattern, resolver)`` pairs, most specific first.
    """
    monday = today - timedelta(days=today.weekday())

    def days(start: date, end: date) -> Callable[[re.Match], DateRange]:
        return lambda _: DateRange(start=start, end=end)

    def last_n(match: re.Match) -> DateRange:
        amount, unit = int(match.group(1)), match.group(2)
        if unit == "dias":
            start = today - timedelta(days=amount - 1)
        elif unit == "semanas":
            start = today - timedelta(weeks=amount) + timedelta(days=1)
        else:
            start = _shift_months(today, amount) + timedelta(days=1)
        return DateRange(start=start, end=today)

    previous_month_end = today.replace(day=1) - timedelta(days=1)
    return [
        (_LAST_N, last_n),
        (
            re.compile(r"\b(?:antes de ayer|anteayer)\b"),
            days(today - timedelta(2), today - timedelta(2)),
        ),
        (re.compile(r"\bayer\b"), days(today - timedelta(1), today - timedelta(1))),
        (re.compile(r"\bhoy\b"), days(today, today)),
        (re.compile(r"\besta semana\b"), days(monday, today)),
        (
            re.compile(r"\b(?:la\s+)?semana\s+(?:pasada|anterior)\b"),
            days(monday - timedelta(7), monday - timedelta(1)),
        ),
        (re.compile(r"\beste mes\b"), days(today.replace(day=1), today)),
        (
            re.compile(r"\b(?:el\s+)?mes\s+(?:pasado|anterior)\b"),
            days(previous_month_end.replace(day=1), previous_month_end),
        ),
        (re.compile(r"\beste ano\b"), days(date(today.year, 1, 1), today)),
        (
            re.compile(r"\b(?:el\s+)?ano\s+(?:pasado|anterior)\b"),
            days(date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)),
        ),
    ]


def _target(scanner: QuestionScanner, start: int, end: int, default: DateTarget) -> DateTarget:
    """Decide which date an expression refers to from the nearby verbs.

    ``subidas/guardadas/cargadas`` -> upload date; ``emitidas/con fecha/
    vigentes`` -> document date; otherwise ``default``.

    Args:
        scanner: Question scanner.
        start: Start of the expression.
        end: End of the expression.
        default: Target when no verb gives a hint.

    Returns:
        The target.
    """
    window = scanner.text[max(0, start - 50) : start] + " " + scanner.text[end : end + 25]
    if _UPLOAD_HINT.search(window):
        return DateTarget.UPLOADED
    if _DOCUMENT_HINT.search(window):
        return DateTarget.DOCUMENT
    return default


def _single_days(scanner: QuestionScanner, today: date) -> list[tuple[int, int, date]]:
    """Find explicit days (``15/03/2025``, ``3 de marzo``) without consuming them.

    Args:
        scanner: Question scanner.
        today: Current date.

    Returns:
        ``(start, end, day)`` triples in order; invalid dates are skipped.
    """
    found = []
    for match in scanner.finditer(_EXPLICIT):
        try:
            day = date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        except ValueError:
            continue
        found.append((match.start(), match.end(), day))
    for match in scanner.finditer(_DAY_MONTH):
        day_number, month = int(match.group(1)), MONTHS[match.group(2)]
        year = int(match.group(3)) if match.group(3) else _recent_year(today, month, day_number)
        try:
            day = date(year, month, day_number)
        except ValueError:
            continue
        found.append((match.start(), match.end(), day))
    return sorted(found)


def _explicit_ranges(scanner: QuestionScanner, today: date) -> list[DateMatch]:
    """Turn explicit days into single days or ranges and consume them.

    Args:
        scanner: Question scanner.
        today: Current date.

    Returns:
        The matches.
    """
    days = _single_days(scanner, today)
    matches: list[DateMatch] = []
    index = 0
    while index < len(days):
        start, end, day = days[index]
        prefix_text = scanner.text[max(0, start - 25) : start]
        prefix = _RANGE_START.search(prefix_text)
        span_start = start - (len(prefix_text) - prefix.start()) if prefix else start
        following = days[index + 1] if index + 1 < len(days) else None
        if prefix and following and _RANGE_JOIN.match(scanner.text[end : following[0]]):
            date_range = DateRange(start=min(day, following[2]), end=max(day, following[2]))
            span_end = following[1]
            index += 2
        elif prefix and prefix.group(1) not in ("de", "del", "entre"):
            date_range, span_end = DateRange(start=day), end
            index += 1
        elif end_prefix := _RANGE_END.search(prefix_text):
            span_start = start - (len(prefix_text) - end_prefix.start())
            date_range, span_end = DateRange(end=day), end
            index += 1
        else:
            date_range, span_start, span_end = DateRange(start=day, end=day), start, end
            index += 1
        target = _target(scanner, span_start, span_end, DateTarget.DOCUMENT)
        matches.append(DateMatch(span_start, span_end, date_range, target))
    for match in matches:
        scanner.consume(match.start, match.end)
    return matches


def find_dates(scanner: QuestionScanner, today: date) -> list[DateMatch]:
    """Find and consume every date expression of the question.

    Relative expressions (``ayer``, ``esta semana``...) default to the upload
    date; calendar dates, months and years default to the document date.
    Nearby verbs override the default.

    Args:
        scanner: Question scanner.
        today: Current date in the configured time zone.

    Returns:
        The matches found.
    """
    matches: list[DateMatch] = []
    for pattern, resolve in _relative_rules(today):
        for match in list(scanner.finditer(pattern)):
            target = _target(scanner, match.start(), match.end(), DateTarget.UPLOADED)
            matches.append(DateMatch(match.start(), match.end(), resolve(match), target))
            scanner.consume(match.start(), match.end())

    matches.extend(_explicit_ranges(scanner, today))

    for match in list(scanner.finditer(_MONTH_ALONE)):
        month = MONTHS[match.group(1)]
        year = int(match.group(2)) if match.group(2) else _recent_year(today, month)
        date_range = DateRange(start=date(year, month, 1), end=_month_end(year, month))
        target = _target(scanner, match.start(), match.end(), DateTarget.DOCUMENT)
        matches.append(DateMatch(match.start(), match.end(), date_range, target))
        scanner.consume(match.start(), match.end())

    for match in list(scanner.finditer(_YEAR)):
        year = int(match.group(1))
        date_range = DateRange(start=date(year, 1, 1), end=date(year, 12, 31))
        target = _target(scanner, match.start(), match.end(), DateTarget.DOCUMENT)
        matches.append(DateMatch(match.start(), match.end(), date_range, target))
        scanner.consume(match.start(), match.end())
    return matches


def has_unresolved_dates(scanner: QuestionScanner) -> bool:
    """Tell whether date-like words remain that the rules could not resolve.

    Args:
        scanner: Question scanner, after ``find_dates``.

    Returns:
        ``True`` for words such as ``lunes``, ``pasado``, ``últimos``, ``trimestre``.
    """
    return bool(_UNRESOLVED.search(scanner.text))


def merge_ranges(ranges: list[DateRange]) -> DateRange | None:
    """Combine several ranges into the smallest range that covers them all.

    Args:
        ranges: Ranges of the same target.

    Returns:
        The covering range (open if any range is open), or ``None`` if empty.
    """
    if not ranges:
        return None
    starts = [r.start for r in ranges]
    ends = [r.end for r in ranges]
    start = None if None in starts else min(s for s in starts if s is not None)
    end = None if None in ends else max(e for e in ends if e is not None)
    return DateRange(start=start, end=end)
