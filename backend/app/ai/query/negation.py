"""Detect negated parts of a question: ``no quiero la de la póliza S``, ``excepto ...``.

A negation trigger opens a *scope* that lasts until the end of the clause
(punctuation, ``pero``, ``sino``, ``solo``...). Values and document types found
inside a scope are excluded instead of included.

Amounts are parsed before negations, so ``menos de 500 €`` is a maximum and not
a negation.
"""

import re

from app.ai.query.scanner import QuestionScanner
from app.ai.query.types import NegationScope

_TRIGGER = re.compile(
    r"\b(?:no|ni|sin|excepto|exceptuando|salvo|menos|excluye\w*|excluir|excluyendo|quitando|"
    r"quita|aparte\s+de|fuera\s+de|distint[oa]s?\s+(?:de|a)|diferentes?\s+(?:de|a))\b"
)
_CLAUSE_END = re.compile(
    r"[.;!?]|\b(?:pero|sino|solo|solamente|unicamente|aunque)\b|"
    r",\s*(?:y\s+)?(?:quiero|necesito|dame|muestra\w*|busca\w*|incluye\w*)\b"
)


def find_negations(scanner: QuestionScanner) -> list[NegationScope]:
    """Find the negation scopes of the question, without consuming anything.

    Args:
        scanner: Question scanner, after amounts were consumed.

    Returns:
        The scopes, in order.
    """
    text = scanner.text
    scopes = []
    for trigger in _TRIGGER.finditer(text):
        clause_end = _CLAUSE_END.search(text, trigger.end())
        end = clause_end.start() if clause_end else len(text)
        scopes.append(NegationScope(trigger.start(), trigger.end(), end))
    return scopes


def is_negated(scopes: list[NegationScope], position: int) -> bool:
    """Tell whether a position is inside any negation scope.

    Args:
        scopes: Negation scopes.
        position: Character position.

    Returns:
        ``True`` if negated.
    """
    return any(scope.contains(position) for scope in scopes)
