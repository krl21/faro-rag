"""Neutralize PDF content before it is placed inside a prompt.

PDF text is untrusted: it may contain instructions aimed at the model
("ignora las instrucciones anteriores...") or try to close the tags that
delimit it. The prompts wrap that text in tags and tell the model to treat it
as data; this module makes sure the text cannot break out of those tags.
"""

import re

_TAG_NAMES = (
    "documento",
    "fragmento",
    "dato",
    "datos_detectados",
    "pregunta",
    "contexto",
    "historial",
    "mensaje",
    "peticion",
)
_DELIMITER_TAGS = re.compile(rf"<\s*/?\s*({'|'.join(_TAG_NAMES)})\b[^>]*>", re.IGNORECASE)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_untrusted(text: str) -> str:
    """Remove control characters and defuse prompt delimiter tags.

    Args:
        text: Untrusted text extracted from a PDF or typed by a user.

    Returns:
        The text with delimiter tags rewritten as ``[tag]`` so they cannot
        open or close a block in the prompt.
    """
    without_control = _CONTROL_CHARS.sub("", text)
    return _DELIMITER_TAGS.sub(lambda m: f"[{m.group(1).lower()}]", without_control)
