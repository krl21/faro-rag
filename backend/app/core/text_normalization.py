"""Text normalization shared by field indexing and question filters.

Both sides must normalize the same way, otherwise ``FW-23`` in a document and
``fw 23`` in a question would never match.
"""

import re
import unicodedata

_NOT_ALNUM = re.compile(r"[^A-Z0-9]")
_NOT_NAME = re.compile(r"[^A-Z0-9 ]")
_SPACES = re.compile(r"\s+")


def fold_char(char: str) -> str:
    """Remove the accent of one character, keeping exactly one character.

    Args:
        char: A single character.

    Returns:
        The base character (``á`` -> ``a``, ``Ñ`` -> ``N``), or ``char`` itself
        when it has no ASCII base.
    """
    base = unicodedata.normalize("NFKD", char)[:1]
    return base if base.isascii() and base else char


def fold(text: str) -> str:
    """Remove accents without changing the length of the text.

    Keeping the length lets the question parser map positions found in the
    folded text back to the original text.

    Args:
        text: Any text.

    Returns:
        The text with each accented character replaced by its base character.
    """
    return "".join(fold_char(c) for c in text)


def normalize_identifier(value: str) -> str:
    """Normalize an identifier for exact comparison.

    Args:
        value: Policy number, tax id, license plate...

    Returns:
        Upper-case letters and digits only: ``fw - 23`` -> ``FW23``.
    """
    return _NOT_ALNUM.sub("", fold(value).upper())


def normalize_name(value: str) -> str:
    """Normalize a person or company name for partial comparison.

    Args:
        value: Holder or issuer name.

    Returns:
        Upper case without accents or punctuation, single spaces:
        ``Pérez, Juan`` -> ``PEREZ JUAN``.
    """
    cleaned = _NOT_NAME.sub(" ", fold(value).upper())
    return _SPACES.sub(" ", cleaned).strip()
