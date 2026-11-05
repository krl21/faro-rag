"""Find amount ranges in a question: ``más de 1000 €``, ``menos de 500``, ``entre 100 y 200``.

A bare number (without currency) only counts as an amount when the question
talks about money (``factura``, ``importe``, ``total``...), so ``más de 3
documentos`` is not taken as an amount.
"""

import re
from decimal import Decimal, InvalidOperation

from app.ai.query.scanner import QuestionScanner
from app.ai.query.types import AmountMatch
from app.schemas.filters import AmountRange

_NUMBER = r"(\d{1,3}(?:[.\s]\d{3})+(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
_CURRENCY = r"(?:\s*(€|eur(?:os?)?|usd|\$|dolares?|cad))?"
_AMOUNT = _NUMBER + _CURRENCY

_BETWEEN = re.compile(rf"\bentre\s+{_AMOUNT}\s+y\s+{_AMOUNT}")
_MINIMUM = re.compile(
    rf"\b(?:mas|mayor(?:es)?|superior(?:es)?|por encima)\s+(?:de|a|que|del)\s+{_AMOUNT}"
)
_MAXIMUM = re.compile(
    rf"\b(?:menos|menor(?:es)?|inferior(?:es)?|por debajo)\s+(?:de|a|que|del)\s+{_AMOUNT}"
)
_MONEY_CONTEXT = re.compile(
    r"\b(?:factur\w*|importe\w*|monto\w*|total\w*|cuest\w*|valor\w*|pag\w*|precio\w*|cobr\w*)\b|€|\$"
)
_CURRENCY_CODES = {
    "€": "EUR",
    "eur": "EUR",
    "euro": "EUR",
    "euros": "EUR",
    "usd": "USD",
    "$": "USD",
    "dolar": "USD",
    "dolares": "USD",
    "cad": "CAD",
}


def parse_number(raw: str) -> Decimal:
    """Parse a Spanish-formatted number (``1.250,50``, ``1 250``, ``1250.5``).

    Args:
        raw: Number as written.

    Returns:
        The value.

    Raises:
        InvalidOperation: If the text is not a number.
    """
    text = raw.replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", text):
        text = text.replace(".", "")
    return Decimal(text)


def _currency(raw: str | None) -> str | None:
    """Map a written currency to its ISO code.

    Args:
        raw: Currency as written, or ``None``.

    Returns:
        The ISO 4217 code, or ``None``.
    """
    return _CURRENCY_CODES.get(raw) if raw else None


def find_amount(scanner: QuestionScanner) -> AmountMatch | None:
    """Find and consume the amount range of the question.

    Args:
        scanner: Question scanner.

    Returns:
        The range, or ``None`` if the question has no amount condition.
    """
    money_context = bool(_MONEY_CONTEXT.search(scanner.text))
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    currency: str | None = None
    spans: list[tuple[int, int]] = []

    def accept(match: re.Match[str], *currency_groups: int) -> bool:
        written = [match.group(g) for g in currency_groups if match.group(g)]
        return bool(written) or money_context

    try:
        for match in list(scanner.finditer(_BETWEEN)):
            if not accept(match, 2, 4):
                continue
            low, high = parse_number(match.group(1)), parse_number(match.group(3))
            minimum, maximum = min(low, high), max(low, high)
            currency = _currency(match.group(4) or match.group(2)) or currency
            spans.append((match.start(), match.end()))
            scanner.consume(match.start(), match.end())
        for pattern, is_minimum in ((_MINIMUM, True), (_MAXIMUM, False)):
            for match in list(scanner.finditer(pattern)):
                if not accept(match, 2):
                    continue
                value = parse_number(match.group(1))
                if is_minimum:
                    minimum = value
                else:
                    maximum = value
                currency = _currency(match.group(2)) or currency
                spans.append((match.start(), match.end()))
                scanner.consume(match.start(), match.end())
    except InvalidOperation:
        return None

    if minimum is None and maximum is None:
        return None
    if minimum is not None and maximum is not None and minimum > maximum:
        minimum, maximum = maximum, minimum
    return AmountMatch(range=AmountRange(min=minimum, max=maximum, currency=currency), spans=spans)
