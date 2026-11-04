"""Deterministic heuristics that let the fake LLM produce plausible answers.

They only exist so the demo and the tests work without a real model. The
output follows the same Spanish JSON contract the real LLM is asked for.
"""

import json
import re
from datetime import date

_POLICY_NUMBER = re.compile(r"\b([A-Z]{2,5}-\d{2,6}(?:-\d+)*)\b")
_DATE = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
_AMOUNT = re.compile(
    r"(?:total|importe|monto)[^\d\n]{0,30}(\d{1,3}(?:\.\d{3})*,\d{2}|\d+(?:\.\d{2})?)\s*(EUR|USD|€|\$)?",
    re.IGNORECASE,
)
_HOLDER = re.compile(
    r"^\s*(?:Titular|Tomador|Cliente)\s*:\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE
)
_TAX_ID = re.compile(r"\b(\d{8}[A-Z]|[A-Z]\d{7}[0-9A-Z])\b")
_LICENSE_PLATE = re.compile(r"\b(\d{4}[- ]?[BCDFGHJKLMNPRSTVWXYZ]{3})\b")
_PAGE_MARKER = re.compile(r"\[Página (\d+)\]")
_BULLET = re.compile(r"^\s*[-•*]\s+(.+)$", re.MULTILINE)
_TAGGED_BLOCK = re.compile(r"<documento>\n?(.*?)\n?</documento>", re.DOTALL)
_TODAY = re.compile(r"Fecha de hoy: (\d{4}-\d{2}-\d{2})")
_REQUEST = re.compile(r"<peticion>\n?(.*?)\n?</peticion>", re.DOTALL)
_FIRST_FRAGMENT = re.compile(r"<fragmento id=\"1\"[^>]*>\n?(.*?)\n?</fragmento>", re.DOTALL)


def document_text(prompt: str) -> str:
    """Return the document text enclosed in ``<documento>`` tags.

    Args:
        prompt: User prompt built by the extraction prompts.

    Returns:
        The enclosed text, or the whole prompt if there are no tags.
    """
    match = _TAGGED_BLOCK.search(prompt)
    return match.group(1) if match else prompt


def _page_at(text: str, position: int | None) -> int | None:
    """Find the page of a position from the ``[Página n]`` markers before it.

    Args:
        text: Document text with page markers.
        position: Character position, or ``None``.

    Returns:
        The page number, or ``None`` if unknown.
    """
    if position is None:
        return None
    pages = [int(m.group(1)) for m in _PAGE_MARKER.finditer(text, 0, position)]
    return pages[-1] if pages else None


def _field(value: object, page: int | None = None) -> dict[str, object]:
    """Wrap a value in the ``{valor, confianza, pagina}`` contract.

    Args:
        value: Extracted value, or ``None`` when not found.
        page: Page where it was found.

    Returns:
        The field object with ``alta`` confidence when found, ``baja`` otherwise.
    """
    found = value not in (None, [], "")
    return {
        "valor": value,
        "confianza": "alta" if found else "baja",
        "pagina": page if found else None,
    }


def _match_field(match: re.Match[str] | None, text: str) -> dict[str, object]:
    """Build a field from a regex match (group 1), with its page.

    Args:
        match: The match, or ``None``.
        text: Text that was searched.

    Returns:
        The field object.
    """
    if match is None:
        return _field(None)
    return _field(match.group(1), _page_at(text, match.start()))


def _dates(text: str) -> list[str]:
    """Find ``dd/mm/yyyy`` dates and return them in ISO format.

    Args:
        text: Text to scan.

    Returns:
        ISO dates in order of appearance.
    """
    return [f"{y}-{m}-{d}" for d, m, y in _DATE.findall(text)]


def _common_fields(text: str) -> dict[str, dict[str, object]]:
    """Extract the fields asked for in every document type.

    Args:
        text: Document text.

    Returns:
        ``titular``, ``nif`` and ``matricula`` in the extraction contract.
    """
    return {
        "titular": _match_field(_HOLDER.search(text), text),
        "nif": _match_field(_TAX_ID.search(text), text),
        "matricula": _match_field(_LICENSE_PLATE.search(text), text),
    }


def classify(text: str) -> str:
    """Classify a document by keywords.

    Args:
        text: Document text.

    Returns:
        JSON with ``tipo`` (``poliza``, ``factura`` or ``desconocido``) and ``confianza``.
    """
    lowered = text.lower()
    if "factura" in lowered:
        doc_type = "factura"
    elif "póliza" in lowered or "poliza" in lowered:
        doc_type = "poliza"
    else:
        doc_type = "desconocido"
    return json.dumps({"tipo": doc_type, "confianza": "alta"})


def extract_policy(text: str) -> str:
    """Extract policy fields with regular expressions.

    Args:
        text: Document text.

    Returns:
        JSON following the policy extraction contract.
    """
    dates = _dates(text)
    validity = {"inicio": dates[0], "fin": dates[1]} if len(dates) >= 2 else None
    first_date = _DATE.search(text)
    first_bullet = _BULLET.search(text)
    return json.dumps(
        {
            "numero_poliza": _match_field(_POLICY_NUMBER.search(text), text),
            "vigencia": _field(validity, _page_at(text, first_date and first_date.start())),
            "coberturas": _field(
                [b.strip() for b in _BULLET.findall(text)],
                _page_at(text, first_bullet and first_bullet.start()),
            ),
            **_common_fields(text),
        }
    )


def extract_invoice(text: str) -> str:
    """Extract invoice fields with regular expressions.

    Args:
        text: Document text.

    Returns:
        JSON following the invoice extraction contract.
    """
    amount = _AMOUNT.search(text)
    dates = _dates(text)
    first_date = _DATE.search(text)
    money = None
    if amount:
        raw = amount.group(1)
        normalized = raw.replace(".", "").replace(",", ".") if "," in raw else raw
        currency = {"€": "EUR", "$": "USD"}.get(amount.group(2) or "", amount.group(2) or "EUR")
        money = {"importe": normalized, "moneda": currency}
    return json.dumps(
        {
            "monto_factura": _field(money, _page_at(text, amount and amount.start())),
            "fecha_factura": _field(
                dates[0] if dates else None, _page_at(text, first_date and first_date.start())
            ),
            "numero_poliza": _match_field(_POLICY_NUMBER.search(text), text),
            **_common_fields(text),
        }
    )


def answer(prompt: str) -> str:
    """Answer by quoting the first retrieved fragment and citing it.

    Args:
        prompt: User prompt with the numbered fragments.

    Returns:
        A short answer citing ``[1]``.
    """
    match = _FIRST_FRAGMENT.search(prompt)
    if not match:
        return "NO_EVIDENCE"
    sentence = re.split(r"(?<=[.!?])\s", match.group(1).strip(), maxsplit=1)[0]
    return f"Según la documentación: {sentence[:300]} [1]"


def parse_query(prompt: str) -> str:
    """Turn a question into filters with the rule-based parser.

    A real model would also use the history; the fake one only applies the
    rules to the current question.

    Args:
        prompt: User prompt built by the query prompts.

    Returns:
        The filters as JSON.
    """
    from app.ai.query.rule_parser import parse_with_rules  # Avoid an import cycle.

    today_match = _TODAY.search(prompt)
    request = _REQUEST.search(prompt)
    today = date.fromisoformat(today_match.group(1)) if today_match else date.today()
    question = request.group(1) if request else prompt
    filters = parse_with_rules(question, today, has_history=False).filters
    return filters.model_dump_json()
