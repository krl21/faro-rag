"""Parse the JSON object returned by an LLM."""

import json
import re
from typing import Any

from app.core.errors import InvalidLLMOutputError

_CODE_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse an LLM answer that should contain a single JSON object.

    Tolerates a surrounding Markdown code fence, which some models add even
    when told not to.

    Args:
        text: Raw model output.

    Returns:
        The decoded object.

    Raises:
        InvalidLLMOutputError: If the text is not a JSON object.
    """
    stripped = text.strip()
    fenced = _CODE_FENCE.match(stripped)
    if fenced:
        stripped = fenced.group(1)
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise InvalidLLMOutputError(f"Answer is not valid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise InvalidLLMOutputError("Answer must be a JSON object")
    return data
